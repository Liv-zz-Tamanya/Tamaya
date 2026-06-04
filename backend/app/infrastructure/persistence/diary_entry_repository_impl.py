from calendar import monthrange
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.model.diary_entry import DiaryEntry
from app.domain.repository.diary_entry_repository import DiaryEntryRepository
from app.infrastructure.persistence.models import DiaryEntryModel


class DiaryEntryRepositoryImpl(DiaryEntryRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def save(self, entry: DiaryEntry) -> DiaryEntry:
        model = DiaryEntryModel(
            id=entry.id,
            user_id=entry.user_id,
            entry_date=entry.entry_date,
            body=entry.body,
            moods=entry.moods,
            keywords=entry.keywords,
            tomorrow=entry.tomorrow,
            daily_check_snapshot=entry.daily_check_snapshot,
            points=entry.points,
            session_id=entry.session_id,
            created_at=entry.created_at,
        )
        self._db.add(model)
        await self._db.commit()
        return entry

    async def find_by_date(self, user_id: UUID, entry_date: date) -> DiaryEntry | None:
        stmt = select(DiaryEntryModel).where(
            DiaryEntryModel.user_id == user_id,
            DiaryEntryModel.entry_date == entry_date,
        )
        result = await self._db.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def find_by_month(self, user_id: UUID, year: int, month: int) -> list[DiaryEntry]:
        start = date(year, month, 1)
        end = date(year, month, monthrange(year, month)[1])
        stmt = (
            select(DiaryEntryModel)
            .where(
                DiaryEntryModel.user_id == user_id,
                DiaryEntryModel.entry_date >= start,
                DiaryEntryModel.entry_date <= end,
            )
            .order_by(DiaryEntryModel.entry_date.desc())
        )
        result = await self._db.execute(stmt)
        return [self._to_domain(m) for m in result.scalars().all()]

    async def list_dates(self, user_id: UUID) -> list[date]:
        stmt = select(DiaryEntryModel.entry_date).where(DiaryEntryModel.user_id == user_id)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def _to_domain(model: DiaryEntryModel) -> DiaryEntry:
        return DiaryEntry(
            id=model.id,
            user_id=model.user_id,
            entry_date=model.entry_date,
            body=model.body,
            moods=list(model.moods),
            keywords=list(model.keywords),
            tomorrow=model.tomorrow,
            daily_check_snapshot=model.daily_check_snapshot or {},
            points=model.points,
            session_id=model.session_id,
            created_at=model.created_at,
        )
