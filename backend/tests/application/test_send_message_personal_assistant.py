from __future__ import annotations

from datetime import date
from uuid import UUID

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.application.service.ai_chat_service import AiChatService
from app.application.service.diary_chat_prompt import DiaryConversationContext
from app.application.usecase.personal_assistant_agent import PersonalAssistantMode
from app.application.usecase.send_message import SendMessageUseCase
from app.domain.model.chat_message import ChatMessage
from app.domain.model.chat_session import ChatSession
from app.domain.model.diary import Diary
from app.domain.repository.chat_session_repository import ChatSessionRepository
from app.domain.repository.diary_repository import DiaryRepository


class _MemoryChatSessionRepo(ChatSessionRepository):
    def __init__(self) -> None:
        self._sessions: dict[UUID, ChatSession] = {}
        self.save_count = 0

    async def save(self, session: ChatSession) -> ChatSession:
        self._sessions[session.id] = session
        self.save_count += 1
        return session

    async def find_by_id(self, session_id: UUID) -> ChatSession | None:
        return self._sessions.get(session_id)

    async def find_by_device_and_date(
        self, device_id: str, session_date: date
    ) -> ChatSession | None:
        return next(
            (
                session
                for session in self._sessions.values()
                if session.device_id == device_id and session.session_date == session_date
            ),
            None,
        )


class _MemoryDiaryRepo(DiaryRepository):
    def __init__(self) -> None:
        self.saved: list[Diary] = []

    async def save(self, diary: Diary) -> Diary:
        self.saved.append(diary)
        return diary

    async def find_by_id(self, diary_id):  # pragma: no cover
        raise NotImplementedError

    async def find_by_device_and_date(self, device_id, diary_date):  # pragma: no cover
        raise NotImplementedError

    async def find_all(self, device_id: str, offset: int = 0, limit: int = 20):  # pragma: no cover
        raise NotImplementedError

    async def count(self, device_id: str) -> int:  # pragma: no cover
        raise NotImplementedError


class _FakeAi(AiChatService):
    def __init__(self, *, finalize_intent: bool = False) -> None:
        self.finalize_intent = finalize_intent
        self.detect_finalize_intent_calls: list[str] = []
        self.generate_closing_message_calls = 0
        self.generate_diary_calls = 0

    async def chat(
        self,
        messages: list[ChatMessage],
        suggest_finalize: bool = False,
        max_turns: int = 5,
    ) -> str:  # pragma: no cover
        raise AssertionError("legacy chat should not be called")

    async def generate_diary(self, messages: list[ChatMessage]) -> dict:
        self.generate_diary_calls += 1
        return {
            "title": "오늘의 회고",
            "content": "오늘은 차분히 하루를 돌아봤다. 이야기하면서 마음이 조금 정리됐다. 마지막에는 일기로 남기기로 했다. 내일도 천천히 가면 된다.",
            "emotion": "calm",
            "satisfaction": 60,
            "keywords": ["회고", "정리", "하루"],
        }

    async def detect_finalize_intent(self, user_message: str) -> bool:
        self.detect_finalize_intent_calls.append(user_message)
        return self.finalize_intent

    async def generate_closing_message(self, messages: list[ChatMessage]) -> str:
        self.generate_closing_message_calls += 1
        return "오늘 이야기를 일기로 정리해볼게."

    async def extract_event_chunks(self, messages: list[ChatMessage]) -> list[dict]:
        return []


class _FakePersonalAssistantAgent:
    def __init__(self, response: AIMessage | Exception) -> None:
        self.response = response
        self.calls: list[dict] = []

    async def run(
        self,
        *,
        messages,
        mode: PersonalAssistantMode,
        diary_context: DiaryConversationContext | None = None,
    ) -> AIMessage:
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


class _FakeExtractChunks:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def execute(
        self, session_id: UUID, diary_date: date, messages: list[ChatMessage]
    ) -> None:
        self.calls.append(
            {"session_id": session_id, "diary_date": diary_date, "messages": messages}
        )


async def _saved_session(repo: _MemoryChatSessionRepo, *, max_turns: int = 5) -> ChatSession:
    session = ChatSession(device_id="dev-a", max_turns=max_turns)
    session.add_message("assistant", "시작해볼까?")
    await repo.save(session)
    return session


async def test_general_diary_response_uses_personal_assistant_and_saves_ai_message():
    repo = _MemoryChatSessionRepo()
    session = await _saved_session(repo)
    ai = _FakeAi()
    agent = _FakePersonalAssistantAgent(AIMessage(content="  조금 더 들려줘.  "))
    factory = _FakePersonalAssistantFactory(agent)
    usecase = SendMessageUseCase(repo, ai, _MemoryDiaryRepo(), factory, _FakeExtractChunks())

    user_msg, ai_msg, suggest, diary = await usecase.execute(session.id, "오늘 힘들었어", "dev-a")

    assert factory.calls == [
        {"device_id": "dev-a", "session_id": session.id, "mode": PersonalAssistantMode.DIARY}
    ]
    assert len(agent.calls) == 1
    assert agent.calls[0]["mode"] == PersonalAssistantMode.DIARY
    assert [type(message) for message in agent.calls[0]["messages"]] == [
        type(AIMessage(content="")),
        type(HumanMessage(content="")),
    ]
    assert [message.content for message in agent.calls[0]["messages"]] == [
        "시작해볼까?",
        "오늘 힘들었어",
    ]
    assert agent.calls[0]["diary_context"] == DiaryConversationContext(
        max_turns=5,
        current_user_turn=1,
        suggest_finalize=False,
    )
    assert user_msg.content == "오늘 힘들었어"
    assert ai_msg.content == "조금 더 들려줘."
    assert suggest is False
    assert diary is None
    assert repo.save_count == 2


