from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.model.event_chunk import EventChunk
from app.domain.repository.event_chunk_repository import EventChunkRepository
from app.infrastructure.persistence.models import EventChunkModel


class EventChunkRepositoryImpl(EventChunkRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def save_all(self, chunks: list[EventChunk]) -> None:
        for chunk in chunks:
            model = EventChunkModel(
                id=chunk.id,
                chat_session_id=chunk.chat_session_id,
                diary_date=chunk.diary_date,
                text=chunk.text,
                embedding=chunk.embedding,
                tags=chunk.tags,
                event_type=chunk.event_type,
                who=chunk.who,
                where=chunk.where,
                when=chunk.when,
                created_at=chunk.created_at,
            )
            self._db.add(model)
        await self._db.commit()

    async def search_similar(
        self,
        embedding: list[float],
        limit: int = 5,
        exclude_session_id: UUID | None = None,
    ) -> list[EventChunk]:
        stmt = (
            sa.select(EventChunkModel)
            .order_by(EventChunkModel.embedding.cosine_distance(embedding))
            .limit(limit)
        )
        if exclude_session_id:
            stmt = stmt.where(EventChunkModel.chat_session_id != exclude_session_id)

        result = await self._db.execute(stmt)
        models = result.scalars().all()

        return [
            EventChunk(
                id=m.id,
                chat_session_id=m.chat_session_id,
                diary_date=m.diary_date,
                text=m.text,
                embedding=list(m.embedding),
                tags=list(m.tags),
                event_type=m.event_type,
                who=m.who,
                where=m.where,
                when=m.when,
                created_at=m.created_at,
            )
            for m in models
        ]
