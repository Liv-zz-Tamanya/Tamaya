"""주/월 웰빙 인사이트 usecase — 집계 + 버킷 trend (G002-3, TDD).

repo.find_by_date_range로 기간 신호를 모아 순수 스코어러로 집계하고,
주간은 일별, 월간은 주별 trend를 만든다. 빈 기간도 500 없이 well-formed.
"""

from datetime import date

from app.application.usecase.get_monthly_insight import GetMonthlyInsightUseCase
from app.application.usecase.get_weekly_insight import GetWeeklyInsightUseCase
from app.domain.model.emotion import Emotion
from app.domain.model.qualitative_signal import BehaviorMention, QualitativeSignal
from app.domain.repository.qualitative_signal_repository import QualitativeSignalRepository
from app.domain.service.insight_period import week_bounds


class _FakeRepo(QualitativeSignalRepository):
    def __init__(self, signals: list[QualitativeSignal]) -> None:
        self._signals = signals
        self.queried: tuple | None = None

    async def save(self, device_id, session_id, signal) -> None:  # pragma: no cover
        raise NotImplementedError

    async def find_by_date_range(self, device_id, start, end) -> list[QualitativeSignal]:
        self.queried = (device_id, start, end)
        return [s for s in self._signals if start <= s.recorded_date <= end]


def _sig(emotion: Emotion, day: date, mentions=()) -> QualitativeSignal:
    return QualitativeSignal(
        emotion=emotion,
        behavior_mentions=tuple(BehaviorMention(b, p) for b, p in mentions),
        recorded_date=day,
    )


async def test_weekly_aggregate_and_daily_trend():
    start, end = week_bounds(2026, 23)
    signals = [
        _sig(Emotion.HAPPY, start, [("운동", 1)]),
        _sig(Emotion.GRATEFUL, start, [("수면", 1)]),
        _sig(Emotion.SAD, end, [("식사거름", -1)]),
    ]
    repo = _FakeRepo(signals)
    uc = GetWeeklyInsightUseCase(repo)

    result = await uc.execute(device_id="dev-1", year=2026, week=23)

    assert repo.queried == ("dev-1", start, end)
    assert result.period == "2026-W23"
    assert result.start_date == start
    assert result.end_date == end
    # 집계 report는 전체 신호 기준, 긍정이 우세하므로 50 초과
    assert result.report.score > 50
    assert result.report.signal_count == 3
    # 일별 trend는 7포인트(월~일)
    assert len(result.trend) == 7
    assert result.trend[0].score > 50  # 월요일 긍정 2건
    assert result.trend[6].score < 50  # 일요일 부정 1건


async def test_weekly_empty_period_is_well_formed():
    repo = _FakeRepo([])
    uc = GetWeeklyInsightUseCase(repo)

    result = await uc.execute(device_id="dev-1", year=2026, week=23)

    assert result.report.score == 50  # 중립
    assert result.report.signal_count == 0
    assert len(result.trend) == 7
    assert all(p.signal_count == 0 and p.score == 50 for p in result.trend)


async def test_monthly_aggregates_by_week():
    repo = _FakeRepo(
        [
            _sig(Emotion.HAPPY, date(2026, 6, 2), [("운동", 1)]),  # 1주차
            _sig(Emotion.CALM, date(2026, 6, 16), [("산책", 1)]),  # 3주차
        ]
    )
    uc = GetMonthlyInsightUseCase(repo)

    result = await uc.execute(device_id="dev-1", year=2026, month=6)

    assert result.period == "2026-06"
    assert result.start_date == date(2026, 6, 1)
    assert result.end_date == date(2026, 6, 30)
    assert result.report.signal_count == 2
    # 6월이 걸치는 ISO 주차 수만큼 trend 포인트가 생긴다(>=4)
    assert len(result.trend) >= 4
    total_in_trend = sum(p.signal_count for p in result.trend)
    assert total_in_trend == 2


async def test_monthly_empty_period_is_well_formed():
    repo = _FakeRepo([])
    uc = GetMonthlyInsightUseCase(repo)

    result = await uc.execute(device_id="dev-1", year=2026, month=6)

    assert result.report.score == 50
    assert result.report.signal_count == 0
    assert len(result.trend) >= 4
