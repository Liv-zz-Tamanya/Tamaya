from abc import ABC, abstractmethod
from datetime import date

from app.domain.model.medical_visit import MedicalVisit


class MedicalVisitRepository(ABC):
    @abstractmethod
    async def upsert_all(self, visits: list[MedicalVisit]) -> int:
        """(device_id, visit_date, institution, visit_type) 기준 upsert. 처리 행 수 반환."""

    @abstractmethod
    async def find_by_date_range(
        self, device_id: str, start: date, end: date
    ) -> list[MedicalVisit]:
        """기간 내(양끝 포함) 진료 이벤트를 날짜 오름차순으로 반환한다."""
