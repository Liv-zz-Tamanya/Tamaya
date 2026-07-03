"""주간 웰빙 인사이트 usecase — 일별 trend 집계.

기간 신호를 순수 스코어러로 집계하고, 월~일 7일 각각의 점수를 trend로 만든다.
빈 기간도 score 50·signal_count 0의 well-formed 결과를 반환한다(500 금지).
"""

from datetime import timedelta

from app.application.usecase.insight_result import InsightResult, TrendPoint
from app.domain.repository.qualitative_signal_repository import QualitativeSignalRepository
from app.domain.service.insight_period import week_bounds
from app.domain.service.wellbeing_score import compute_wellbeing_score


class GetWeeklyInsightUseCase:
    def __init__(self, repo: QualitativeSignalRepository) -> None:
        self._repo = repo

    async def execute(self, device_id: str, year: int, week: int) -> InsightResult:
        start, end = week_bounds(year, week)
        signals = await self._repo.find_by_date_range(device_id, start, end)

        report = compute_wellbeing_score(signals)

        trend: list[TrendPoint] = []
        for offset in range(7):
            day = start + timedelta(days=offset)
            day_signals = [s for s in signals if s.recorded_date == day]
            day_report = compute_wellbeing_score(day_signals)
            trend.append(
                TrendPoint(
                    label=day.isoformat(),
                    score=day_report.score,
                    signal_count=day_report.signal_count,
                )
            )

        return InsightResult(
            period=f"{year}-W{week:02d}",
            start_date=start,
            end_date=end,
            report=report,
            trend=trend,
        )
