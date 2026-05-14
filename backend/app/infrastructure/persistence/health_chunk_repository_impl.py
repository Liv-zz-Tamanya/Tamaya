from datetime import date

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.model.health_chunk import HealthChunk
from app.domain.repository.health_chunk_repository import HealthChunkRepository
from app.infrastructure.persistence.models import HealthChunkModel


class HealthChunkRepositoryImpl(HealthChunkRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def save_all(self, chunks: list[HealthChunk]) -> None:
        for chunk in chunks:
            model = HealthChunkModel(
                id=chunk.id,
                record_date=chunk.record_date,
                text=chunk.text,
                embedding=chunk.embedding,
                data_types=chunk.data_types,
                created_at=chunk.created_at,
            )
            self._db.add(model)
        await self._db.commit()

    async def search_similar(
        self,
        embedding: list[float],
        limit: int = 5,
    ) -> list[HealthChunk]:
        stmt = (
            sa.select(HealthChunkModel)
            .order_by(HealthChunkModel.embedding.cosine_distance(embedding))
            .limit(limit)
        )
        result = await self._db.execute(stmt)
        return [self._to_domain(m) for m in result.scalars().all()]

    async def find_by_date(self, record_date: date) -> list[HealthChunk]:
        stmt = sa.select(HealthChunkModel).where(HealthChunkModel.record_date == record_date)
        result = await self._db.execute(stmt)
        return [self._to_domain(m) for m in result.scalars().all()]

    async def exists_for_date(self, record_date: date) -> bool:
        stmt = sa.select(sa.exists().where(HealthChunkModel.record_date == record_date))
        result = await self._db.execute(stmt)
        return result.scalar()

    @staticmethod
    def _to_domain(model: HealthChunkModel) -> HealthChunk:
        return HealthChunk(
            id=model.id,
            record_date=model.record_date,
            text=model.text,
            embedding=list(model.embedding),
            data_types=list(model.data_types),
            created_at=model.created_at,
        )
