from calendar import monthrange
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.model.daily_check import DailyCheck
from app.domain.repository.daily_check_repository import DailyCheckRepository
from app.infrastructure.persistence.models import DailyCheckModel


class DailyCheckRepositoryImpl(DailyCheckRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def upsert(self, check: DailyCheck) -> DailyCheck:
        stmt = select(DailyCheckModel).where(
            DailyCheckModel.user_id == check.user_id,
            DailyCheckModel.check_date == check.check_date,
        )
        result = await self._db.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            model = DailyCheckModel(
                id=check.id,
                user_id=check.user_id,
                check_date=check.check_date,
                created_at=check.created_at,
            )
            self._db.add(model)
        model.food = check.food
        model.water = check.water
        model.sleep = check.sleep
        model.movement = check.movement
        model.sun = check.sun
        await self._db.commit()
        await self._db.refresh(model)
        return self._to_domain(model)

    async def find_by_date(self, user_id: UUID, check_date: date) -> DailyCheck | None:
        stmt = select(DailyCheckModel).where(
            DailyCheckModel.user_id == user_id,
            DailyCheckModel.check_date == check_date,
        )
        result = await self._db.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def find_by_month(self, user_id: UUID, year: int, month: int) -> list[DailyCheck]:
        start = date(year, month, 1)
        end = date(year, month, monthrange(year, month)[1])
        stmt = select(DailyCheckModel).where(
            DailyCheckModel.user_id == user_id,
            DailyCheckModel.check_date >= start,
            DailyCheckModel.check_date <= end,
        )
        result = await self._db.execute(stmt)
        return [self._to_domain(m) for m in result.scalars().all()]

    @staticmethod
    def _to_domain(model: DailyCheckModel) -> DailyCheck:
        return DailyCheck(
            id=model.id,
            user_id=model.user_id,
            check_date=model.check_date,
            food=model.food or {},
            water=model.water,
            sleep=model.sleep or {},
            movement=model.movement or {},
            sun=model.sun or {},
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
