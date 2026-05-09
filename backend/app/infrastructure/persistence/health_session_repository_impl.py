from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.model.health_message import HealthMessage
from app.domain.model.health_session import HealthSession
from app.domain.repository.health_session_repository import HealthSessionRepository
from app.infrastructure.persistence.models import HealthMessageModel, HealthSessionModel


class HealthSessionRepositoryImpl(HealthSessionRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def save(self, session: HealthSession) -> HealthSession:
        stmt = (
            select(HealthSessionModel)
            .options(selectinload(HealthSessionModel.messages))
            .where(HealthSessionModel.id == session.id)
        )
        result = await self._db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing_count = len(existing.messages)
            for msg in session.messages[existing_count:]:
                existing.messages.append(
                    HealthMessageModel(role=msg.role, content=msg.content, created_at=msg.created_at)
                )
            await self._db.flush()
        else:
            model = HealthSessionModel(
                id=session.id,
                created_at=session.created_at,
            )
            for msg in session.messages:
                model.messages.append(
                    HealthMessageModel(role=msg.role, content=msg.content, created_at=msg.created_at)
                )
            self._db.add(model)
            await self._db.flush()

        await self._db.commit()
        return session

    async def find_by_id(self, session_id: UUID) -> HealthSession | None:
        stmt = (
            select(HealthSessionModel)
            .options(selectinload(HealthSessionModel.messages))
            .where(HealthSessionModel.id == session_id)
        )
        result = await self._db.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    @staticmethod
    def _to_domain(model: HealthSessionModel) -> HealthSession:
        messages = [
            HealthMessage(role=m.role, content=m.content, created_at=m.created_at)
            for m in model.messages
        ]
        return HealthSession(
            id=model.id,
            messages=messages,
            created_at=model.created_at,
        )
