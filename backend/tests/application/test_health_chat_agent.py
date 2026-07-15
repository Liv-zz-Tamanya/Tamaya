from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

from app.application.service.embedding_service import EmbeddingService
from app.application.service.health_ai_service import HealthAiService
from app.application.usecase.health_chat_agent import HealthChatAgent
from app.domain.model.health_chunk import HealthChunk
from app.domain.model.health_message import HealthMessage
from app.domain.repository.health_chunk_repository import HealthChunkRepository


class _FakeHealthAi(HealthAiService):
    def __init__(self, reply: str = "health reply") -> None:
        self.reply = reply
        self.chat_calls: list[dict] = []

    async def chat(
        self,
        messages: list[HealthMessage],
        health_context: list[str] | None = None,
    ) -> str:
        self.chat_calls.append({"messages": messages, "health_context": health_context})
        return self.reply


class _FakeEmbedding(EmbeddingService):
    def __init__(self, embedding: list[float]) -> None:
        self.embedding = embedding
        self.calls: list[list[str]] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        return [self.embedding]


class _FakeHealthChunkRepo(HealthChunkRepository):
    def __init__(self, chunks: list[HealthChunk]) -> None:
        self.chunks = chunks
        self.search_calls: list[dict] = []

    async def save_all(self, chunks: list[HealthChunk]) -> None:  # pragma: no cover
        raise NotImplementedError

    async def search_similar(
        self,
        device_id: str,
        embedding: list[float],
        limit: int = 5,
    ) -> list[HealthChunk]:
        self.search_calls.append({"device_id": device_id, "embedding": embedding, "limit": limit})
        return self.chunks

    async def find_by_date(
        self, device_id: str, record_date: date
    ) -> list[HealthChunk]:  # pragma: no cover
        raise NotImplementedError

    async def exists_for_date(self, device_id: str, record_date: date) -> bool:  # pragma: no cover
        raise NotImplementedError


def _message(content: str) -> HealthMessage:
    return HealthMessage(role="user", content=content, created_at=datetime.now())


def _health_chunk(text: str) -> HealthChunk:
    return HealthChunk(
        device_id="dev-a",
        record_date=date(2026, 7, 10),
        text=text,
        embedding=[0.1, 0.2],
        data_types=["steps"],
    )


async def test_health_chat_agent_retrieves_health_data_and_returns_ai_reply():
    ai = _FakeHealthAi(reply="health data reply")
    embedding = _FakeEmbedding([0.2, 0.8])
    repo = _FakeHealthChunkRepo([_health_chunk("9,144걸음을 걸었어.")])
    agent = HealthChatAgent(ai, embedding, repo)
    messages = [_message("어제 몇 걸음 걸었어?")]

    response = await agent.run(
        device_id="dev-a",
        session_id=uuid4(),
        messages=messages,
        current_user_message="어제 몇 걸음 걸었어?",
    )

    assert response == "health data reply"
    assert embedding.calls == [["어제 몇 걸음 걸었어?"]]
    assert repo.search_calls == [{"device_id": "dev-a", "embedding": [0.2, 0.8], "limit": 5}]
    assert ai.chat_calls == [
        {
            "messages": messages,
            "health_context": ["- 2026-07-10: 9,144걸음을 걸었어."],
        }
    ]


async def test_health_chat_agent_passes_no_context_when_search_returns_empty():
    ai = _FakeHealthAi(reply="no health data reply")
    embedding = _FakeEmbedding([0.5, 0.5])
    repo = _FakeHealthChunkRepo([])
    agent = HealthChatAgent(ai, embedding, repo)
    messages = [_message("오늘 운동 기록 있어?")]

    response = await agent.run(
        device_id="dev-a",
        session_id=uuid4(),
        messages=messages,
        current_user_message="오늘 운동 기록 있어?",
    )

    assert response == "no health data reply"
    assert embedding.calls == [["오늘 운동 기록 있어?"]]
    assert repo.search_calls == [{"device_id": "dev-a", "embedding": [0.5, 0.5], "limit": 5}]
    assert ai.chat_calls == [{"messages": messages, "health_context": None}]
