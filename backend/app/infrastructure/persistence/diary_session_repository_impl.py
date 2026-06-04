from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.model.diary_session import DiarySession, DiaryTurn
from app.domain.repository.diary_session_repository import DiarySessionRepository
from app.infrastructure.persistence.models import DiarySessionModel, DiaryTurnModel


class DiarySessionRepositoryImpl(DiarySessionRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def save(self, session: DiarySession) -> DiarySession:
        model = await self._db.get(
            DiarySessionModel, session.id, options=[selectinload(DiarySessionModel.turns)]
        )
        if model is None:
            model = DiarySessionModel(id=session.id, created_at=session.created_at)
            self._db.add(model)
        model.user_id = session.user_id
        model.session_date = session.session_date
        model.mode = session.mode
        model.status = session.status

        existing = len(model.turns)
        for turn in session.turns[existing:]:
            model.turns.append(
                DiaryTurnModel(
                    role=turn.role,
                    content=turn.content,
                    turn=turn.turn,
                    created_at=turn.created_at,
                )
            )
        await self._db.commit()
        return session

    async def find_by_id(self, session_id: UUID) -> DiarySession | None:
        model = await self._db.get(
            DiarySessionModel, session_id, options=[selectinload(DiarySessionModel.turns)]
        )
        return self._to_domain(model) if model else None

    @staticmethod
    def _to_domain(model: DiarySessionModel) -> DiarySession:
        return DiarySession(
            id=model.id,
            user_id=model.user_id,
            session_date=model.session_date,
            mode=model.mode,
            status=model.status,
            turns=[
                DiaryTurn(role=t.role, content=t.content, turn=t.turn, created_at=t.created_at)
                for t in model.turns
            ],
            created_at=model.created_at,
        )
