from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.model.diary_session import DiarySession


class DiarySessionRepository(ABC):
    @abstractmethod
    async def save(self, session: DiarySession) -> DiarySession: ...

    @abstractmethod
    async def find_by_id(self, session_id: UUID) -> DiarySession | None: ...
