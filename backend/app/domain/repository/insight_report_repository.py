from abc import ABC, abstractmethod
from datetime import datetime

from app.domain.model.insight_report import InsightPeriodType, InsightReport


class InsightReportRepository(ABC):
    @abstractmethod
    async def find_by_period(
        self, device_id: str, period_type: InsightPeriodType, period_key: str
    ) -> InsightReport | None:
        """(device_id, period_type, period_key) 캐시 조회."""

    @abstractmethod
    async def find_recent(self, device_id: str, since: datetime) -> list[InsightReport]:
        """created_at >= since 리포트 — 쿨다운 판정용(생성 시각 내림차순)."""

    @abstractmethod
    async def save(self, report: InsightReport) -> InsightReport:
        """저장. 동일 기간 UNIQUE 충돌 시 기존 리포트를 반환한다(재생성 금지 정책)."""
