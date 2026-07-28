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
    async def find_by_date_range(
        self, device_id: str, start: date, end: date
    ) -> list[HealthDailySummary]:
        """기간 내(양끝 포함) 일별 요약을 날짜 오름차순으로 반환한다."""

    @abstractmethod
    async def find_all(self, device_id: str) -> list[HealthDailySummary]: ...

    @abstractmethod
    async def source_hash_exists(self, device_id: str, source_hash: str) -> bool: ...
