from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.model.diary import Diary
from app.domain.model.emotion import Emotion
from app.domain.repository.diary_repository import DiaryRepository
from app.infrastructure.persistence.models import DiaryModel


class DiaryRepositoryImpl(DiaryRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def save(self, diary: Diary) -> Diary:
        model = DiaryModel(
            id=diary.id,
            device_id=diary.device_id,
            diary_date=diary.diary_date,
            title=diary.title,
            content=diary.content,
            emotion=diary.emotion.value,
            satisfaction=diary.satisfaction,
            chat_session_id=diary.chat_session_id,
            created_at=diary.created_at,
        )
        self._db.add(model)
        await self._db.commit()
        return diary

    async def find_by_id(self, diary_id: UUID) -> Diary | None:
        model = await self._db.get(DiaryModel, diary_id)
        return self._to_domain(model) if model else None

    async def find_by_device_and_date(self, device_id: str, diary_date: date) -> Diary | None:
        stmt = select(DiaryModel).where(
            DiaryModel.device_id == device_id,
            DiaryModel.diary_date == diary_date,
        )
        result = await self._db.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def find_all(self, device_id: str, offset: int = 0, limit: int = 20) -> list[Diary]:
        stmt = (
            select(DiaryModel)
            .where(DiaryModel.device_id == device_id)
            .order_by(DiaryModel.diary_date.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._db.execute(stmt)
        return [self._to_domain(m) for m in result.scalars().all()]

    async def count(self, device_id: str) -> int:
        stmt = (
            select(func.count())
            .select_from(DiaryModel)
            .where(DiaryModel.device_id == device_id)
        )
        result = await self._db.execute(stmt)
        return result.scalar_one()

    @staticmethod
    def _to_domain(model: DiaryModel) -> Diary:
        return Diary(
            id=model.id,
            device_id=model.device_id,
            diary_date=model.diary_date,
            title=model.title,
            content=model.content,
            emotion=Emotion(model.emotion),
            satisfaction=model.satisfaction,
            chat_session_id=model.chat_session_id,
            created_at=model.created_at,
        )
