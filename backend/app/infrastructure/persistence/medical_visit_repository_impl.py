from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.model.medical_visit import MedicalVisit, MedicalVisitType
from app.domain.repository.medical_visit_repository import MedicalVisitRepository
from app.infrastructure.persistence.models import MedicalVisitModel


class MedicalVisitRepositoryImpl(MedicalVisitRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def upsert_all(self, visits: list[MedicalVisit]) -> int:
        if not visits:
            return 0
        # 재수입 멱등: (device, 날짜, 기관, 구분) 충돌 시 횟수·위치만 갱신
        statement = insert(MedicalVisitModel).values(
            [
                {
                    "id": visit.id,
                    "device_id": visit.device_id,
                    "visit_date": visit.visit_date,
                    "visit_type": visit.visit_type.value,
                    "institution": visit.institution,
                    "location": visit.location,
                    "visit_days": visit.visit_days,
                    "prescription_count": visit.prescription_count,
                    "medication_days": visit.medication_days,
                    "created_at": visit.created_at,
                }
                for visit in visits
            ]
        )
        statement = statement.on_conflict_do_update(
            constraint="uq_medical_visits_dedupe",
            set_={
                "location": statement.excluded.location,
                "visit_days": statement.excluded.visit_days,
                "prescription_count": statement.excluded.prescription_count,
                "medication_days": statement.excluded.medication_days,
            },
        )
        await self._db.execute(statement)
        await self._db.commit()
        return len(visits)

    async def find_by_date_range(
        self, device_id: str, start: date, end: date
    ) -> list[MedicalVisit]:
        result = await self._db.execute(
            select(MedicalVisitModel)
            .where(
                MedicalVisitModel.device_id == device_id,
                MedicalVisitModel.visit_date >= start,
                MedicalVisitModel.visit_date <= end,
            )
            .order_by(MedicalVisitModel.visit_date)
        )
        return [self._to_domain(row) for row in result.scalars().all()]

    @staticmethod
    def _to_domain(row: MedicalVisitModel) -> MedicalVisit:
        return MedicalVisit(
            id=row.id,
            device_id=row.device_id,
            visit_date=row.visit_date,
            visit_type=MedicalVisitType(row.visit_type),
            institution=row.institution,
            location=row.location,
            visit_days=row.visit_days,
            prescription_count=row.prescription_count,
            medication_days=row.medication_days,
            created_at=row.created_at,
        )
