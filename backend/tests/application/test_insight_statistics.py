"""인사이트 통계 게이트 — paired 추출·검정·BH 보정·게이트·회귀 검증.

전부 순수 fixture로 완결된다(DB·LLM 없음).
null 300-seed 거짓양성 회귀가 이 파일의 핵심 테스트다.
"""

from __future__ import annotations

import dataclasses
import random
from datetime import date, timedelta

import pytest

from app.application.service.insight_statistics import benjamini_hochberg, evaluate_hypotheses
from app.domain.service.insight_hypotheses import GateFailureReason
from app.domain.service.insight_models import DailyFact
from evals.lifelog_generator import PROFILES, LifelogFixture, generate_lifelog

START = date(2026, 5, 1)
GENERATOR_END = date(2026, 7, 27)


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


def _sleep_facts(pairs: list[tuple[int | None, int | None]]) -> list[DailyFact]:
    """(sleep, satisfaction) 목록을 연속 날짜 DailyFact로 만든다."""
    return [
        _fact(START + timedelta(days=i), sleep=sleep, satisfaction=satisfaction)
        for i, (sleep, satisfaction) in enumerate(pairs)
    ]


def _facts_from_fixture(fixture: LifelogFixture) -> list[DailyFact]:
    """생성기 산출물을 DailyFact[]로 변환한다 (DB·repository 미사용)."""
    start = date.fromisoformat(fixture.meta["start_date"])
    end = date.fromisoformat(fixture.meta["end_date"])
    sleep_by = {r["record_date"]: r["duration_minutes"] for r in fixture.sleep_records}
    steps_by = {r["record_date"]: r["step_count"] for r in fixture.health_summaries}
    satisfaction_by = {
        r["diary_date"]: r["satisfaction"]
        for r in fixture.diaries
        if not r["satisfaction_estimated"]
    }
    facts = []
    day = start
    while day <= end:
        key = day.isoformat()
        facts.append(
            _fact(
                day,
                steps=steps_by.get(key),
                sleep=sleep_by.get(key),
                satisfaction=satisfaction_by.get(key),
            )
        )
        day += timedelta(days=1)
    return facts


def _by_key(findings):
    return {f.hypothesis_key: f for f in findings}


# ── paired sample 추출 ──────────────────────────────────────────────────────


def test_pairs_use_only_days_with_both_observations():
    # sleep 관측 0~19일, satisfaction 관측 10~29일 → 교집합 10일만 검정 대상
    facts = []
    for i in range(30):
        day = START + timedelta(days=i)
        facts.append(
            _fact(
                day,
                sleep=400 + i if i < 20 else None,
                satisfaction=50 + i if i >= 10 else None,
            )
        )
    finding = _by_key(evaluate_hypotheses(facts))["sleep_satisfaction"]

    assert finding.coverage.eligible_days == 30
    assert finding.coverage.predictor_observed_days == 20
    assert finding.coverage.outcome_observed_days == 20
    assert finding.coverage.paired_days == 10
    assert finding.n == 10
    assert finding.failure_reasons == (GateFailureReason.INSUFFICIENT_SAMPLE,)
    assert finding.effect_size is None and finding.p_value is None and finding.q_value is None


def test_zero_steps_is_observation_not_missing():
    facts = [
        _fact(START + timedelta(days=i), steps=0 if i % 2 == 0 else 8000, satisfaction=50 + i)
        for i in range(24)
    ]
    finding = _by_key(evaluate_hypotheses(facts))["steps_satisfaction"]
    assert finding.coverage.predictor_observed_days == 24  # 0보도 관측이다
    assert finding.n == 24


def test_same_date_pairing_not_lagged():
    # 수면과 만족도를 same-date로 완전 동조시킨다. 구현이 하루라도 밀리면
    # 상관 부호가 반전되므로(교대 패턴) 즉시 잡힌다.
    pairs = [(300, 40) if i % 2 == 0 else (500, 80) for i in range(24)]
    finding = _by_key(evaluate_hypotheses(_sleep_facts(pairs)))["sleep_satisfaction"]

    assert finding.effect_size is not None and finding.effect_size > 0.9
    assert finding.gate_passed is True
    assert finding.failure_reasons == ()


