"""정성신호 SQLAlchemy 리포지토리 구현 — device_id 기간 조회.

behavior_mentions는 JSONB([{behavior, polarity}])로 직렬화/역직렬화한다.
recorded_date는 [start, end] 양끝 포함(inclusive) 범위로 조회한다.
"""

import uuid
from datetime import date
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.model.emotion import Emotion
from app.domain.model.qualitative_signal import BehaviorMention, QualitativeSignal
from app.domain.repository.qualitative_signal_repository import QualitativeSignalRepository
from app.infrastructure.persistence.models import QualitativeSignalModel


class QualitativeSignalRepositoryImpl(QualitativeSignalRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def save(self, device_id: str, session_id: UUID, signal: QualitativeSignal) -> None:
        model = QualitativeSignalModel(
            id=uuid.uuid4(),
            device_id=device_id,
            session_id=session_id,
            emotion=signal.emotion.value,
            behavior_mentions=[
                {"behavior": m.behavior, "polarity": m.polarity} for m in signal.behavior_mentions
            ],
            recorded_date=signal.recorded_date,
        )
        try:
            self._db.add(model)
            await self._db.commit()
        except Exception:
            # commit 실패 시 공유 AsyncSession이 invalid 상태로 남아 같은 요청의
            # 후속 DB 작업을 모두 깨뜨린다. rollback으로 세션을 회복한 뒤 재전파한다.
            await self._db.rollback()
            raise

    async def find_by_date_range(
        self, device_id: str, start: date, end: date
    ) -> list[QualitativeSignal]:
        stmt = (
            sa.select(QualitativeSignalModel)
            .where(
                QualitativeSignalModel.device_id == device_id,
                QualitativeSignalModel.recorded_date >= start,
                QualitativeSignalModel.recorded_date <= end,
            )
            .order_by(QualitativeSignalModel.recorded_date)
        )
        result = await self._db.execute(stmt)
        models = result.scalars().all()

        return [
            QualitativeSignal(
                emotion=Emotion(m.emotion),
                behavior_mentions=tuple(
                    BehaviorMention(behavior=item["behavior"], polarity=int(item["polarity"]))
                    for item in (m.behavior_mentions or [])
                ),
                recorded_date=m.recorded_date,
            )
            for m in models
        ]
