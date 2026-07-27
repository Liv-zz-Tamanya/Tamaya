from abc import ABC, abstractmethod
from datetime import date

from app.domain.model.sleep_record import SleepRecord


class SleepRecordRepository(ABC):
    @abstractmethod
    async def upsert_all(self, records: list[SleepRecord]) -> int:
        """(device_id, record_date) 기준 upsert. 처리한 행 수를 반환한다."""

    @abstractmethod
    async def find_by_date_range(
        self, device_id: str, start: date, end: date
    ) -> list[SleepRecord]:
        """기간 내(양끝 포함) 수면 기록을 날짜 오름차순으로 반환한다."""
