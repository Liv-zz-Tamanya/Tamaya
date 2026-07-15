from app.application.service.embedding_service import EmbeddingService
from app.domain.model.health_chunk import HealthChunk
from app.domain.repository.health_chunk_repository import HealthChunkRepository


class HealthRecordQueryService:
    def __init__(
        self,
        embedding_service: EmbeddingService,
        health_chunk_repo: HealthChunkRepository,
    ) -> None:
        self._embedding_service = embedding_service
        self._health_chunk_repo = health_chunk_repo

    async def search_similar(
        self,
        device_id: str,
        query: str,
        limit: int = 5,
    ) -> list[HealthChunk]:
        query_embedding = self._embedding_service.embed([query])[0]
        return await self._health_chunk_repo.search_similar(
            device_id=device_id,
            embedding=query_embedding,
            limit=limit,
        )
