"""가설 레지스트리·StatisticalFinding 불변식 검증 (PR-B2)."""

from __future__ import annotations

import pytest

from app.domain.service.insight_hypotheses import (
    FDR_ALPHA,
    MIN_ABS_SPEARMAN_RHO,
    MIN_PAIRED_OBSERVATIONS,
    REGISTERED_HYPOTHESES,
    FindingCoverage,
    GateFailureReason,
    HypothesisPairing,
    InsightTestType,
    StatisticalFinding,
)

COVERAGE = FindingCoverage(
    eligible_days=90, paired_days=61, predictor_observed_days=78, outcome_observed_days=69
)


def _finding(**overrides) -> StatisticalFinding:
    base = dict(
        hypothesis_key="sleep_satisfaction",
        test_type=InsightTestType.SPEARMAN,
        n=61,
        effect_size=0.38,
        p_value=0.002,
        q_value=0.004,
        gate_passed=True,
        coverage=COVERAGE,
        failure_reasons=(),
    )
    base.update(overrides)
    return StatisticalFinding(**base)


def test_registry_has_exactly_two_preregistered_hypotheses():
    # 런타임 가설 생성·컬럼 자동 탐색 금지 정책 — 레지스트리가 유일한 가설 출처다
    assert [h.key for h in REGISTERED_HYPOTHESES] == ["sleep_satisfaction", "steps_satisfaction"]
    assert all(h.test_type == InsightTestType.SPEARMAN for h in REGISTERED_HYPOTHESES)
    # record_date=기상일 규칙에서 same-date가 '지난밤 수면 → 오늘 만족도'다
    assert all(h.pairing == HypothesisPairing.SAME_DATE for h in REGISTERED_HYPOTHESES)
    assert all(h.outcome == "satisfaction" for h in REGISTERED_HYPOTHESES)


def test_policy_constants():
    assert MIN_PAIRED_OBSERVATIONS == 20
    assert FDR_ALPHA == 0.05
    assert MIN_ABS_SPEARMAN_RHO == 0.30


def test_valid_finding_accepted():
    finding = _finding()
    assert finding.gate_passed is True


def test_n_must_match_paired_days():
    with pytest.raises(ValueError):
        _finding(n=60)


def test_gate_passed_requires_empty_failure_reasons():
    with pytest.raises(ValueError):
        _finding(failure_reasons=(GateFailureReason.EFFECT_TOO_SMALL,))


def test_gate_failed_requires_failure_reasons():
    with pytest.raises(ValueError):
        _finding(gate_passed=False, failure_reasons=())


def test_gate_passed_requires_statistics():
    with pytest.raises(ValueError):
        _finding(q_value=None)


def test_p_and_q_range_validated():
    with pytest.raises(ValueError):
        _finding(p_value=1.5)
    with pytest.raises(ValueError):
        _finding(q_value=-0.1)


def test_effect_size_range_validated():
    with pytest.raises(ValueError):
        _finding(effect_size=1.2)


def test_abstained_finding_accepted():
    finding = _finding(
        effect_size=None,
        p_value=None,
        q_value=None,
        gate_passed=False,
        failure_reasons=(GateFailureReason.INSUFFICIENT_SAMPLE,),
        n=3,
        coverage=FindingCoverage(
            eligible_days=90, paired_days=3, predictor_observed_days=13, outcome_observed_days=22
        ),
    )
    assert finding.gate_passed is False
