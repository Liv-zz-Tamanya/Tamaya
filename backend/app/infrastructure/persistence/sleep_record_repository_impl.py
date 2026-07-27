from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.model.sleep_record import SleepRecord
from app.domain.repository.sleep_record_repository import SleepRecordRepository
from app.infrastructure.persistence.models import SleepRecordModel


class SleepRecordRepositoryImpl(SleepRecordRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def upsert_all(self, records: list[SleepRecord]) -> int:
        if not records:
            return 0
        # 재수입 멱등: (device_id, record_date) 충돌 시 측정값만 갱신
        statement = insert(SleepRecordModel).values(
            [
                {
                    "id": record.id,
                    "device_id": record.device_id,
                    "record_date": record.record_date,
                    "duration_minutes": record.duration_minutes,
                    "source": record.source,
                    "created_at": record.created_at,
                }
                for record in records
            ]
        )
        statement = statement.on_conflict_do_update(
            constraint="uq_sleep_records_device_record_date",
            set_={
                "duration_minutes": statement.excluded.duration_minutes,
                "source": statement.excluded.source,
            },
        )
        await self._db.execute(statement)
        await self._db.commit()
        return len(records)

    async def find_by_date_range(
        self, device_id: str, start: date, end: date
    ) -> list[SleepRecord]:
        result = await self._db.execute(
            select(SleepRecordModel)
            .where(
                SleepRecordModel.device_id == device_id,
                SleepRecordModel.record_date >= start,
                SleepRecordModel.record_date <= end,
            )
            .order_by(SleepRecordModel.record_date)
        )
        return [self._to_domain(row) for row in result.scalars().all()]

    @staticmethod
    def _to_domain(row: SleepRecordModel) -> SleepRecord:
        return SleepRecord(
            id=row.id,
            device_id=row.device_id,
            record_date=row.record_date,
            duration_minutes=row.duration_minutes,
            source=row.source,
            created_at=row.created_at,
        )
