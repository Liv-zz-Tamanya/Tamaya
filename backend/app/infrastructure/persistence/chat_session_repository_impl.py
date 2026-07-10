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
            existing.max_turns = session.max_turns
            existing.is_finalized = session.is_finalized
            if len(session.messages) < len(existing.messages):
                # 재회고 리셋: 메시지가 줄었으면 전체 교체 (cascade delete-orphan)
                existing.messages.clear()
                for msg in session.messages:
                    existing.messages.append(
                        ChatMessageModel(
                            role=msg.role, content=msg.content, created_at=msg.created_at
                        )
                    )
            else:
                # 증분: 새 메시지만 추가
                for msg in session.messages[len(existing.messages):]:
                    existing.messages.append(
                        ChatMessageModel(
                            role=msg.role, content=msg.content, created_at=msg.created_at
                        )
                    )
            await self._db.flush()
        else:
            model = ChatSessionModel(
                id=session.id,
                device_id=session.device_id,
                session_date=session.session_date,
                max_turns=session.max_turns,
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

    async def find_by_device_and_date(
        self, device_id: str, session_date: date
    ) -> ChatSession | None:
        stmt = (
            select(ChatSessionModel)
            .options(selectinload(ChatSessionModel.messages))
            .where(
                ChatSessionModel.device_id == device_id,
                ChatSessionModel.session_date == session_date,
            )
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
            device_id=model.device_id,
            session_date=model.session_date,
            messages=messages,
            max_turns=model.max_turns,
            is_finalized=model.is_finalized,
            created_at=model.created_at,
        )
