import asyncio
from datetime import date
from uuid import UUID

from app.application.service.embedding_service import EmbeddingService
from app.application.service.reranking_service import (
    DEFAULT_CANDIDATE_K,
    MAX_CANDIDATE_K,
    RerankingService,
    apply_reranking,
)
from app.domain.model.event_chunk import EventChunk
from app.domain.repository.event_chunk_repository import EventChunkRepository


class DiaryMemoryQueryService:
    """일기 기억 검색 — embedding → (날짜 필터된) pgvector 후보 → 재정렬 → final_k.

    reranking_service가 None이면 기존 단일 단계 검색과 동일하게 동작한다.
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        event_chunk_repo: EventChunkRepository,
        reranking_service: RerankingService | None = None,
        candidate_k: int = DEFAULT_CANDIDATE_K,
    ) -> None:
        self._embedding_service = embedding_service
        self._event_chunk_repo = event_chunk_repo
        self._reranking = reranking_service
        self._candidate_k = min(candidate_k, MAX_CANDIDATE_K)

    async def search_similar(
        self,
        device_id: str,
        query: str,
        exclude_session_id: UUID | None = None,
        limit: int = 5,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[EventChunk]:
        validate_date_range(start_date, end_date)
        embeddings = await asyncio.to_thread(self._embedding_service.embed, [query])
        query_embedding = embeddings[0]
        candidate_limit = max(self._candidate_k, limit) if self._reranking else limit
        chunks = await self._event_chunk_repo.search_similar(
            device_id=device_id,
            embedding=query_embedding,
            limit=candidate_limit,
            exclude_session_id=exclude_session_id,
            start_date=start_date,
            end_date=end_date,
        )
        if self._reranking is None:
            return chunks
        return await apply_reranking(
            self._reranking, query, chunks, [chunk.text for chunk in chunks], limit
        )


def validate_date_range(start_date: date | None, end_date: date | None) -> None:
    if start_date is not None and end_date is not None and start_date > end_date:
        raise ValueError(f"start_date({start_date}) must be <= end_date({end_date})")
