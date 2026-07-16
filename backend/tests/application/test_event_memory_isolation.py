from __future__ import annotations

import math
from datetime import date
from uuid import UUID, uuid4

import pytest
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.tools import BaseTool

from app.application.service.ai_chat_service import AiChatService
from app.application.service.diary_memory_query_service import DiaryMemoryQueryService
from app.application.service.embedding_service import EmbeddingService
from app.application.service.health_record_query_service import HealthRecordQueryService
from app.application.service.tool_calling_chat_model import ToolCallingChatModel
from app.application.usecase.personal_assistant_agent_factory import PersonalAssistantAgentFactory
from app.application.usecase.send_message import SendMessageUseCase
from app.domain.model.chat_message import ChatMessage
from app.domain.model.chat_session import ChatSession
from app.domain.model.diary import Diary
from app.domain.model.event_chunk import EventChunk
from app.domain.repository.chat_session_repository import ChatSessionRepository
from app.domain.repository.diary_repository import DiaryRepository
from app.domain.repository.event_chunk_repository import EventChunkRepository
from app.domain.repository.health_chunk_repository import HealthChunkRepository


class _MemoryChatSessionRepo(ChatSessionRepository):
    def __init__(self) -> None:
        self._sessions: dict[UUID, ChatSession] = {}

    async def save(self, session: ChatSession) -> ChatSession:
        self._sessions[session.id] = session
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
    async def save(self, diary: Diary) -> Diary:  # pragma: no cover
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
    async def chat(
        self,
        messages: list[ChatMessage],
        suggest_finalize: bool = False,
        max_turns: int = 5,
    ) -> str:
        return "응답"

    async def generate_diary(self, messages: list[ChatMessage]) -> dict:  # pragma: no cover
        raise NotImplementedError

    async def detect_finalize_intent(self, user_message: str) -> bool:  # pragma: no cover
        return False

    async def generate_closing_message(
        self, messages: list[ChatMessage]
    ) -> str:  # pragma: no cover
        raise NotImplementedError

    async def extract_event_chunks(
        self, messages: list[ChatMessage]
    ) -> list[dict]:  # pragma: no cover
        raise NotImplementedError


class _FakeEmbedding(EmbeddingService):
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0]]


class _MemoryEventChunkRepo(EventChunkRepository):
    def __init__(self, session_device_ids: dict[UUID, str], chunks: list[EventChunk]) -> None:
        self._session_device_ids = session_device_ids
        self._chunks = chunks
        self.calls: list[tuple[str, UUID | None]] = []

    async def save_all(self, chunks: list[EventChunk]) -> None:  # pragma: no cover
        self._chunks.extend(chunks)

    async def search_similar(
        self,
        device_id: str,
        embedding: list[float],
        limit: int = 5,
        exclude_session_id: UUID | None = None,
    ) -> list[EventChunk]:
        self.calls.append((device_id, exclude_session_id))
        scoped = [
            chunk
            for chunk in self._chunks
            if self._session_device_ids[chunk.chat_session_id] == device_id
            and chunk.chat_session_id != exclude_session_id
        ]
        return sorted(scoped, key=lambda chunk: _cosine_distance(chunk.embedding, embedding))[
            :limit
        ]


class _FakeHealthChunkRepo(HealthChunkRepository):
    def __init__(self) -> None:
        self.calls = 0

    async def save_all(self, chunks):  # pragma: no cover
        raise NotImplementedError

    async def search_similar(
        self,
        device_id: str,
        embedding: list[float],
        limit: int = 5,
    ) -> list:
        self.calls += 1
        return []

    async def find_by_date(self, device_id: str, record_date: date) -> list:
        return []

    async def exists_for_date(self, device_id: str, record_date: date) -> bool:
        return False


class _FakeToolCallingModel(ToolCallingChatModel):
    def __init__(self, *, use_tool: bool = True) -> None:
        self.use_tool = use_tool
        self.calls: list[dict] = []

    async def ainvoke(
        self,
        messages: list[BaseMessage],
        tools: list[BaseTool],
    ) -> AIMessage:
        self.calls.append({"messages": list(messages), "tools": list(tools)})
        if self.use_tool and len(self.calls) == 1:
            return AIMessage(
                content="기억을 찾아볼게.",
                tool_calls=[
                    {
                        "name": "search_diary_memories",
                        "args": {"query": "지난번 얘기", "limit": 5},
                        "id": "call-diary",
                        "type": "tool_call",
                    }
                ],
            )
        return AIMessage(content="지난번 얘기는 기록에 없어서 잘 모르겠어.")


class _FakeExtractChunks:
    async def execute(
        self, session_id: UUID, diary_date: date, messages: list[ChatMessage]
    ) -> None:
        return None


def _cosine_distance(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    return 1 - dot / (left_norm * right_norm)


def _chunk(session_id: UUID, text: str, embedding: list[float]) -> EventChunk:
    return EventChunk(
        id=uuid4(),
        chat_session_id=session_id,
        diary_date=date(2026, 7, 10),
        text=text,
        embedding=embedding,
        tags=[],
        event_type="daily",
    )


@pytest.mark.asyncio
async def test_send_message_uses_tool_calling_memory_search_with_verified_device_id():
    session = ChatSession(device_id="dev-a", max_turns=5)
    session.add_message("assistant", "시작해볼까?")
    repo = _MemoryChatSessionRepo()
    await repo.save(session)
    event_repo = _MemoryEventChunkRepo({session.id: "dev-a"}, [])
    health_repo = _FakeHealthChunkRepo()
    model = _FakeToolCallingModel()
    factory = PersonalAssistantAgentFactory(
        model,
        DiaryMemoryQueryService(_FakeEmbedding(), event_repo),
        HealthRecordQueryService(_FakeEmbedding(), health_repo),
    )
    usecase = SendMessageUseCase(
        repo,
        _FakeAi(),
        _MemoryDiaryRepo(),
        factory,
        _FakeExtractChunks(),
    )

    _, ai_msg, _, _ = await usecase.execute(session.id, "지난번 얘기 기억나?", "dev-a")

    assert event_repo.calls == [("dev-a", session.id)]
    assert health_repo.calls == 0
    assert ai_msg.content == "지난번 얘기는 기록에 없어서 잘 모르겠어."
    assert any(isinstance(message, ToolMessage) for message in model.calls[1]["messages"])


@pytest.mark.asyncio
async def test_send_message_uses_personal_assistant_without_tool_search_when_model_answers_directly():
    session = ChatSession(device_id="dev-a", max_turns=5)
    session.add_message("assistant", "시작해볼까?")
    repo = _MemoryChatSessionRepo()
    await repo.save(session)
    event_repo = _MemoryEventChunkRepo({session.id: "dev-a"}, [])
    health_repo = _FakeHealthChunkRepo()
    model = _FakeToolCallingModel(use_tool=False)
    factory = PersonalAssistantAgentFactory(
        model,
        DiaryMemoryQueryService(_FakeEmbedding(), event_repo),
        HealthRecordQueryService(_FakeEmbedding(), health_repo),
    )
    usecase = SendMessageUseCase(
        repo,
        _FakeAi(),
        _MemoryDiaryRepo(),
        factory,
        _FakeExtractChunks(),
    )

    _, ai_msg, _, _ = await usecase.execute(session.id, "오늘은 그냥 이야기할래", "dev-a")

    assert ai_msg.content == "지난번 얘기는 기록에 없어서 잘 모르겠어."
    assert event_repo.calls == []
    assert health_repo.calls == 0
    assert len(model.calls) == 1
