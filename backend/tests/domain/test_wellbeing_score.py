"""웰빙 스코어러(재정의) — None 정직성·이상치 클립·코칭 독립 검증.

이전 정의(코칭 정성신호 기여분)의 테스트를 대체한다 (DEC-B5).
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

from app.domain.service.insight_models import Baselines, DailyFact
from app.domain.service.wellbeing_score import compute_wellbeing

START = date(2026, 6, 1)

STABLE_BASELINES = Baselines(
    steps_mean=7500.0,
    steps_stdev=1500.0,
    sleep_mean=430.0,
    sleep_stdev=45.0,
    steps_p75=8500.0,
    observed_days=80,
    unstable=False,
)

UNSTABLE_BASELINES = Baselines(
    steps_mean=7500.0,
    steps_stdev=1500.0,
    sleep_mean=None,
    sleep_stdev=None,
    steps_p75=None,
    observed_days=5,
    unstable=True,
)


def _fact(
    day: date,
    steps: int | None = None,
    sleep: int | None = None,
    satisfaction: int | None = None,
) -> DailyFact:
    return DailyFact(
        date=day,
        steps=steps,
        sleep_minutes=sleep,
        satisfaction=satisfaction,
        emotion="calm" if satisfaction is not None else None,
        has_medical_visit=False,
        steps_p75=None,
        is_weekend=day.weekday() >= 5,
    )


def _week(satisfactions, steps=7500, sleep=430) -> list[DailyFact]:
    return [
        _fact(START + timedelta(days=i), steps=steps, sleep=sleep, satisfaction=s)
        for i, s in enumerate(satisfactions)
    ]


def test_no_diary_returns_none_not_zero():
    # 0은 '매우 나쁨'으로 읽히지만 실제 의미는 '모름' — 반드시 None
    facts = [_fact(START + timedelta(days=i), steps=8000, sleep=420) for i in range(7)]
    report = compute_wellbeing(facts, STABLE_BASELINES)

    assert report.score is None
    assert report.emotion_score is None
    assert report.behavior_score is None
    assert report.diary_days == 0
    assert report.lifelog_days == 7
    assert report.is_partial is True


def test_score_none_iff_diary_days_zero():
    # DEC-B1 불변식의 도메인 측 절반: score is None ⟺ diary_days == 0
    empty = compute_wellbeing([], STABLE_BASELINES)
    assert empty.score is None and empty.diary_days == 0

    with_diary = compute_wellbeing(_week([60] * 7), STABLE_BASELINES)
    assert with_diary.score is not None and with_diary.diary_days == 7


def test_diary_only_period_scores_with_neutral_behavior():
    # 라이프로그가 없어도 일기가 있으면 점수는 나온다 — 행동 축은 중립 50
    facts = [_fact(START + timedelta(days=i), satisfaction=80) for i in range(7)]
    report = compute_wellbeing(facts, STABLE_BASELINES)

    assert report.behavior_score == 50.0
    assert report.score == round(0.6 * 80 + 0.4 * 50)
    assert report.is_partial is True


def test_unstable_baseline_neutralizes_behavior():
    facts = _week([60] * 7, steps=12000, sleep=520)  # 평소보다 훨씬 활동적이어도
    report = compute_wellbeing(facts, UNSTABLE_BASELINES)
    assert report.behavior_score == 50.0  # 관측 30일 미만 — 판단 유보


def test_outlier_day_clipped():
    # 16,388걸음 하루가 주간 score를 5점 이상 흔들면 안 된다 (일별 winsorize)
    normal = compute_wellbeing(_week([60] * 7, steps=7500), STABLE_BASELINES)
    facts = _week([60] * 7, steps=7500)
    facts[3] = _fact(START + timedelta(days=3), steps=16388, sleep=430, satisfaction=60)
    outlier = compute_wellbeing(facts, STABLE_BASELINES)

    assert abs(outlier.score - normal.score) <= 5


def test_good_week_beats_bad_week():
    good = compute_wellbeing(_week([85] * 7, steps=9000, sleep=460), STABLE_BASELINES)
    bad = compute_wellbeing(_week([30] * 7, steps=4500, sleep=330), STABLE_BASELINES)
    assert good.score - bad.score >= 30  # 중앙 수렴(둘 다 55쯤)이 없어야 한다


def test_score_range():
    # 랜덤 픽스처 1000개에서 항상 0~100 또는 None
    rng = random.Random(42)
    for _ in range(1000):
        facts = []
        for i in range(rng.randint(0, 14)):
            facts.append(
                _fact(
                    START + timedelta(days=i),
                    steps=rng.choice([None, rng.randint(0, 40000)]),
                    sleep=rng.choice([None, rng.randint(1, 1440)]),
                    satisfaction=rng.choice([None, rng.randint(0, 100)]),
                )
            )
        report = compute_wellbeing(facts, STABLE_BASELINES)
        if report.score is None:
            assert report.diary_days == 0
        else:
            assert 0 <= report.score <= 100


def test_no_coaching_dependency():
    """새 인사이트 경로가 코칭 산출물(QualitativeSignal)을 임포트하지 않는다 (정적 검사)."""
    app_root = Path(__file__).resolve().parents[2] / "app"
    insight_paths = [
        app_root / "domain" / "service" / "wellbeing_score.py",
        app_root / "domain" / "service" / "insight_aggregation.py",
        app_root / "domain" / "service" / "insight_models.py",
        app_root / "domain" / "model" / "wellbeing_report.py",
        app_root / "application" / "usecase" / "insight_facts.py",
        app_root / "application" / "usecase" / "get_weekly_insight.py",
        app_root / "application" / "usecase" / "get_monthly_insight.py",
    ]
    offenders = [
        str(path)
        for path in insight_paths
        if "qualitative_signal import" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []
