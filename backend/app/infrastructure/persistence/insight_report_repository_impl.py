from datetime import date, datetime

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.model.insight_report import (
    InsightCard,
    InsightPeriodType,
    InsightReport,
    InsightReportStatus,
)
from app.domain.repository.insight_report_repository import InsightReportRepository
from app.infrastructure.persistence.models import InsightReportModel


class InsightReportRepositoryImpl(InsightReportRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def find_by_period(
        self, device_id: str, period_type: InsightPeriodType, period_key: str
    ) -> InsightReport | None:
        stmt = sa.select(InsightReportModel).where(
            InsightReportModel.device_id == device_id,
            InsightReportModel.period_type == period_type.value,
            InsightReportModel.period_key == period_key,
        )
        result = await self._db.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def find_recent(self, device_id: str, since: datetime) -> list[InsightReport]:
        stmt = (
            sa.select(InsightReportModel)
            .where(
                InsightReportModel.device_id == device_id,
                InsightReportModel.created_at >= since,
            )
            .order_by(InsightReportModel.created_at.desc())
        )
        result = await self._db.execute(stmt)
        return [self._to_domain(m) for m in result.scalars().all()]

    async def save(self, report: InsightReport) -> InsightReport:
        self._db.add(
            InsightReportModel(
                id=report.id,
                device_id=report.device_id,
                period_type=report.period_type.value,
                period_key=report.period_key,
                payload=report.payload,
                model_meta=report.model_meta,
                created_at=report.created_at,
                updated_at=report.updated_at,
            )
        )
        try:
            await self._db.commit()
        except IntegrityError:
            # 동시 요청이 같은 기간을 생성한 경우 — 캐시 우선 정책이므로
            # 500으로 흘리지 않고 먼저 저장된 리포트를 반환한다.
            await self._db.rollback()
            existing = await self.find_by_period(
                report.device_id, report.period_type, report.period_key
            )
            if existing is None:
                raise
            return existing
        return report

    @staticmethod
    def _to_domain(model: InsightReportModel) -> InsightReport:
        payload = model.payload
        cards = tuple(
            InsightCard(
                hypothesis_key=card["hypothesis_key"],
                title=card["title"],
                message=card["message"],
                evidence_dates=tuple(
                    date.fromisoformat(value) for value in card.get("evidence_dates", [])
                ),
            )
            for card in payload.get("cards", [])
        )
        return InsightReport(
            id=model.id,
            device_id=model.device_id,
            period_type=InsightPeriodType(model.period_type),
            period_key=model.period_key,
            status=InsightReportStatus(payload["status"]),
            cards=cards,
            selected_hypothesis_keys=tuple(
                model.model_meta.get("selected_hypothesis_keys", [])
            ),
            payload=payload,
            model_meta=model.model_meta,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
