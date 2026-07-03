from datetime import date

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.model.health_record import HealthDailySummary
from app.domain.repository.health_record_repository import HealthRecordRepository
from app.infrastructure.persistence.models import HealthDailySummaryModel


class HealthRecordRepositoryImpl(HealthRecordRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def save(self, record: HealthDailySummary) -> HealthDailySummary:
        model = HealthDailySummaryModel(
            id=record.id,
            record_date=record.record_date,
            step_count=record.step_count,
            step_goal=record.step_goal,
            step_goal_achieved=record.step_goal_achieved,
            step_calories=record.step_calories,
            step_distance_m=record.step_distance_m,
            has_exercise=record.has_exercise,
            exercise_duration_sec=record.exercise_duration_sec,
            exercise_distance_m=record.exercise_distance_m,
            exercise_calories=record.exercise_calories,
            heart_rate_avg=record.heart_rate_avg,
            heart_rate_min=record.heart_rate_min,
            heart_rate_max=record.heart_rate_max,
            floors_climbed=record.floors_climbed,
            source_hash=record.source_hash,
            created_at=record.created_at,
        )
        self._db.add(model)
        await self._db.commit()
        return record

    async def find_by_date(self, record_date: date) -> HealthDailySummary | None:
        stmt = sa.select(HealthDailySummaryModel).where(
            HealthDailySummaryModel.record_date == record_date
        )
        result = await self._db.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def find_all(self) -> list[HealthDailySummary]:
        stmt = sa.select(HealthDailySummaryModel).order_by(HealthDailySummaryModel.record_date)
        result = await self._db.execute(stmt)
        return [self._to_domain(m) for m in result.scalars().all()]

    async def source_hash_exists(self, source_hash: str) -> bool:
        stmt = sa.select(sa.exists().where(HealthDailySummaryModel.source_hash == source_hash))
        result = await self._db.execute(stmt)
        return result.scalar()

    @staticmethod
    def _to_domain(model: HealthDailySummaryModel) -> HealthDailySummary:
        return HealthDailySummary(
            id=model.id,
            record_date=model.record_date,
            step_count=model.step_count,
            step_goal=model.step_goal,
            step_goal_achieved=model.step_goal_achieved,
            step_calories=model.step_calories,
            step_distance_m=model.step_distance_m,
            has_exercise=model.has_exercise,
            exercise_duration_sec=model.exercise_duration_sec,
            exercise_distance_m=model.exercise_distance_m,
            exercise_calories=model.exercise_calories,
            heart_rate_avg=model.heart_rate_avg,
            heart_rate_min=model.heart_rate_min,
            heart_rate_max=model.heart_rate_max,
            floors_climbed=model.floors_climbed,
            source_hash=model.source_hash,
            created_at=model.created_at,
        )
