from uuid import UUID, uuid4

import pytest
from langchain_core.messages import AIMessage

from app.application.service.model_provider_error import (
    ModelProviderError,
    ModelProviderErrorCategory,
)
from app.application.service.personal_assistant_timeout import PersonalAssistantTimeoutError
from app.application.usecase.personal_assistant_agent import PersonalAssistantMode
from app.application.usecase.send_health_message import SendHealthMessageUseCase
from app.domain.model.health_session import HealthSession
from app.domain.repository.health_session_repository import HealthSessionRepository


class _MemoryHealthSessionRepo(HealthSessionRepository):
    def __init__(self) -> None:
        self.sessions: dict[UUID, HealthSession] = {}
        self.save_count = 0

    async def save(self, session: HealthSession) -> HealthSession:
        self.sessions[session.id] = session
        self.save_count += 1
        return session

    async def find_by_id(self, session_id: UUID, device_id: str) -> HealthSession | None:
        session = self.sessions.get(session_id)
        if session is None or session.device_id != device_id:
            return None
        return session


class _FakePersonalAssistantAgent:
    def __init__(self, response: AIMessage | Exception) -> None:
        self.response = response
        self.calls: list[dict] = []

    async def run(self, *, messages, mode: PersonalAssistantMode, diary_context=None) -> AIMessage:
        self.calls.append(
            {
                "messages": list(messages),
                "mode": mode,
                "diary_context": diary_context,
            }
        )
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class _FakePersonalAssistantFactory:
    def __init__(self, agent: _FakePersonalAssistantAgent) -> None:
        self.agent = agent
        self.calls: list[dict] = []

    def create(
        self,
        *,
        device_id: str,
        session_id: UUID,
        mode: PersonalAssistantMode,
    ) -> _FakePersonalAssistantAgent:
        self.calls.append({"device_id": device_id, "session_id": session_id, "mode": mode})
        return self.agent


def _session() -> HealthSession:
    session = HealthSession(device_id="dev-a")
    session.add_message("assistant", "건강 인사")
    return session


async def test_general_health_response_uses_personal_assistant_and_saves_ai_message():
    repo = _MemoryHealthSessionRepo()
    session = _session()
    await repo.save(session)
    agent = _FakePersonalAssistantAgent(AIMessage(content="  9,144걸음이야.  "))
    factory = _FakePersonalAssistantFactory(agent)
    usecase = SendHealthMessageUseCase(repo, factory)

    user_msg, ai_msg = await usecase.execute(session.id, "어제 걸음 수 알려줘", "dev-a")

    assert factory.calls == [
        {"device_id": "dev-a", "session_id": session.id, "mode": PersonalAssistantMode.HEALTH}
    ]
    assert len(agent.calls) == 1
    assert agent.calls[0]["mode"] == PersonalAssistantMode.HEALTH
    assert agent.calls[0]["diary_context"] is None
    assert [message.content for message in agent.calls[0]["messages"]] == [
        "건강 인사",
        "어제 걸음 수 알려줘",
    ]
    assert user_msg.content == "어제 걸음 수 알려줘"
    assert ai_msg.content == "9,144걸음이야."
    assert repo.save_count == 2
    assert [message.content for message in session.messages] == [
        "건강 인사",
        "어제 걸음 수 알려줘",
        "9,144걸음이야.",
    ]


async def test_missing_health_session_raises_without_factory_or_save():
    repo = _MemoryHealthSessionRepo()
    agent = _FakePersonalAssistantAgent(AIMessage(content="호출되면 안 됨"))
    factory = _FakePersonalAssistantFactory(agent)
    usecase = SendHealthMessageUseCase(repo, factory)

    with pytest.raises(ValueError, match="세션을 찾을 수 없습니다."):
        await usecase.execute(uuid4(), "안녕", "dev-a")

    assert factory.calls == []
    assert agent.calls == []
    assert repo.save_count == 0


async def test_agent_error_is_propagated_without_saving_empty_response():
    repo = _MemoryHealthSessionRepo()
    session = _session()
    await repo.save(session)
    agent = _FakePersonalAssistantAgent(RuntimeError("agent failed"))
    usecase = SendHealthMessageUseCase(repo, _FakePersonalAssistantFactory(agent))

    with pytest.raises(RuntimeError, match="agent failed"):
        await usecase.execute(session.id, "어제 기록", "dev-a")

    assert repo.save_count == 1
    assert [message.content for message in session.messages] == ["건강 인사", "어제 기록"]


async def test_agent_timeout_is_propagated_without_saving_assistant_message():
    repo = _MemoryHealthSessionRepo()
    session = _session()
    await repo.save(session)
    agent = _FakePersonalAssistantAgent(PersonalAssistantTimeoutError("execution"))
    usecase = SendHealthMessageUseCase(repo, _FakePersonalAssistantFactory(agent))

    with pytest.raises(PersonalAssistantTimeoutError) as error:
        await usecase.execute(session.id, "어제 기록", "dev-a")

    assert error.value.stage == "execution"
    assert repo.save_count == 1
    assert [message.content for message in session.messages] == ["건강 인사", "어제 기록"]


async def test_model_provider_error_is_propagated_without_saving_assistant_message():
    repo = _MemoryHealthSessionRepo()
    session = _session()
    await repo.save(session)
    agent = _FakePersonalAssistantAgent(
        ModelProviderError(category=ModelProviderErrorCategory.UNAVAILABLE, retryable=True)
    )
    usecase = SendHealthMessageUseCase(repo, _FakePersonalAssistantFactory(agent))

    with pytest.raises(ModelProviderError):
        await usecase.execute(session.id, "어제 기록", "dev-a")

    assert repo.save_count == 1
    assert [message.content for message in session.messages] == ["건강 인사", "어제 기록"]


async def test_empty_or_tool_call_final_content_is_not_saved():
    responses = [
        AIMessage(content="   "),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "search_health_records",
                    "args": {"query": "걸음"},
                    "id": "call-health",
                    "type": "tool_call",
                }
            ],
        ),
        AIMessage(content=[{"type": "image", "url": "x"}]),
    ]

    for response in responses:
        repo = _MemoryHealthSessionRepo()
        session = _session()
        await repo.save(session)
        agent = _FakePersonalAssistantAgent(response)
        usecase = SendHealthMessageUseCase(repo, _FakePersonalAssistantFactory(agent))

        with pytest.raises(ValueError):
            await usecase.execute(session.id, "어제 기록", "dev-a")

        assert repo.save_count == 1
