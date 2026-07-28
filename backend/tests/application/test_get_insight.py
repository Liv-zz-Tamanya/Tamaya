"""주/월 웰빙 인사이트 usecase — 일기·라이프로그 집계 + DEC-B2 trend.

빈 기간 계약(DEC-B3): 500이 아니라 well-formed 결과 — 단 이전의 '중립 50'이
아니라 score=None·diary_days=0으로 '모름'을 정직하게 표현한다.
"""

from __future__ import annotations

from datetime import date, timedelta

from app.application.usecase.get_monthly_insight import GetMonthlyInsightUseCase
from app.application.usecase.get_weekly_insight import GetWeeklyInsightUseCase
from app.domain.model.diary import Diary
from app.domain.model.emotion import Emotion
from app.domain.model.health_record import HealthDailySummary
from app.domain.model.medical_visit import MedicalVisit
from app.domain.model.sleep_record import SleepRecord
from app.domain.repository.diary_repository import DiaryRepository
from app.domain.repository.health_record_repository import HealthRecordRepository
from app.domain.repository.medical_visit_repository import MedicalVisitRepository
from app.domain.repository.sleep_record_repository import SleepRecordRepository
from app.domain.service.insight_period import week_bounds


class FakeHealthRepo(HealthRecordRepository):
    def __init__(self, records: list[HealthDailySummary] | None = None) -> None:
        self._records = records or []
        self.queried: tuple | None = None

    async def save(self, record):  # pragma: no cover
        raise NotImplementedError

    async def find_by_date(self, device_id, record_date):  # pragma: no cover
        raise NotImplementedError

    async def find_by_date_range(self, device_id, start, end):
        self.queried = (device_id, start, end)
        return [r for r in self._records if start <= r.record_date <= end]

    async def find_all(self, device_id):  # pragma: no cover
        raise NotImplementedError

    async def source_hash_exists(self, device_id, source_hash):  # pragma: no cover
        raise NotImplementedError


class FakeSleepRepo(SleepRecordRepository):
    def __init__(self, records: list[SleepRecord] | None = None) -> None:
        self._records = records or []

    async def upsert_all(self, records):  # pragma: no cover
        raise NotImplementedError

    async def find_by_date_range(self, device_id, start, end):
        return [r for r in self._records if start <= r.record_date <= end]


class FakeDiaryRepo(DiaryRepository):
    def __init__(self, diaries: list[Diary] | None = None) -> None:
        self._diaries = diaries or []

    async def save(self, diary):  # pragma: no cover
        raise NotImplementedError

    async def find_by_id(self, diary_id):  # pragma: no cover
        raise NotImplementedError

    async def find_by_device_and_date(self, device_id, diary_date):  # pragma: no cover
        raise NotImplementedError

    async def find_by_date_range(self, device_id, start, end):
        return [d for d in self._diaries if start <= d.diary_date <= end]

    async def find_all(self, device_id, offset=0, limit=20):  # pragma: no cover
        raise NotImplementedError

    async def count(self, device_id):  # pragma: no cover
        raise NotImplementedError


class FakeVisitRepo(MedicalVisitRepository):
    def __init__(self, visits: list[MedicalVisit] | None = None) -> None:
        self._visits = visits or []

    async def upsert_all(self, visits):  # pragma: no cover
        raise NotImplementedError

    async def find_by_date_range(self, device_id, start, end):
        return [v for v in self._visits if start <= v.visit_date <= end]


def _summary(day: date, steps: int) -> HealthDailySummary:
    return HealthDailySummary(
        device_id="dev-1",
        record_date=day,
        step_count=steps,
        step_goal=10000,
        step_goal_achieved=steps >= 10000,
        step_calories=steps * 0.04,
        step_distance_m=steps * 0.75,
        has_exercise=False,
        exercise_duration_sec=0,
        exercise_distance_m=0.0,
        exercise_calories=0.0,
        heart_rate_avg=None,
        heart_rate_min=None,
        heart_rate_max=None,
        floors_climbed=0,
        source_hash=f"myhr-{day.isoformat()}",
    )


def _diary(day: date, satisfaction: int, estimated: bool = False) -> Diary:
    return Diary(
        device_id="dev-1",
        diary_date=day,
        title="t",
        content="c",
        emotion=Emotion.CALM,
        satisfaction=satisfaction,
        satisfaction_estimated=estimated,
    )


