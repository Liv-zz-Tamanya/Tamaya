"""주간 웰빙 인사이트 usecase — 일기·라이프로그 기반 집계 + 일별 trend.

빈 기간은 score=None·diary_days=0의 well-formed 결과를 반환한다(500 금지).
trend는 일기가 있는 날만 포함한다(DEC-B2) — null이 섞이면 프론트의
Math.max 계산이 NaN이 되므로 희소 시계열로 유지한다.
"""

from app.application.usecase.insight_facts import load_period_facts
from app.application.usecase.insight_result import InsightResult, TrendPoint
from app.domain.repository.diary_repository import DiaryRepository
from app.domain.repository.health_record_repository import HealthRecordRepository
from app.domain.repository.medical_visit_repository import MedicalVisitRepository
from app.domain.repository.sleep_record_repository import SleepRecordRepository
from app.domain.service.insight_period import week_bounds
from app.domain.service.wellbeing_score import compute_wellbeing


class GetWeeklyInsightUseCase:
    def __init__(
        self,
        health_repo: HealthRecordRepository,
        sleep_repo: SleepRecordRepository,
        diary_repo: DiaryRepository,
        visit_repo: MedicalVisitRepository,
    ) -> None:
        self._health_repo = health_repo
        self._sleep_repo = sleep_repo
        self._diary_repo = diary_repo
        self._visit_repo = visit_repo

    async def execute(self, device_id: str, year: int, week: int) -> InsightResult:
        start, end = week_bounds(year, week)
        facts, baselines = await load_period_facts(
            self._health_repo,
            self._sleep_repo,
            self._diary_repo,
            self._visit_repo,
            device_id,
            start,
            end,
        )

        report = compute_wellbeing(facts, baselines)

        trend: list[TrendPoint] = []
        for fact in facts:
            day_report = compute_wellbeing([fact], baselines)
            if day_report.score is None:  # DEC-B2: 일기 없는 날은 생략
                continue
            trend.append(
                TrendPoint(
                    label=fact.date.isoformat(),
                    score=day_report.score,
                    signal_count=day_report.diary_days,
                )
            )

        return InsightResult(
            period=f"{year}-W{week:02d}",
            start_date=start,
            end_date=end,
            report=report,
            trend=trend,
        )
