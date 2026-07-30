from abc import ABC, abstractmethod
from datetime import date

from app.domain.model.health_chunk import HealthChunk


class HealthChunkRepository(ABC):
    @abstractmethod
    async def save_all(self, chunks: list[HealthChunk]) -> None: ...

    @abstractmethod
    async def search_similar(
        self,
        device_id: str,
        embedding: list[float],
        limit: int = 5,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[HealthChunk]:
        """cosine 유사도 검색. 날짜가 주어지면 record_date 범위(SQL)로 먼저 거른다."""

    @abstractmethod
    async def find_by_date(self, device_id: str, record_date: date) -> list[HealthChunk]: ...

    @abstractmethod
    async def exists_for_date(self, device_id: str, record_date: date) -> bool: ...