def test_estimated_none_satisfaction_rows_excluded():
    # DailyFact.satisfaction=None(estimated 일기 포함)은 페어에서 빠진다
    pairs = [(400 + i, 50 + i) for i in range(25)]
    facts = _sleep_facts(pairs)
    facts[5] = _fact(START + timedelta(days=5), sleep=430, satisfaction=None)
    finding = _by_key(evaluate_hypotheses(facts))["sleep_satisfaction"]
    assert finding.n == 24


# ── 실패 사유 ───────────────────────────────────────────────────────────────


def test_insufficient_sample_below_threshold():
    pairs = [(400 + i, 50 + i) for i in range(19)]  # n=19 < 20
    finding = _by_key(evaluate_hypotheses(_sleep_facts(pairs)))["sleep_satisfaction"]
    assert finding.failure_reasons == (GateFailureReason.INSUFFICIENT_SAMPLE,)
    assert finding.gate_passed is False


def test_constant_input_detected():
    pairs = [(420, 40 + (i * 7) % 30) for i in range(25)]  # 수면이 상수
    finding = _by_key(evaluate_hypotheses(_sleep_facts(pairs)))["sleep_satisfaction"]
    assert finding.failure_reasons == (GateFailureReason.CONSTANT_INPUT,)
    assert finding.effect_size is None


def test_effect_too_small_only():
    # 약한 진짜 효과(rho~0.2) + 큰 표본 → 유의하지만 효과크기 게이트 탈락
    rng = random.Random(7)
    pairs = []
    for _ in range(240):
        sleep = rng.gauss(430, 45)
        satisfaction = 60 + 0.2 * (sleep - 430) / 45 * 10 + rng.gauss(0, 10)
        pairs.append((round(sleep), round(max(0, min(100, satisfaction)))))
    finding = _by_key(evaluate_hypotheses(_sleep_facts(pairs)))["sleep_satisfaction"]

    assert finding.failure_reasons == (GateFailureReason.EFFECT_TOO_SMALL,)
    assert finding.q_value is not None and finding.q_value <= 0.05
    assert abs(finding.effect_size) < 0.30


def test_not_significant_only():
    # 표본이 작으면 |rho|>=0.30이어도 유의하지 않을 수 있다
    rng = random.Random(1)  # 실측 rho=0.385, p=0.094
    pairs = []
    for _ in range(20):
        sleep = rng.gauss(430, 45)
        satisfaction = 60 + 0.35 * (sleep - 430) / 45 * 10 + rng.gauss(0, 10)
        pairs.append((round(sleep), round(max(0, min(100, satisfaction)))))
    finding = _by_key(evaluate_hypotheses(_sleep_facts(pairs)))["sleep_satisfaction"]

    assert finding.failure_reasons == (GateFailureReason.NOT_SIGNIFICANT,)
    assert abs(finding.effect_size) >= 0.30
    assert finding.q_value > 0.05


def test_both_failure_reasons_in_fixed_order():
    rng = random.Random(3)
    pairs = [(round(rng.gauss(430, 45)), round(rng.gauss(60, 10))) for _ in range(60)]
    finding = _by_key(evaluate_hypotheses(_sleep_facts(pairs)))["sleep_satisfaction"]

    assert finding.failure_reasons == (
        GateFailureReason.EFFECT_TOO_SMALL,
        GateFailureReason.NOT_SIGNIFICANT,
    )


def test_negative_correlation_can_pass_gate():
    # 부호를 보존해야 한다 — 음의 상관도 유효 후보다
    rng = random.Random(5)
    pairs = []
    for _ in range(40):
        sleep = rng.gauss(430, 45)
        satisfaction = 60 - 0.8 * (sleep - 430) / 45 * 10 + rng.gauss(0, 4)
        pairs.append((round(sleep), round(max(0, min(100, satisfaction)))))
    finding = _by_key(evaluate_hypotheses(_sleep_facts(pairs)))["sleep_satisfaction"]

    assert finding.effect_size < 0
    assert abs(finding.effect_size) >= 0.30
    assert finding.q_value <= 0.05
    assert finding.gate_passed is True


# ── BH FDR 보정 ─────────────────────────────────────────────────────────────