async def test_initial_turn_passes_current_turn_and_max_turns():
    repo = _MemoryChatSessionRepo()
    session = await _saved_session(repo, max_turns=3)
    agent = _FakePersonalAssistantAgent(AIMessage(content="응, 이어가볼까?"))
    usecase = SendMessageUseCase(
        repo,
        _FakeAi(),
        _MemoryDiaryRepo(),
        _FakePersonalAssistantFactory(agent),
        _FakeExtractChunks(),
    )

    _, _, suggest, _ = await usecase.execute(session.id, "첫 번째 이야기", "dev-a")

    assert agent.calls[0]["diary_context"] == DiaryConversationContext(
        max_turns=3,
        current_user_turn=1,
        suggest_finalize=False,
    )
    assert suggest is False


async def test_suggest_finalize_without_user_consent_still_uses_personal_assistant():
    repo = _MemoryChatSessionRepo()
    session = ChatSession(device_id="dev-a", max_turns=5)
    for index in range(3):
        session.add_message("user", f"이야기 {index}")
        session.add_message("assistant", "응")
    await repo.save(session)
    ai = _FakeAi(finalize_intent=False)
    agent = _FakePersonalAssistantAgent(AIMessage(content="오늘 이야기를 정리해볼까?"))
    factory = _FakePersonalAssistantFactory(agent)
    usecase = SendMessageUseCase(repo, ai, _MemoryDiaryRepo(), factory, _FakeExtractChunks())

    _, ai_msg, suggest, diary = await usecase.execute(session.id, "아직 더 말할래", "dev-a")

    assert ai.detect_finalize_intent_calls == ["아직 더 말할래"]
    assert factory.calls == [
        {"device_id": "dev-a", "session_id": session.id, "mode": PersonalAssistantMode.DIARY}
    ]
    assert agent.calls[0]["diary_context"] == DiaryConversationContext(
        max_turns=5,
        current_user_turn=4,
        suggest_finalize=True,
    )
    assert ai_msg.content == "오늘 이야기를 정리해볼까?"
    assert suggest is True
    assert diary is None


async def test_user_consent_finalize_skips_personal_assistant_and_preserves_finalize_flow():
    repo = _MemoryChatSessionRepo()
    diary_repo = _MemoryDiaryRepo()
    extract_chunks = _FakeExtractChunks()
    session = ChatSession(device_id="dev-a", max_turns=5)
    for index in range(3):
        session.add_message("user", f"이야기 {index}")
        session.add_message("assistant", "응")
    await repo.save(session)
    ai = _FakeAi(finalize_intent=True)
    agent = _FakePersonalAssistantAgent(AIMessage(content="호출되면 안 됨"))
    factory = _FakePersonalAssistantFactory(agent)
    usecase = SendMessageUseCase(repo, ai, diary_repo, factory, extract_chunks)

    _, ai_msg, suggest, diary = await usecase.execute(session.id, "응 정리해줘", "dev-a")

    assert factory.calls == []
    assert agent.calls == []
    assert ai_msg.content == "오늘 이야기를 일기로 정리해볼게."
    assert suggest is False
    assert diary is not None
    assert session.is_finalized is True
    assert len(diary_repo.saved) == 1
    assert len(extract_chunks.calls) == 1


async def test_must_finalize_skips_personal_assistant_and_preserves_finalize_flow():
    repo = _MemoryChatSessionRepo()
    diary_repo = _MemoryDiaryRepo()
    extract_chunks = _FakeExtractChunks()
    session = ChatSession(device_id="dev-a", max_turns=3)
    for index in range(2):
        session.add_message("user", f"이야기 {index}")
        session.add_message("assistant", "응")
    await repo.save(session)
    agent = _FakePersonalAssistantAgent(AIMessage(content="호출되면 안 됨"))
    factory = _FakePersonalAssistantFactory(agent)
    usecase = SendMessageUseCase(repo, _FakeAi(), diary_repo, factory, extract_chunks)

    _, ai_msg, suggest, diary = await usecase.execute(session.id, "세 번째", "dev-a")

    assert factory.calls == []
    assert agent.calls == []
    assert ai_msg.content == "오늘 이야기를 일기로 정리해볼게."
    assert suggest is False
    assert diary is not None
    assert session.is_finalized is True
    assert len(diary_repo.saved) == 1
    assert len(extract_chunks.calls) == 1


async def test_agent_exception_is_not_saved_or_fallback_to_legacy_chat():
    repo = _MemoryChatSessionRepo()
    session = await _saved_session(repo)
    ai = _FakeAi()
    agent = _FakePersonalAssistantAgent(RuntimeError("agent failed"))
    factory = _FakePersonalAssistantFactory(agent)
    usecase = SendMessageUseCase(repo, ai, _MemoryDiaryRepo(), factory, _FakeExtractChunks())

    with pytest.raises(RuntimeError, match="agent failed"):
        await usecase.execute(session.id, "오늘 힘들었어", "dev-a")

    assert repo.save_count == 1


async def test_empty_or_tool_call_final_content_is_not_saved():
    for response in (
        AIMessage(content="   "),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "search_diary_memories",
                    "args": {"query": "x"},
                    "id": "call-1",
                    "type": "tool_call",
                }
            ],
        ),
    ):
        repo = _MemoryChatSessionRepo()
        session = await _saved_session(repo)
        agent = _FakePersonalAssistantAgent(response)
        usecase = SendMessageUseCase(
            repo,
            _FakeAi(),
            _MemoryDiaryRepo(),
            _FakePersonalAssistantFactory(agent),
            _FakeExtractChunks(),
        )

        with pytest.raises(ValueError):
            await usecase.execute(session.id, "오늘 힘들었어", "dev-a")

        assert repo.save_count == 1
