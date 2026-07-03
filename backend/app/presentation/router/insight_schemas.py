"""인사이트 응답 DTO — InsightResult(application) → JSON 직렬화."""

from datetime import date

from pydantic import BaseModel

from app.application.usecase.insight_result import InsightResult
from app.domain.model.wellbeing_report import WellbeingReport


class WellbeingReportResponse(BaseModel):
    score: int  # 0–100
    emotion_score: int
    behavior_score: int
    signal_count: int

    @classmethod
    def from_domain(cls, report: WellbeingReport) -> "WellbeingReportResponse":
        return cls(
            score=report.score,
            emotion_score=report.emotion_score,
            behavior_score=report.behavior_score,
            signal_count=report.signal_count,
        )


class TrendPointResponse(BaseModel):
    label: str
    score: int
    signal_count: int


class InsightResponse(BaseModel):
    period: str
    start_date: date
    end_date: date
    report: WellbeingReportResponse
    trend: list[TrendPointResponse]

    @classmethod
    def from_result(cls, result: InsightResult) -> "InsightResponse":
        return cls(
            period=result.period,
            start_date=result.start_date,
            end_date=result.end_date,
            report=WellbeingReportResponse.from_domain(result.report),
            trend=[
                TrendPointResponse(label=p.label, score=p.score, signal_count=p.signal_count)
                for p in result.trend
            ],
        )
