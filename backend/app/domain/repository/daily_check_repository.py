from abc import ABC, abstractmethod
from datetime import date
from uuid import UUID

from app.domain.model.daily_check import DailyCheck


class DailyCheckRepository(ABC):
    @abstractmethod
    async def upsert(self, check: DailyCheck) -> DailyCheck: ...

    @abstractmethod
    async def find_by_date(self, user_id: UUID, check_date: date) -> DailyCheck | None: ...

    @abstractmethod
    async def find_by_month(self, user_id: UUID, year: int, month: int) -> list[DailyCheck]: ...
