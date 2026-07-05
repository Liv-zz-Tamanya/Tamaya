from abc import ABC, abstractmethod
from datetime import date
from uuid import UUID

from app.domain.model.diary import Diary


class DiaryRepository(ABC):
    @abstractmethod
    async def save(self, diary: Diary) -> Diary: ...

    @abstractmethod
    async def find_by_id(self, diary_id: UUID) -> Diary | None: ...

    @abstractmethod
    async def find_by_device_and_date(
        self, device_id: str, diary_date: date
    ) -> Diary | None: ...

    @abstractmethod
    async def find_all(self, device_id: str, offset: int = 0, limit: int = 20) -> list[Diary]: ...

    @abstractmethod
    async def count(self, device_id: str) -> int: ...
