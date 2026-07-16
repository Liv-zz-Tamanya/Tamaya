import asyncio
from uuid import UUID

from app.application.service.embedding_service import EmbeddingService
from app.domain.model.event_chunk import EventChunk
from app.domain.repository.event_chunk_repository import EventChunkRepository


class DiaryMemoryQueryService:
    def __init__(
        self,
        embedding_service: EmbeddingService,
        event_chunk_repo: EventChunkRepository,
    ) -> None:
        self._embedding_service = embedding_service
        self._event_chunk_repo = event_chunk_repo

    async def search_similar(
        self,
        device_id: str,
        query: str,
        exclude_session_id: UUID | None = None,
        limit: int = 5,
    ) -> list[EventChunk]:
        embeddings = await asyncio.to_thread(self._embedding_service.embed, [query])
        query_embedding = embeddings[0]
        return await self._event_chunk_repo.search_similar(
            device_id=device_id,
            embedding=query_embedding,
            limit=limit,
            exclude_session_id=exclude_session_id,
        )
