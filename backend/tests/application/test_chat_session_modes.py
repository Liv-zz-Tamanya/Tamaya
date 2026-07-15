from __future__ import annotations

from datetime import date
from uuid import UUID

import pytest

from app.application.service.ai_chat_service import AiChatService
from app.application.usecase.diary_keywords import normalize_diary_keywords
from app.application.usecase.send_message import SendMessageUseCase
from app.application.usecase.start_chat_session import StartChatSessionUseCase
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
        for session in self._sessions.values():
            if session.device_id == device_id and session.session_date == session_date:
                return session
        return None


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
    def __init__(self) -> None:
        self.chat_calls: list[int] = []

    async def chat(
        self,
        messages: list[ChatMessage],
        suggest_finalize: bool = False,
        memories: list[str] | None = None,
        max_turns: int = 5,
    ) -> str:
        self.chat_calls.append(max_turns)
        return f"{max_turns}턴 회고를 시작해볼까?"

    async def generate_diary(self, messages: list[ChatMessage]) -> dict:
        return {
            "title": "짧은 회고",
            "content": "오늘은 조금 지쳤지만 차분히 하루를 돌아봤다. 짧게라도 정리하니 마음이 가벼워졌다. 내일은 조금 더 천천히 숨을 고르고 싶다. 오늘도 잘 버텼다.",
            "emotion": "calm",
            "satisfaction": 55,
            "keywords": ["방학", "운동", "자격증"],
        }

    async def detect_finalize_intent(self, user_message: str) -> bool:
        return False

    async def generate_closing_message(self, messages: list[ChatMessage]) -> str:
        return "여기까지 들은 걸로 오늘 일기를 정리해볼게."

    async def classify_memory_need(self, user_message: str) -> bool:
        return False

    async def extract_event_chunks(self, messages: list[ChatMessage]) -> list[dict]:
        return []


class _FakeChatAgent:
    def __init__(self) -> None:
        self.calls: list[int] = []

    async def run(
        self,
        device_id: str,
        session_id: UUID,
        messages: list[ChatMessage],
        current_user_message: str,
        suggest_finalize: bool = False,
        max_turns: int = 5,
    ) -> str:
        self.calls.append(max_turns)
        return "조금 더 들려줘."


class _FakeExtractChunks:
    def __init__(self) -> None:
        self.calls = 0

    async def execute(
        self, session_id: UUID, diary_date: date, messages: list[ChatMessage]
    ) -> None:
        self.calls += 1


@pytest.mark.asyncio
async def test_start_chat_session_reuses_same_turn_policy():
    repo = _MemoryChatSessionRepo()
    ai = _FakeAi()
    today = date.today()
    session = ChatSession(device_id="dev-1", session_date=today, max_turns=5)
    session.add_message("assistant", "이미 진행 중이야.")
    await repo.save(session)

    usecase = StartChatSessionUseCase(repo, ai)
    resumed = await usecase.execute("dev-1", max_turns=5)

    assert resumed is session
    assert resumed.messages[0].content == "이미 진행 중이야."
    assert ai.chat_calls == []
    assert repo.save_count == 1


@pytest.mark.asyncio
async def test_start_chat_session_resets_when_turn_policy_changes():
    repo = _MemoryChatSessionRepo()
    ai = _FakeAi()
    today = date.today()
    session = ChatSession(device_id="dev-1", session_date=today, max_turns=5)
    session.add_message("assistant", "기존 인삿말")
    session.add_message("user", "이전 대화")
    await repo.save(session)

    usecase = StartChatSessionUseCase(repo, ai)
    restarted = await usecase.execute("dev-1", max_turns=3)

    assert restarted.id == session.id
    assert restarted.max_turns == 3
    assert restarted.is_finalized is False
    assert len(restarted.messages) == 1
    assert restarted.messages[0].role == "assistant"
    assert "3턴 회고" in restarted.messages[0].content
    assert ai.chat_calls == [3]
    assert repo.save_count == 2


@pytest.mark.asyncio
async def test_start_chat_session_resets_when_requested_explicitly():
    repo = _MemoryChatSessionRepo()
    ai = _FakeAi()
    today = date.today()
    session = ChatSession(device_id="dev-1", session_date=today, max_turns=5)
    session.add_message("assistant", "기존 인삿말")
    session.add_message("user", "이어지는 대화")
    await repo.save(session)

    usecase = StartChatSessionUseCase(repo, ai)
    restarted = await usecase.execute("dev-1", max_turns=5, reset=True)

    assert restarted.id == session.id
    assert restarted.max_turns == 5
    assert len(restarted.messages) == 1
    assert "5턴 회고" in restarted.messages[0].content
    assert ai.chat_calls == [5]
    assert repo.save_count == 2


@pytest.mark.asyncio
async def test_send_message_auto_finalizes_on_third_turn_for_short_mode():
    repo = _MemoryChatSessionRepo()
    diary_repo = _MemoryDiaryRepo()
    ai = _FakeAi()
    chat_agent = _FakeChatAgent()
    extract_chunks = _FakeExtractChunks()

    session = ChatSession(device_id="dev-1", max_turns=3)
    session.add_message("assistant", "시작해볼까?")
    session.add_message("user", "첫 번째")
    session.add_message("assistant", "응")
    session.add_message("user", "두 번째")
    session.add_message("assistant", "계속 들려줘")
    await repo.save(session)

    usecase = SendMessageUseCase(repo, ai, diary_repo, chat_agent, extract_chunks)
    user_msg, ai_msg, suggest, diary = await usecase.execute(session.id, "세 번째", "dev-1")

    assert user_msg.content == "세 번째"
    assert ai_msg.content == "여기까지 들은 걸로 오늘 일기를 정리해볼게."
    assert suggest is False
    assert diary is not None
    assert diary.title == "짧은 회고"
    assert diary.keywords == ["방학", "운동", "자격증"]
    assert session.is_finalized is True
    assert len(diary_repo.saved) == 1
    assert chat_agent.calls == []
    assert extract_chunks.calls == 1


def test_normalize_diary_keywords_keeps_short_unique_strings():
    keywords = normalize_diary_keywords(
        [" 방학 ", "", "운동", "방학", 123, "자격증", "추가"],
    )

    assert keywords == ["방학", "운동", "자격증"]
