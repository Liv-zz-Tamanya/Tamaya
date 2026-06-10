"""월간 웰빙 인사이트 usecase — 주별 trend 집계.

기간 신호를 순수 스코어러로 집계하고, 월이 걸치는 각 ISO 주차별 점수를 trend로 만든다.
신호가 없는 주도 score 50·signal_count 0으로 포함해 well-formed를 보장한다(500 금지).
"""

from datetime import timedelta

from app.application.usecase.insight_result import InsightResult, TrendPoint
from app.domain.repository.qualitative_signal_repository import QualitativeSignalRepository
from app.domain.service.insight_period import month_bounds
from app.domain.service.wellbeing_score import compute_wellbeing_score


class GetMonthlyInsightUseCase:
    def __init__(self, repo: QualitativeSignalRepository) -> None:
        self._repo = repo

    async def execute(self, device_id: str, year: int, month: int) -> InsightResult:
        start, end = month_bounds(year, month)
        signals = await self._repo.find_by_date_range(device_id, start, end)

        report = compute_wellbeing_score(signals)

        trend: list[TrendPoint] = []
        for iso_year, iso_week in self._iso_weeks_in_range(start, end):
            week_signals = [
                s
                for s in signals
                if (s.recorded_date.isocalendar().year, s.recorded_date.isocalendar().week)
                == (iso_year, iso_week)
            ]
            week_report = compute_wellbeing_score(week_signals)
            trend.append(
                TrendPoint(
                    label=f"{iso_year}-W{iso_week:02d}",
                    score=week_report.score,
                    signal_count=week_report.signal_count,
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
