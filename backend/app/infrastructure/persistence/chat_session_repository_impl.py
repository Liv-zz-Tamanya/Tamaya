from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.model.chat_message import ChatMessage
from app.domain.model.chat_session import ChatSession
from app.domain.repository.chat_session_repository import ChatSessionRepository
from app.infrastructure.persistence.models import ChatMessageModel, ChatSessionModel


class ChatSessionRepositoryImpl(ChatSessionRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def save(self, session: ChatSession) -> ChatSession:
        stmt = (
            select(ChatSessionModel)
            .options(selectinload(ChatSessionModel.messages))
            .where(ChatSessionModel.id == session.id)
        )
        result = await self._db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            existing.is_finalized = session.is_finalized
            # 새 메시지만 추가
            existing_count = len(existing.messages)
            for msg in session.messages[existing_count:]:
                existing.messages.append(
                    ChatMessageModel(role=msg.role, content=msg.content, created_at=msg.created_at)
                )
            await self._db.flush()
        else:
            model = ChatSessionModel(
                id=session.id,
                session_date=session.session_date,
                is_finalized=session.is_finalized,
                created_at=session.created_at,
            )
            for msg in session.messages:
                model.messages.append(
                    ChatMessageModel(role=msg.role, content=msg.content, created_at=msg.created_at)
                )
            self._db.add(model)
            await self._db.flush()
        await self._db.commit()
        return session

    async def find_by_id(self, session_id: UUID) -> ChatSession | None:
        stmt = (
            select(ChatSessionModel)
            .options(selectinload(ChatSessionModel.messages))
            .where(ChatSessionModel.id == session_id)
        )
        result = await self._db.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def find_by_date(self, session_date: date) -> ChatSession | None:
        stmt = (
            select(ChatSessionModel)
            .options(selectinload(ChatSessionModel.messages))
            .where(ChatSessionModel.session_date == session_date)
        )
        result = await self._db.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    @staticmethod
    def _to_domain(model: ChatSessionModel) -> ChatSession:
        messages = [
            ChatMessage(role=m.role, content=m.content, created_at=m.created_at)
            for m in model.messages
        ]
        return ChatSession(
            id=model.id,
            session_date=model.session_date,
            messages=messages,
            is_finalized=model.is_finalized,
            created_at=model.created_at,
        )
