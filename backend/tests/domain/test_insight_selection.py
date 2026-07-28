"""후보 선정·쿨다운·근거 날짜 — 순수 결정론 함수 검증."""

from __future__ import annotations

from datetime import date, timedelta

from app.domain.model.insight_report import InsightCard, InsightReport, InsightReportStatus
from app.domain.service.insight_hypotheses import (
    REGISTERED_HYPOTHESES,
    FindingCoverage,
    GateFailureReason,
    InsightTestType,
    StatisticalFinding,
)
from app.domain.service.insight_models import DailyFact
from app.domain.service.insight_selection import (
    InsightSelectionOutcome,
    select_evidence_dates,
    select_insight_candidates,
)

START = date(2026, 7, 27)


def _finding(
    key: str = "sleep_satisfaction",
    effect: float | None = 0.4,
    q: float | None = 0.01,
    gate_passed: bool = True,
    failure_reasons: tuple = (),
) -> StatisticalFinding:
    return StatisticalFinding(
        hypothesis_key=key,
        test_type=InsightTestType.SPEARMAN,
        n=60,
        effect_size=effect,
        p_value=q,
        q_value=q,
        gate_passed=gate_passed,
        coverage=FindingCoverage(90, 60, 70, 65),
        failure_reasons=failure_reasons,
    )


def _abstained(key: str) -> StatisticalFinding:
    return StatisticalFinding(
        hypothesis_key=key,
        test_type=InsightTestType.SPEARMAN,
        n=3,
        effect_size=None,
        p_value=None,
        q_value=None,
        gate_passed=False,
        coverage=FindingCoverage(90, 3, 10, 12),
        failure_reasons=(GateFailureReason.INSUFFICIENT_SAMPLE,),
    )


def _fact(day: date, sleep: int | None, satisfaction: int | None) -> DailyFact:
    return DailyFact(
        date=day,
        steps=None,
        sleep_minutes=sleep,
        satisfaction=satisfaction,
        emotion="calm" if satisfaction is not None else None,
        has_medical_visit=False,
        steps_p75=None,
        is_weekend=day.weekday() >= 5,
    )


def test_only_gate_passed_selected():
    result = select_insight_candidates(
        [
            _finding("sleep_satisfaction"),
            _finding(
                "steps_satisfaction",
                effect=0.1,
                q=0.5,
                gate_passed=False,
                failure_reasons=(
                    GateFailureReason.EFFECT_TOO_SMALL,
                    GateFailureReason.NOT_SIGNIFICANT,
                ),
            ),
        ],
        recently_exposed_hypothesis_keys=(),
    )
    assert result.outcome == InsightSelectionOutcome.SELECTED
    assert [f.hypothesis_key for f in result.selected] == ["sleep_satisfaction"]


def test_cooldown_key_excluded():
    result = select_insight_candidates(
        [_finding("sleep_satisfaction"), _finding("steps_satisfaction", effect=0.35, q=0.02)],
        recently_exposed_hypothesis_keys={"sleep_satisfaction"},
    )
    assert [f.hypothesis_key for f in result.selected] == ["steps_satisfaction"]


def test_all_passed_in_cooldown_returns_cooldown():
    result = select_insight_candidates(
        [_finding("sleep_satisfaction")],
        recently_exposed_hypothesis_keys={"sleep_satisfaction"},
    )
    assert result.outcome == InsightSelectionOutcome.COOLDOWN
    assert result.selected == ()


def test_insufficient_data_when_nothing_testable():
    result = select_insight_candidates(
        [_abstained("sleep_satisfaction"), _abstained("steps_satisfaction")],
        recently_exposed_hypothesis_keys=(),
    )
    assert result.outcome == InsightSelectionOutcome.INSUFFICIENT_DATA


def test_no_signal_when_tested_but_none_passed():
    result = select_insight_candidates(
        [
            _abstained("sleep_satisfaction"),
            _finding(
                "steps_satisfaction",
                effect=0.1,
                q=0.6,
                gate_passed=False,
                failure_reasons=(
                    GateFailureReason.EFFECT_TOO_SMALL,
                    GateFailureReason.NOT_SIGNIFICANT,
                ),
            ),
        ],
        recently_exposed_hypothesis_keys=(),
    )
    assert result.outcome == InsightSelectionOutcome.NO_SIGNAL


def test_ordering_abs_effect_then_q_then_registry():
    stronger_negative = _finding("steps_satisfaction", effect=-0.5, q=0.03)
    weaker_positive = _finding("sleep_satisfaction", effect=0.4, q=0.01)
    result = select_insight_candidates(
        [weaker_positive, stronger_negative], recently_exposed_hypothesis_keys=()
    )
    # 음의 rho도 부호를 보존한 채 |effect| 우선으로 선정된다
    assert [f.hypothesis_key for f in result.selected] == [
        "steps_satisfaction",
        "sleep_satisfaction",
    ]
    assert result.selected[0].effect_size == -0.5


