"""인사이트 응답 DTO — InsightResult(application) → JSON 직렬화.

DEC-B1: score is None ⟺ signal_count == 0 불변식을 validator로 강제한다.
프론트(wellbeing.tsx)는 signal_count===0으로 empty 화면을 판정하므로,
이 불변식이 지켜지는 한 score=null이 렌더 경로에 도달하지 않는다.
0이 아니라 None인 이유: 게이트가 나중에 제거되면 0은 '매우 나쁨'으로
조용히 잘못 렌더되지만 null은 눈에 띄게 깨져서 즉시 발견된다.
"""

from datetime import date

from pydantic import BaseModel, model_validator

from app.application.usecase.insight_result import InsightResult
from app.domain.model.wellbeing_report import WellbeingReport


class WellbeingReportResponse(BaseModel):
    score: int | None  # 0–100, 기간에 일기가 없으면 null
    emotion_score: float | None  # 기간 일기 satisfaction 평균 (0–100)
    behavior_score: float | None  # 개인 기준선 대비 걸음·수면 (0–100)
    signal_count: int  # DEPRECATED: 프론트 마이그레이션 후 제거. diary_days 사용
    diary_days: int  # satisfaction 관측 일기 일수 (정식 이름)
    lifelog_days: int  # 걸음 또는 수면이 있는 날 수

    @model_validator(mode="after")
    def _enforce_none_invariant(self) -> "WellbeingReportResponse":
        if (self.score is None) != (self.signal_count == 0):
            raise ValueError("score=None과 signal_count=0은 반드시 함께여야 함 (DEC-B1)")
        return self

    @classmethod
    def from_domain(cls, report: WellbeingReport) -> "WellbeingReportResponse":
        return cls(
            score=report.score,
            emotion_score=report.emotion_score,
            behavior_score=report.behavior_score,
            signal_count=report.diary_days,  # 의미 변경: 코칭 신호 수 → 일기 관측 일수
            diary_days=report.diary_days,
            lifelog_days=report.lifelog_days,
        )


class TrendPointResponse(BaseModel):
    label: str
    score: int  # DEC-B2: 일기 없는 버킷은 배열에서 생략되므로 항상 숫자
    signal_count: int


class InsightCardResponse(BaseModel):
    hypothesis_key: str
    title: str
    message: str
    evidence_dates: list[date]


class InsightReportResponse(BaseModel):
    """생성형 주간 인사이트 리포트 — 비생성 상태도 200 well-formed."""

    id: str
    period: str
    start_date: date
    end_date: date
    status: str
    from_cache: bool
    cards: list[InsightCardResponse]
    created_at: str

    @classmethod
    def from_domain(cls, report, start_date: date, end_date: date, from_cache: bool):
        return cls(
            id=str(report.id),
            period=report.period_key,
            start_date=start_date,
            end_date=end_date,
            status=report.status.value,
            from_cache=from_cache,
            cards=[
                InsightCardResponse(
                    hypothesis_key=card.hypothesis_key,
                    title=card.title,
                    message=card.message,
                    evidence_dates=list(card.evidence_dates),
                )
                for card in report.cards
            ],
            created_at=report.created_at.isoformat(),
        )


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
