from __future__ import annotations

import asyncio
import threading
from datetime import date

from app.application.service.embedding_service import EmbeddingService
from app.application.service.health_record_query_service import HealthRecordQueryService
from app.domain.model.health_chunk import HealthChunk
from app.domain.repository.health_chunk_repository import HealthChunkRepository


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


def _health_chunk(text: str) -> HealthChunk:
    return HealthChunk(
        device_id="dev-a",
        record_date=date(2026, 7, 10),
        text=text,
        embedding=[0.1, 0.2],
        data_types=["steps"],
    )


async def test_health_record_query_service_searches_with_first_embedding():
    chunks = [_health_chunk("첫 번째 건강 기록"), _health_chunk("두 번째 건강 기록")]
    embedding = _FakeEmbedding([0.6, 0.4])
    repo = _FakeHealthChunkRepo(chunks)
    service = HealthRecordQueryService(embedding, repo)

    result = await service.search_similar(
        device_id="dev-a",
        query="걸음 수 알려줘",
        limit=4,
    )

    assert result is chunks
    assert embedding.calls == [["걸음 수 알려줘"]]
    assert repo.search_calls == [{"device_id": "dev-a", "embedding": [0.6, 0.4], "limit": 4}]


async def test_health_record_query_service_returns_empty_results():
    embedding = _FakeEmbedding([0.5, 0.5])
    repo = _FakeHealthChunkRepo([])
    service = HealthRecordQueryService(embedding, repo)

    result = await service.search_similar(device_id="dev-a", query="오늘 건강 기록 있어?")

    assert result == []
    assert embedding.calls == [["오늘 건강 기록 있어?"]]
    assert repo.search_calls == [{"device_id": "dev-a", "embedding": [0.5, 0.5], "limit": 5}]


async def test_health_embedding_does_not_block_event_loop_before_repository_search():
    started = threading.Event()
    release = threading.Event()
    loop_progressed = asyncio.Event()

    class _BlockingEmbedding(_FakeEmbedding):
        def embed(self, texts: list[str]) -> list[list[float]]:
            started.set()
            release.wait()
            return super().embed(texts)

    embedding = _BlockingEmbedding([0.8, 0.2])
    repo = _FakeHealthChunkRepo([])
    service = HealthRecordQueryService(embedding, repo)
    task = asyncio.create_task(service.search_similar(device_id="dev-a", query="건강 검색"))

    await asyncio.to_thread(started.wait)

    async def _mark_loop_progress() -> None:
        await asyncio.sleep(0)
        loop_progressed.set()

    asyncio.create_task(_mark_loop_progress())
    await asyncio.wait_for(loop_progressed.wait(), timeout=1)
    assert repo.search_calls == []

    release.set()
    await task