def test_registry_order_breaks_exact_ties_regardless_of_input_order():
    a = _finding("sleep_satisfaction", effect=0.4, q=0.01)
    b = _finding("steps_satisfaction", effect=0.4, q=0.01)
    forward = select_insight_candidates([a, b], ())
    reversed_input = select_insight_candidates([b, a], ())
    assert [f.hypothesis_key for f in forward.selected] == [
        "sleep_satisfaction",
        "steps_satisfaction",
    ]
    assert forward.selected == reversed_input.selected  # same input → same output


def test_limit_respected():
    result = select_insight_candidates(
        [_finding("sleep_satisfaction"), _finding("steps_satisfaction")],
        (),
        limit=1,
    )
    assert len(result.selected) == 1


# ── evidence dates ──────────────────────────────────────────────────────────

SLEEP_HYPOTHESIS = REGISTERED_HYPOTHESES[0]


def test_positive_rho_prefers_same_direction_days():
    facts = [
        _fact(START, sleep=520, satisfaction=90),  # 둘 다 높음 — 최상위 근거
        _fact(START + timedelta(days=1), sleep=300, satisfaction=20),  # 둘 다 낮음
        _fact(START + timedelta(days=2), sleep=510, satisfaction=25),  # 반대 방향
        _fact(START + timedelta(days=3), sleep=430, satisfaction=55),  # 중간
    ]
    dates = select_evidence_dates(SLEEP_HYPOTHESIS, facts, effect_sign=1.0)
    assert dates[0] in (START, START + timedelta(days=1))
    assert START + timedelta(days=2) not in dates[:2]


def test_negative_rho_prefers_opposite_direction_days():
    facts = [
        _fact(START, sleep=520, satisfaction=85),  # 같은 방향 — 음의 상관 근거 아님
        _fact(START + timedelta(days=1), sleep=520, satisfaction=15),  # 반대 방향
        _fact(START + timedelta(days=2), sleep=300, satisfaction=90),  # 반대 방향
    ]
    dates = select_evidence_dates(SLEEP_HYPOTHESIS, facts, effect_sign=-1.0)
    assert set(dates[:2]) == {START + timedelta(days=1), START + timedelta(days=2)}


def test_missing_days_excluded_and_limit_three():
    facts = [_fact(START + timedelta(days=i), sleep=None, satisfaction=50) for i in range(3)]
    facts += [
        _fact(START + timedelta(days=3 + i), sleep=400 + i * 30, satisfaction=40 + i * 15)
        for i in range(5)
    ]
    dates = select_evidence_dates(SLEEP_HYPOTHESIS, facts, effect_sign=1.0)
    assert len(dates) == 3
    assert all(day >= START + timedelta(days=3) for day in dates)


def test_tie_broken_by_earlier_date():
    facts = [
        _fact(START + timedelta(days=1), sleep=500, satisfaction=80),
        _fact(START, sleep=500, satisfaction=80),
        _fact(START + timedelta(days=2), sleep=300, satisfaction=30),
    ]
    dates = select_evidence_dates(SLEEP_HYPOTHESIS, facts, effect_sign=1.0, limit=3)
    same_score_pair = [d for d in dates if d in (START, START + timedelta(days=1))]
    assert same_score_pair == sorted(same_score_pair)


# ── 리포트 모델 불변식 ──────────────────────────────────────────────────────


def _card(key: str = "sleep_satisfaction") -> InsightCard:
    return InsightCard(
        hypothesis_key=key,
        title="잠과 만족도의 패턴",
        message="함께 나타나는 경향이 있었어요.",
        evidence_dates=(START,),
    )


def test_generated_report_requires_cards():
    import pytest

    with pytest.raises(ValueError):
        InsightReport(
            device_id="dev-1",
            period_type="weekly",
            period_key="2026-W31",
            status=InsightReportStatus.GENERATED,
            cards=(),
            selected_hypothesis_keys=("sleep_satisfaction",),
            payload={},
            model_meta={},
        )


def test_non_generated_report_rejects_cards():
    import pytest

    with pytest.raises(ValueError):
        InsightReport(
            device_id="dev-1",
            period_type="weekly",
            period_key="2026-W31",
            status=InsightReportStatus.COOLDOWN,
            cards=(_card(),),
            selected_hypothesis_keys=(),
            payload={},
            model_meta={},
        )


def test_card_rejects_blank_and_duplicate_dates():
    import pytest

    with pytest.raises(ValueError):
        InsightCard(
            hypothesis_key="sleep_satisfaction",
            title=" ",
            message="m",
            evidence_dates=(),
        )
    with pytest.raises(ValueError):
        InsightCard(
            hypothesis_key="sleep_satisfaction",
            title="t",
            message="m",
            evidence_dates=(START, START),
        )
