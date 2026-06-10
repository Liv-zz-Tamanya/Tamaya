"""인사이트 usecase 결과 DTO — 집계 리포트 + 기간 trend.

스코어러(domain)는 순수하게 유지하고, 기간 라벨·trend 조립은 application 관심사로 둔다.
"""

from dataclasses import dataclass
from datetime import date

from app.domain.model.wellbeing_report import WellbeingReport


@dataclass(frozen=True)
class TrendPoint:
    label: str  # 일별(YYYY-MM-DD) 또는 주별(YYYY-Www) 라벨
    score: int
    signal_count: int


@dataclass(frozen=True)
class InsightResult:
    period: str  # "2026-W23" | "2026-06"
    start_date: date
    end_date: date
    report: WellbeingReport  # 기간 전체 집계
    trend: list[TrendPoint]  # 버킷별 시계열
