import asyncio
from datetime import date

from app.application.service.diary_memory_query_service import validate_date_range
from app.application.service.embedding_service import EmbeddingService
from app.application.service.reranking_service import (
    DEFAULT_CANDIDATE_K,
    MAX_CANDIDATE_K,
    RerankingService,
    apply_reranking,
)
from app.domain.model.health_chunk import HealthChunk
from app.domain.repository.health_chunk_repository import HealthChunkRepository


class HealthRecordQueryService:
    """건강 기록 검색 — embedding → (날짜 필터된) pgvector 후보 → 재정렬 → final_k.

    reranking_service가 None이면 기존 단일 단계 검색과 동일하게 동작한다.
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        health_chunk_repo: HealthChunkRepository,
        reranking_service: RerankingService | None = None,
        candidate_k: int = DEFAULT_CANDIDATE_K,
    ) -> None:
        self._embedding_service = embedding_service
        self._health_chunk_repo = health_chunk_repo
        self._reranking = reranking_service
        self._candidate_k = min(candidate_k, MAX_CANDIDATE_K)

    async def search_similar(
        self,
        device_id: str,
        query: str,
        limit: int = 5,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[HealthChunk]:
        validate_date_range(start_date, end_date)
        embeddings = await asyncio.to_thread(self._embedding_service.embed, [query])
        query_embedding = embeddings[0]
        candidate_limit = max(self._candidate_k, limit) if self._reranking else limit
        chunks = await self._health_chunk_repo.search_similar(
            device_id=device_id,
            embedding=query_embedding,
            limit=candidate_limit,
            start_date=start_date,
            end_date=end_date,
        )
        if self._reranking is None:
            return chunks
        return await apply_reranking(
            self._reranking, query, chunks, [chunk.text for chunk in chunks], limit
        )
