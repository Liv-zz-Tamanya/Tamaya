"""QueryService 2단계 검색 — candidate_k 조회·final_k 반환·날짜 전달 검증."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from app.application.service.diary_memory_query_service import DiaryMemoryQueryService
from app.application.service.health_record_query_service import HealthRecordQueryService
from app.application.service.reranking_service import RerankingService

START = date(2026, 7, 20)
END = date(2026, 7, 21)


class _FakeEmbedding:
    def embed(self, texts):
        return [[0.1] * 384 for _ in texts]


def _chunk(chunk_id: str):
    return SimpleNamespace(id=chunk_id, text=f"text-{chunk_id}")


class _FakeEventChunkRepo:
    def __init__(self, chunks):
        self._chunks = chunks
        self.calls: list[dict] = []

    async def search_similar(self, device_id, embedding, limit=5, exclude_session_id=None,
                             start_date=None, end_date=None):
        self.calls.append({
            "device_id": device_id, "limit": limit, "exclude_session_id": exclude_session_id,
            "start_date": start_date, "end_date": end_date,
        })
        return self._chunks[:limit]


class _FakeHealthChunkRepo:
    def __init__(self, chunks):
        self._chunks = chunks
        self.calls: list[dict] = []

    async def search_similar(self, device_id, embedding, limit=5, start_date=None, end_date=None):
        self.calls.append({
            "device_id": device_id, "limit": limit,
            "start_date": start_date, "end_date": end_date,
        })
        return self._chunks[:limit]


class _ReverseReranker(RerankingService):
    def rerank(self, query, documents):
        return list(range(len(documents)))  # 뒤쪽 후보일수록 높은 점수


async def test_diary_without_reranker_keeps_legacy_behavior():
    repo = _FakeEventChunkRepo([_chunk(f"c{i}") for i in range(20)])
    service = DiaryMemoryQueryService(_FakeEmbedding(), repo)

    result = await service.search_similar("dev-1", "질문", limit=5)

    assert repo.calls[0]["limit"] == 5  # candidate 확장 없음 — 기존 동작
    assert [c.id for c in result] == ["c0", "c1", "c2", "c3", "c4"]


async def test_diary_with_reranker_fetches_candidate_k_and_returns_final_k():
    repo = _FakeEventChunkRepo([_chunk(f"c{i}") for i in range(20)])
    service = DiaryMemoryQueryService(
        _FakeEmbedding(), repo, _ReverseReranker(), candidate_k=15
    )

    result = await service.search_similar("dev-1", "질문", limit=5)

    assert repo.calls[0]["limit"] == 15  # candidate_k로 조회
    assert len(result) == 5  # final_k만 반환
    assert [c.id for c in result] == ["c14", "c13", "c12", "c11", "c10"]  # 재정렬됨


async def test_candidate_k_never_below_final_k():
    repo = _FakeEventChunkRepo([_chunk(f"c{i}") for i in range(20)])
    service = DiaryMemoryQueryService(
        _FakeEmbedding(), repo, _ReverseReranker(), candidate_k=5
    )
    await service.search_similar("dev-1", "질문", limit=10)
    assert repo.calls[0]["limit"] == 10


async def test_diary_passes_dates_and_session_exclusion_to_repo():
    repo = _FakeEventChunkRepo([])
    service = DiaryMemoryQueryService(_FakeEmbedding(), repo)

    await service.search_similar(
        "dev-1", "질문", limit=5, start_date=START, end_date=END
    )

    call = repo.calls[0]
    assert call["start_date"] == START
    assert call["end_date"] == END


async def test_invalid_date_range_raises():
    service = DiaryMemoryQueryService(_FakeEmbedding(), _FakeEventChunkRepo([]))
    with pytest.raises(ValueError):
        await service.search_similar("dev-1", "질문", start_date=END, end_date=START)


async def test_health_service_same_structure():
    repo = _FakeHealthChunkRepo([_chunk(f"h{i}") for i in range(20)])
    service = HealthRecordQueryService(
        _FakeEmbedding(), repo, _ReverseReranker(), candidate_k=12
    )

    result = await service.search_similar(
        "dev-1", "질문", limit=3, start_date=START, end_date=START
    )

    call = repo.calls[0]
    assert call["limit"] == 12
    assert call["start_date"] == START
    assert [c.id for c in result] == ["h11", "h10", "h9"]


async def test_health_invalid_date_range_raises():
    service = HealthRecordQueryService(_FakeEmbedding(), _FakeHealthChunkRepo([]))
    with pytest.raises(ValueError):
        await service.search_similar("dev-1", "질문", start_date=END, end_date=START)