def test_bh_known_values_and_order_restored():
    # 정렬 p [0.01, 0.03, 0.04] → adj [0.03, 0.045, 0.04] → 역방향 최소 [0.03, 0.04, 0.04]
    qs = benjamini_hochberg([0.01, 0.04, 0.03])
    assert qs == pytest.approx([0.03, 0.04, 0.04])


def test_bh_monotone_in_p():
    ps = [0.001, 0.02, 0.02, 0.4, 0.9]
    qs = benjamini_hochberg(ps)
    ordered = [q for _, q in sorted(zip(ps, qs, strict=True))]
    assert ordered == sorted(ordered)


def test_bh_clamped_to_one():
    assert benjamini_hochberg([1.0, 0.9]) == [1.0, 1.0]


def test_bh_single_p_equals_q():
    assert benjamini_hochberg([0.2]) == [0.2]


def test_bh_family_excludes_untested_hypotheses():
    # steps가 전부 결측이면 steps 가설은 family에서 빠지고 sleep의 q == p
    pairs = [(400 + (i * 13) % 60, 45 + (i * 7) % 40) for i in range(30)]
    findings = _by_key(evaluate_hypotheses(_sleep_facts(pairs)))

    steps = findings["steps_satisfaction"]
    assert steps.failure_reasons == (GateFailureReason.INSUFFICIENT_SAMPLE,)
    assert steps.q_value is None

    sleep = findings["sleep_satisfaction"]
    assert sleep.q_value == pytest.approx(sleep.p_value)


# ── 생성기 연동 회귀 ────────────────────────────────────────────────────────


def test_planted_strong_both_hypotheses_detected():
    fixture = generate_lifelog(PROFILES["planted_strong"], "eval-planted-01", GENERATOR_END)
    findings = _by_key(evaluate_hypotheses(_facts_from_fixture(fixture)))

    for key in ("sleep_satisfaction", "steps_satisfaction"):
        finding = findings[key]
        assert finding.gate_passed is True, (key, finding)
        assert finding.n >= 20
        assert abs(finding.effect_size) >= 0.30
        assert finding.q_value <= 0.05


def test_sparse_profile_abstains_on_insufficient_sample():
    fixture = generate_lifelog(PROFILES["sparse"], "eval-sparse-01", GENERATOR_END)
    findings = _by_key(evaluate_hypotheses(_facts_from_fixture(fixture)))

    sleep = findings["sleep_satisfaction"]
    assert sleep.gate_passed is False
    assert GateFailureReason.INSUFFICIENT_SAMPLE in sleep.failure_reasons

    # steps도 coverage(0.30)×diary(0.25)라 기대 페어 ~7일 — 현 seed 실측도 표본 부족
    steps = findings["steps_satisfaction"]
    assert steps.gate_passed is False
    assert GateFailureReason.INSUFFICIENT_SAMPLE in steps.failure_reasons


def test_null_300_seeds_false_positive_rate_under_10_percent():
    """가장 중요한 회귀 — 순수 노이즈에서 게이트가 열리는 seed가 10%를 넘으면 안 된다.

    seed 범위는 NULL_SEED_BASE + [0, 300) 으로 고정한다.
    """
    NULL_SEED_BASE = 900_000
    false_positive_seeds = 0
    passes_per_hypothesis = {"sleep_satisfaction": 0, "steps_satisfaction": 0}

    for offset in range(300):
        profile = dataclasses.replace(PROFILES["null"], seed=NULL_SEED_BASE + offset)
        fixture = generate_lifelog(profile, "eval-null-sweep", GENERATOR_END)
        findings = evaluate_hypotheses(_facts_from_fixture(fixture))
        passed = [f for f in findings if f.gate_passed]
        if passed:
            false_positive_seeds += 1
            for finding in passed:
                passes_per_hypothesis[finding.hypothesis_key] += 1

    rate = false_positive_seeds / 300
    assert rate <= 0.10, (
        f"any-candidate false-positive seed rate={rate:.3f} "
        f"({false_positive_seeds}/300), "
        f"sleep passes={passes_per_hypothesis['sleep_satisfaction']}, "
        f"steps passes={passes_per_hypothesis['steps_satisfaction']}, "
        f"total passed candidates={sum(passes_per_hypothesis.values())}"
    )
