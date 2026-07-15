from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from app.application.service.ai_chat_service import AiChatService
from app.application.service.embedding_service import EmbeddingService
from app.application.usecase.chat_agent import ChatAgent
from app.domain.model.chat_message import ChatMessage
from app.domain.model.event_chunk import EventChunk
from app.domain.repository.event_chunk_repository import EventChunkRepository


class _FakeAi(AiChatService):
    def __init__(self, *, should_retrieve: bool, reply: str = "agent reply") -> None:
        self.should_retrieve = should_retrieve
        self.reply = reply
        self.classify_calls: list[str] = []
        self.chat_calls: list[dict] = []

    async def chat(
        self,
        messages: list[ChatMessage],
        suggest_finalize: bool = False,
        memories: list[str] | None = None,
        max_turns: int = 5,
    ) -> str:
        self.chat_calls.append(
            {
                "messages": messages,
                "suggest_finalize": suggest_finalize,
                "memories": memories,
                "max_turns": max_turns,
            }
        )
        return self.reply

    async def generate_diary(self, messages: list[ChatMessage]) -> dict:  # pragma: no cover
        raise NotImplementedError

    async def detect_finalize_intent(self, user_message: str) -> bool:  # pragma: no cover
        raise NotImplementedError

    async def generate_closing_message(
        self, messages: list[ChatMessage]
    ) -> str:  # pragma: no cover
        raise NotImplementedError

    async def classify_memory_need(self, user_message: str) -> bool:
        self.classify_calls.append(user_message)
        return self.should_retrieve

    async def extract_event_chunks(
        self, messages: list[ChatMessage]
    ) -> list[dict]:  # pragma: no cover
        raise NotImplementedError


class _FakeEmbedding(EmbeddingService):
    def __init__(self, embedding: list[float]) -> None:
        self.embedding = embedding
        self.calls: list[list[str]] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        return [self.embedding]


class _FakeEventChunkRepo(EventChunkRepository):
    def __init__(self, chunks: list[EventChunk]) -> None:
        self.chunks = chunks
        self.search_calls: list[dict] = []

    async def save_all(self, chunks: list[EventChunk]) -> None:  # pragma: no cover
        raise NotImplementedError

    async def search_similar(
        self,
        device_id: str,
        embedding: list[float],
        limit: int = 5,
        exclude_session_id: UUID | None = None,
    ) -> list[EventChunk]:
        self.search_calls.append(
            {
                "device_id": device_id,
                "embedding": embedding,
                "limit": limit,
                "exclude_session_id": exclude_session_id,
            }
        )
        return self.chunks


def _message(content: str) -> ChatMessage:
    return ChatMessage(role="user", content=content, created_at=datetime.now())


def _event_chunk(
    *,
    session_id: UUID,
    text: str = "팀 발표를 준비했다",
    tags: list[str] | None = None,
    who: str | None = None,
    where: str | None = None,
    when: str | None = None,
) -> EventChunk:
    return EventChunk(
        id=uuid4(),
        chat_session_id=session_id,
        diary_date=date(2026, 7, 10),
        text=text,
        embedding=[0.1, 0.2],
        tags=tags or [],
        event_type="work",
        who=who,
        where=where,
        when=when,
    )


async def test_chat_agent_skips_memory_retrieval_when_not_needed():
    ai = _FakeAi(should_retrieve=False, reply="no memory reply")
    embedding = _FakeEmbedding([0.7, 0.3])
    repo = _FakeEventChunkRepo([])
    agent = ChatAgent(ai, embedding, repo)
    messages = [_message("오늘은 그냥 얘기하고 싶어")]
    session_id = uuid4()

    response = await agent.run(
        device_id="dev-a",
        session_id=session_id,
        messages=messages,
        current_user_message="오늘은 그냥 얘기하고 싶어",
        suggest_finalize=True,
        max_turns=3,
    )

    assert response == "no memory reply"
    assert ai.classify_calls == ["오늘은 그냥 얘기하고 싶어"]
    assert embedding.calls == []
    assert repo.search_calls == []
    assert ai.chat_calls == [
        {
            "messages": messages,
            "suggest_finalize": True,
            "memories": None,
            "max_turns": 3,
        }
    ]


async def test_chat_agent_retrieves_and_formats_memories_when_needed():
    session_id = uuid4()
    chunk_session_id = uuid4()
    ai = _FakeAi(should_retrieve=True, reply="memory reply")
    embedding = _FakeEmbedding([0.1, 0.9])
    repo = _FakeEventChunkRepo(
        [
            _event_chunk(
                session_id=chunk_session_id,
                tags=["발표", "회사"],
                who="민수",
                where="회의실",
                when="오전",
            )
        ]
    )
    agent = ChatAgent(ai, embedding, repo)
    messages = [_message("지난 발표 기억나?")]

    response = await agent.run(
        device_id="dev-a",
        session_id=session_id,
        messages=messages,
        current_user_message="지난 발표 기억나?",
        suggest_finalize=False,
        max_turns=5,
    )

    assert response == "memory reply"
    assert embedding.calls == [["지난 발표 기억나?"]]
    assert repo.search_calls == [
        {
            "device_id": "dev-a",
            "embedding": [0.1, 0.9],
            "limit": 5,
            "exclude_session_id": session_id,
        }
    ]
    assert ai.chat_calls[0]["messages"] is messages
    assert ai.chat_calls[0]["suggest_finalize"] is False
    assert ai.chat_calls[0]["max_turns"] == 5
    assert ai.chat_calls[0]["memories"] == [
        "- 2026-07-10: 팀 발표를 준비했다 (인물:민수, 장소:회의실, 시간:오전) #발표 #회사"
    ]


async def test_chat_agent_passes_no_memories_when_retrieval_returns_empty():
    ai = _FakeAi(should_retrieve=True, reply="empty memory reply")
    embedding = _FakeEmbedding([0.4, 0.6])
    repo = _FakeEventChunkRepo([])
    agent = ChatAgent(ai, embedding, repo)

    response = await agent.run(
        device_id="dev-a",
        session_id=uuid4(),
        messages=[],
        current_user_message="예전에 말한 거 기억나?",
    )

    assert response == "empty memory reply"
    assert embedding.calls == [["예전에 말한 거 기억나?"]]
    assert len(repo.search_calls) == 1
    assert ai.chat_calls[0]["memories"] is None
