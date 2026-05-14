from abc import ABC, abstractmethod
from datetime import date

from app.domain.model.health_chunk import HealthChunk


class HealthChunkRepository(ABC):
    @abstractmethod
    async def save_all(self, chunks: list[HealthChunk]) -> None: ...

    @abstractmethod
    async def search_similar(
        self,
        embedding: list[float],
        limit: int = 5,
    ) -> list[HealthChunk]: ...

    @abstractmethod
    async def find_by_date(self, record_date: date) -> list[HealthChunk]: ...

    @abstractmethod
    async def exists_for_date(self, record_date: date) -> bool: ...
