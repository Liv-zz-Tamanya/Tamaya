from abc import ABC, abstractmethod
from datetime import date

from app.domain.model.health_record import HealthDailySummary


class HealthRecordRepository(ABC):
    @abstractmethod
    async def save(self, record: HealthDailySummary) -> HealthDailySummary: ...

    @abstractmethod
    async def find_by_date(
        self, device_id: str, record_date: date
    ) -> HealthDailySummary | None: ...

    @abstractmethod
    async def find_all(self, device_id: str) -> list[HealthDailySummary]: ...

    @abstractmethod
    async def source_hash_exists(self, device_id: str, source_hash: str) -> bool: ...
