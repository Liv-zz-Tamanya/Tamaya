from datetime import date
from uuid import UUID, uuid4

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.tools import BaseTool

from app.application.service.tool_calling_chat_model import ToolCallingChatModel
from app.application.usecase.personal_assistant_agent_factory import PersonalAssistantAgentFactory
from app.application.usecase.send_health_message import SendHealthMessageUseCase
from app.domain.model.health_chunk import HealthChunk
from app.domain.model.health_session import HealthSession
from app.domain.repository.health_session_repository import HealthSessionRepository


class _MemoryHealthSessionRepo(HealthSessionRepository):
    def __init__(self) -> None:
        self.sessions: dict[UUID, HealthSession] = {}

    async def save(self, session: HealthSession) -> HealthSession:
        self.sessions[session.id] = session
        return session

    async def find_by_id(self, session_id: UUID, device_id: str) -> HealthSession | None:
        session = self.sessions.get(session_id)
        if session is None or session.device_id != device_id:
            return None
        return session


class _FakeToolCallingModel(ToolCallingChatModel):
    def __init__(self, responses: list[AIMessage]) -> None:
        self.responses = responses
        self.calls: list[dict] = []

    async def ainvoke(
        self,
        messages: list[BaseMessage],
        tools: list[BaseTool],
    ) -> AIMessage:
        self.calls.append({"messages": list(messages), "tools": list(tools)})
        return self.responses.pop(0)


class _FakeDiaryQuery:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def search_similar(
        self,
        device_id: str,
        query: str,
        exclude_session_id: UUID | None = None,
        limit: int = 5,
    ) -> list:
        self.calls.append(
            {
                "device_id": device_id,
                "query": query,
                "exclude_session_id": exclude_session_id,
                "limit": limit,
            }
        )
        return []


class _FakeHealthQuery:
    def __init__(self, chunks: list[HealthChunk] | None = None) -> None:
        self.chunks = chunks or []
        self.calls: list[dict] = []

    async def search_similar(self, device_id: str, query: str, limit: int = 5) -> list[HealthChunk]:
        self.calls.append({"device_id": device_id, "query": query, "limit": limit})
        return self.chunks


def _session() -> HealthSession:
    session = HealthSession(device_id="dev-a")
    session.add_message("assistant", "건강 인사")
    return session


def _health_chunk(text: str) -> HealthChunk:
    return HealthChunk(
        id=uuid4(),
        device_id="dev-a",
        record_date=date(2026, 7, 10),
        text=text,
        embedding=[0.1, 0.2],
        data_types=["steps"],
    )


async def test_health_message_without_tool_search_saves_final_response():
    repo = _MemoryHealthSessionRepo()
    session = _session()
    await repo.save(session)
    model = _FakeToolCallingModel([AIMessage(content="걸음수나 운동 기록을 물어봐줘.")])
    diary_query = _FakeDiaryQuery()
    health_query = _FakeHealthQuery()
    factory = PersonalAssistantAgentFactory(model, diary_query, health_query)
    usecase = SendHealthMessageUseCase(repo, factory)

    _, ai_msg = await usecase.execute(session.id, "안녕", "dev-a")

    assert ai_msg.content == "걸음수나 운동 기록을 물어봐줘."
    assert health_query.calls == []
    assert diary_query.calls == []
    assert [tool.name for tool in model.calls[0]["tools"]] == ["search_health_records"]


async def test_health_message_tool_search_passes_result_to_next_model_call():
    repo = _MemoryHealthSessionRepo()
    session = _session()
    await repo.save(session)
    model = _FakeToolCallingModel(
        [
            AIMessage(
                content="건강 기록을 확인할게.",
                tool_calls=[
                    {
                        "name": "search_health_records",
                        "args": {"query": "어제 걸음 수", "limit": 2},
                        "id": "call-health",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="어제는 9,144걸음이야."),
        ]
    )
    diary_query = _FakeDiaryQuery()
    health_query = _FakeHealthQuery([_health_chunk("9,144걸음을 걸었어.")])
    factory = PersonalAssistantAgentFactory(model, diary_query, health_query)
    usecase = SendHealthMessageUseCase(repo, factory)

    _, ai_msg = await usecase.execute(session.id, "어제 몇 걸음 걸었어?", "dev-a")

    assert ai_msg.content == "어제는 9,144걸음이야."
    assert health_query.calls == [{"device_id": "dev-a", "query": "어제 걸음 수", "limit": 2}]
    assert diary_query.calls == []
    tool_messages = [
        message for message in model.calls[1]["messages"] if isinstance(message, ToolMessage)
    ]
    assert len(tool_messages) == 1
    assert tool_messages[0].tool_call_id == "call-health"
    assert "9,144걸음을 걸었어." in tool_messages[0].content
    assert [message.role for message in session.messages] == ["assistant", "user", "assistant"]


async def test_health_message_empty_search_result_is_normal_tool_result():
    repo = _MemoryHealthSessionRepo()
    session = _session()
    await repo.save(session)
    model = _FakeToolCallingModel(
        [
            AIMessage(
                content="건강 기록을 확인할게.",
                tool_calls=[
                    {
                        "name": "search_health_records",
                        "args": {"query": "오늘 운동", "limit": 5},
                        "id": "call-empty",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="오늘 운동 기록은 찾지 못했어."),
        ]
    )
    health_query = _FakeHealthQuery([])
    factory = PersonalAssistantAgentFactory(model, _FakeDiaryQuery(), health_query)
    usecase = SendHealthMessageUseCase(repo, factory)

    _, ai_msg = await usecase.execute(session.id, "오늘 운동 기록 있어?", "dev-a")

    assert ai_msg.content == "오늘 운동 기록은 찾지 못했어."
    assert health_query.calls == [{"device_id": "dev-a", "query": "오늘 운동", "limit": 5}]
    tool_messages = [
        message for message in model.calls[1]["messages"] if isinstance(message, ToolMessage)
    ]
    assert len(tool_messages) == 1
    assert '"count": 0' in tool_messages[0].content
