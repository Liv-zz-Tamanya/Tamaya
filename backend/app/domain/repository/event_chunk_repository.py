from abc import ABC, abstractmethod
from datetime import date
from uuid import UUID

from app.domain.model.event_chunk import EventChunk


class EventChunkRepository(ABC):
    @abstractmethod
    async def save_all(self, chunks: list[EventChunk]) -> None: ...

    @abstractmethod
    async def search_similar(
        self,
        device_id: str,
        embedding: list[float],
        limit: int = 5,
        exclude_session_id: UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[EventChunk]:
        """cosine 유사도 검색. 날짜가 주어지면 diary_date 범위(SQL)로 먼저 거른다."""
