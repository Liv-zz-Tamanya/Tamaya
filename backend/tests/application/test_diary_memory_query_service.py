from __future__ import annotations

import asyncio
import threading
from datetime import date
from uuid import UUID, uuid4

from app.application.service.diary_memory_query_service import DiaryMemoryQueryService
from app.application.service.embedding_service import EmbeddingService
from app.domain.model.event_chunk import EventChunk
from app.domain.repository.event_chunk_repository import EventChunkRepository


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


def _event_chunk(text: str) -> EventChunk:
    return EventChunk(
        id=uuid4(),
        chat_session_id=uuid4(),
        diary_date=date(2026, 7, 10),
        text=text,
        embedding=[0.1, 0.2],
        tags=[],
        event_type="daily",
    )


async def test_diary_memory_query_service_searches_with_first_embedding():
    chunks = [_event_chunk("첫 번째 기억"), _event_chunk("두 번째 기억")]
    embedding = _FakeEmbedding([0.3, 0.7])
    repo = _FakeEventChunkRepo(chunks)
    service = DiaryMemoryQueryService(embedding, repo)
    exclude_session_id = uuid4()

    result = await service.search_similar(
        device_id="dev-a",
        query="지난 기억 찾아줘",
        exclude_session_id=exclude_session_id,
        limit=3,
    )

    assert result is chunks
    assert embedding.calls == [["지난 기억 찾아줘"]]
    assert repo.search_calls == [
        {
            "device_id": "dev-a",
            "embedding": [0.3, 0.7],
            "limit": 3,
            "exclude_session_id": exclude_session_id,
        }
    ]


async def test_diary_memory_query_service_returns_empty_results():
    embedding = _FakeEmbedding([0.1, 0.9])
    repo = _FakeEventChunkRepo([])
    service = DiaryMemoryQueryService(embedding, repo)

    result = await service.search_similar(device_id="dev-a", query="기억 검색")

    assert result == []
    assert embedding.calls == [["기억 검색"]]
    assert repo.search_calls == [
        {
            "device_id": "dev-a",
            "embedding": [0.1, 0.9],
            "limit": 5,
            "exclude_session_id": None,
        }
    ]


async def test_diary_embedding_does_not_block_event_loop_before_repository_search():
    started = threading.Event()
    release = threading.Event()
    loop_progressed = asyncio.Event()

    class _BlockingEmbedding(_FakeEmbedding):
        def embed(self, texts: list[str]) -> list[list[float]]:
            started.set()
            release.wait()
            return super().embed(texts)

    embedding = _BlockingEmbedding([0.2, 0.8])
    repo = _FakeEventChunkRepo([])
    service = DiaryMemoryQueryService(embedding, repo)
    task = asyncio.create_task(service.search_similar(device_id="dev-a", query="기억 검색"))

    await asyncio.to_thread(started.wait)

    async def _mark_loop_progress() -> None:
        await asyncio.sleep(0)
        loop_progressed.set()

    asyncio.create_task(_mark_loop_progress())
    await asyncio.wait_for(loop_progressed.wait(), timeout=1)
    assert repo.search_calls == []

    release.set()
    await task