def _weekly_usecase(
    diaries: list[Diary] | None = None,
    summaries: list[HealthDailySummary] | None = None,
    sleeps: list[SleepRecord] | None = None,
) -> tuple[GetWeeklyInsightUseCase, FakeHealthRepo]:
    health = FakeHealthRepo(summaries)
    uc = GetWeeklyInsightUseCase(health, FakeSleepRepo(sleeps), FakeDiaryRepo(diaries), FakeVisitRepo())
    return uc, health


async def test_weekly_aggregate_and_daily_trend():
    start, end = week_bounds(2026, 23)
    diaries = [_diary(start, 80), _diary(start + timedelta(days=1), 70), _diary(end, 30)]
    uc, health = _weekly_usecase(diaries=diaries)

    result = await uc.execute(device_id="dev-1", year=2026, week=23)

    assert result.period == "2026-W23"
    assert result.start_date == start
    assert result.end_date == end
    assert result.report.score is not None
    assert result.report.diary_days == 3
    # DEC-B2: 일기 있는 3일만 trend에 포함 — null 포인트 없음
    assert len(result.trend) == 3
    assert [p.label for p in result.trend] == [
        start.isoformat(),
        (start + timedelta(days=1)).isoformat(),
        end.isoformat(),
    ]
    assert all(p.score is not None for p in result.trend)
    # 기준선 계산을 위해 최근 90일 창을 조회한다
    assert health.queried == ("dev-1", end - timedelta(days=89), end)


async def test_weekly_empty_period_is_well_formed():
    # DEC-B3: 500 금지 계약은 유지하되 '중립 50'이 아니라 '모름(None)'
    uc, _ = _weekly_usecase()

    result = await uc.execute(device_id="dev-1", year=2026, week=23)

    assert result.report.score is None
    assert result.report.diary_days == 0
    assert result.trend == []


async def test_weekly_lifelog_only_period_has_none_score():
    # 걸음·수면만 있고 일기가 없는 주 — score=None → 스키마에서 signal_count=0
    start, end = week_bounds(2026, 23)
    summaries = [_summary(start + timedelta(days=i), 8000) for i in range(7)]
    sleeps = [
        SleepRecord(device_id="dev-1", record_date=start + timedelta(days=i), duration_minutes=420)
        for i in range(7)
    ]
    uc, _ = _weekly_usecase(summaries=summaries, sleeps=sleeps)

    result = await uc.execute(device_id="dev-1", year=2026, week=23)

    assert result.report.score is None
    assert result.report.diary_days == 0
    assert result.report.lifelog_days == 7
    assert result.trend == []


async def test_weekly_trend_excludes_estimated_only_days():
    # estimated 일기만 있는 날은 '모름' — trend에 나타나지 않는다 (PR-A2 연계)
    start, _ = week_bounds(2026, 23)
    diaries = [_diary(start, 60), _diary(start + timedelta(days=1), 50, estimated=True)]
    uc, _ = _weekly_usecase(diaries=diaries)

    result = await uc.execute(device_id="dev-1", year=2026, week=23)

    assert result.report.diary_days == 1
    assert len(result.trend) == 1
    assert result.trend[0].label == start.isoformat()


async def test_monthly_aggregates_by_week():
    diaries = [_diary(date(2026, 6, 2), 70), _diary(date(2026, 6, 16), 60)]
    uc = GetMonthlyInsightUseCase(
        FakeHealthRepo(), FakeSleepRepo(), FakeDiaryRepo(diaries), FakeVisitRepo()
    )

    result = await uc.execute(device_id="dev-1", year=2026, month=6)

    assert result.period == "2026-06"
    assert result.start_date == date(2026, 6, 1)
    assert result.end_date == date(2026, 6, 30)
    assert result.report.diary_days == 2
    # DEC-B2: 일기가 있는 2개 주만 trend에 포함
    assert len(result.trend) == 2
    assert sum(p.signal_count for p in result.trend) == 2


async def test_monthly_empty_period_is_well_formed():
    uc = GetMonthlyInsightUseCase(FakeHealthRepo(), FakeSleepRepo(), FakeDiaryRepo(), FakeVisitRepo())

    result = await uc.execute(device_id="dev-1", year=2026, month=6)

    assert result.report.score is None
    assert result.report.diary_days == 0
    assert result.trend == []
