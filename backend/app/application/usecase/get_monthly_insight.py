"""월간 웰빙 인사이트 usecase — 일기·라이프로그 기반 집계 + 주별 trend.

빈 기간은 score=None·diary_days=0의 well-formed 결과를 반환한다(500 금지).
trend는 일기가 있는 주만 포함한다(DEC-B2).
"""

from datetime import timedelta

from app.application.usecase.insight_facts import load_period_facts
from app.application.usecase.insight_result import InsightResult, TrendPoint
from app.domain.repository.diary_repository import DiaryRepository
from app.domain.repository.health_record_repository import HealthRecordRepository
from app.domain.repository.medical_visit_repository import MedicalVisitRepository
from app.domain.repository.sleep_record_repository import SleepRecordRepository
from app.domain.service.insight_period import month_bounds
from app.domain.service.wellbeing_score import compute_wellbeing


class GetMonthlyInsightUseCase:
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

    async def execute(self, device_id: str, year: int, month: int) -> InsightResult:
        start, end = month_bounds(year, month)
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
        for iso_year, iso_week in self._iso_weeks_in_range(start, end):
            week_facts = [
                f
                for f in facts
                if (f.date.isocalendar().year, f.date.isocalendar().week) == (iso_year, iso_week)
            ]
            week_report = compute_wellbeing(week_facts, baselines)
            if week_report.score is None:  # DEC-B2: 일기 없는 주는 생략
                continue
            trend.append(
                TrendPoint(
                    label=f"{iso_year}-W{iso_week:02d}",
                    score=week_report.score,
                    signal_count=week_report.diary_days,
                )
            )

        return InsightResult(
            period=f"{year}-{month:02d}",
            start_date=start,
            end_date=end,
            report=report,
            trend=trend,
        )

    @staticmethod
    def _iso_weeks_in_range(start, end) -> list[tuple[int, int]]:
        """[start, end]에 걸친 ISO (year, week)를 순서대로 중복 없이 수집한다."""
        weeks: list[tuple[int, int]] = []
        seen: set[tuple[int, int]] = set()
        day = start
        while day <= end:
            iso = day.isocalendar()
            key = (iso.year, iso.week)
            if key not in seen:
                seen.add(key)
                weeks.append(key)
            day += timedelta(days=1)
        return weeks
