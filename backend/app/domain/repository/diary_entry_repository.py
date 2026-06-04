from abc import ABC, abstractmethod
from datetime import date
from uuid import UUID

from app.domain.model.diary_entry import DiaryEntry


class DiaryEntryRepository(ABC):
    @abstractmethod
    async def save(self, entry: DiaryEntry) -> DiaryEntry: ...

    @abstractmethod
    async def find_by_date(self, user_id: UUID, entry_date: date) -> DiaryEntry | None: ...

    @abstractmethod
    async def find_by_month(self, user_id: UUID, year: int, month: int) -> list[DiaryEntry]: ...

    @abstractmethod
    async def list_dates(self, user_id: UUID) -> list[date]: ...
