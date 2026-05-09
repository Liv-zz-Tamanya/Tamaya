from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.model.event_chunk import EventChunk


class EventChunkRepository(ABC):
    @abstractmethod
    async def save_all(self, chunks: list[EventChunk]) -> None: ...

    @abstractmethod
    async def search_similar(
        self,
        embedding: list[float],
        limit: int = 5,
        exclude_session_id: UUID | None = None,
    ) -> list[EventChunk]: ...
