"""DailyFact 집계 — 날짜 구멍 채우기·결측 None 유지·기준선 안정성 검증."""

from __future__ import annotations

from datetime import date, timedelta

from app.domain.model.diary import Diary
from app.domain.model.emotion import Emotion
from app.domain.model.health_record import HealthDailySummary
from app.domain.model.medical_visit import MedicalVisit, MedicalVisitType
from app.domain.model.sleep_record import SleepRecord
from app.domain.service.insight_aggregation import build_daily_facts, compute_baselines

START = date(2026, 5, 1)
END = START + timedelta(days=89)  # 90일 범위


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


def _sleep(day: date, minutes: int) -> SleepRecord:
    return SleepRecord(device_id="dev-1", record_date=day, duration_minutes=minutes)


def _diary(day: date, satisfaction: int = 60, estimated: bool = False) -> Diary:
    return Diary(
        device_id="dev-1",
        diary_date=day,
        title="t",
        content="c",
        emotion=Emotion.CALM,
        satisfaction=satisfaction,
        satisfaction_estimated=estimated,
    )


def test_fills_date_gaps():
    # 90일 범위에 데이터는 40일치뿐이어도 반환 행 수는 정확히 90 —
    # 행 생략은 후속 lag 계산을 하루씩 밀리게 하는 조용한 버그다.
    summaries = [_summary(START + timedelta(days=i), 7000) for i in range(40)]
    facts = build_daily_facts(summaries, [], [], [], START, END)

    assert len(facts) == 90
    assert [f.date for f in facts] == [START + timedelta(days=i) for i in range(90)]


def test_missing_is_none_not_zero():
    facts = build_daily_facts([], [], [], [], START, START)
    only = facts[0]
    assert only.steps is None
    assert only.sleep_minutes is None
    assert only.satisfaction is None
    assert only.emotion is None
    assert only.has_medical_visit is False


def test_zero_steps_preserved():
    # steps=0은 '하루 종일 안 움직임'이라는 실제 관측 — None으로 바꾸면 안 된다
    facts = build_daily_facts([_summary(START, 0)], [], [], [], START, START)
    assert facts[0].steps == 0


def test_estimated_satisfaction_excluded():
    # PR-A2: LLM 판단 불가(estimated)의 50은 '모름' — 분석에 넣지 않는다.
    # 단 emotion은 사용자가 남긴 관측이므로 유지한다.
    facts = build_daily_facts(
        [], [], [_diary(START, satisfaction=50, estimated=True)], [], START, START
    )
    assert facts[0].satisfaction is None
    assert facts[0].emotion == "calm"


def test_medical_visit_flag():
    visit = MedicalVisit(
        device_id="dev-1",
        visit_date=START,
        visit_type=MedicalVisitType.OUTPATIENT,
        institution="이비인후과",
    )
    facts = build_daily_facts([], [], [], [visit], START, START + timedelta(days=1))
    assert facts[0].has_medical_visit is True
    assert facts[1].has_medical_visit is False


def test_weekend_flag():
    facts = build_daily_facts([], [], [], [], date(2026, 5, 1), date(2026, 5, 3))
    # 2026-05-01 금 / 05-02 토 / 05-03 일
    assert [f.is_weekend for f in facts] == [False, True, True]


def test_baseline_unstable_under_30_days():
    summaries = [_summary(START + timedelta(days=i), 7000) for i in range(29)]
    facts = build_daily_facts(summaries, [], [], [], START, END)
    assert compute_baselines(facts).unstable is True

    summaries = [_summary(START + timedelta(days=i), 7000) for i in range(30)]
    facts = build_daily_facts(summaries, [], [], [], START, END)
    assert compute_baselines(facts).unstable is False


def test_baseline_p75_is_personal_distribution():
    # 절대 기준(1만보)이 아니라 개인 분포의 75분위 —
    # 4000~7000보 사용자의 '많이 걸은 날'은 1만보가 아니다
    summaries = [
        _summary(START + timedelta(days=i), steps)
        for i, steps in enumerate([4000, 5000, 6000, 7000] * 10)
    ]
    facts = build_daily_facts(summaries, [], [], [], START, END)
    baselines = compute_baselines(facts)
    assert baselines.steps_p75 is not None
    assert baselines.steps_p75 < 10000
