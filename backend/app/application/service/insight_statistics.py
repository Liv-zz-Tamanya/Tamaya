"""인사이트 통계 게이트 — 사전 등록 가설을 DailyFact에서 검정한다.

DailyFact[] → paired sample 추출(listwise deletion) → Spearman 양측 검정
→ BH FDR 보정 → 3중 게이트(n·|rho|·q) → StatisticalFinding[].

순수 함수: 같은 입력이면 항상 같은 결과. DB·LLM·네트워크 없음.
scipy는 이 계층에만 격리한다 — domain은 순수 Python을 유지한다.
BH 보정 family는 '한 사용자 × 한 기간 × 한 실행'의 사전 등록 가설 전체다.
"""

from scipy.stats import spearmanr

from app.domain.service.insight_hypotheses import (
    FDR_ALPHA,
    MIN_ABS_SPEARMAN_RHO,
    MIN_PAIRED_OBSERVATIONS,
    REGISTERED_HYPOTHESES,
    FindingCoverage,
    GateFailureReason,
    HypothesisDefinition,
    StatisticalFinding,
)
from app.domain.service.insight_models import DailyFact


def evaluate_hypotheses(facts: list[DailyFact]) -> list[StatisticalFinding]:
    """사전 등록 가설 전체를 검정한다. 결과 순서는 레지스트리 등록 순서."""
    tested = [_test_hypothesis(hypothesis, facts) for hypothesis in REGISTERED_HYPOTHESES]

    # 표본 부족·상수 입력은 p가 없으므로 BH family에서 제외한다
    valid_indices = [i for i, t in enumerate(tested) if t["p_value"] is not None]
    q_values = benjamini_hochberg([tested[i]["p_value"] for i in valid_indices])
    for index, q_value in zip(valid_indices, q_values, strict=True):
        tested[index]["q_value"] = q_value

    return [_apply_gate(t) for t in tested]


def _test_hypothesis(hypothesis: HypothesisDefinition, facts: list[DailyFact]) -> dict:
    predictor_values = [getattr(f, hypothesis.predictor) for f in facts]
    outcome_values = [getattr(f, hypothesis.outcome) for f in facts]

    # SAME_DATE 페어링: 같은 DailyFact 행에서 둘 다 관측된 날만 사용 (listwise deletion)
    pairs = [
        (float(x), float(y))
        for x, y in zip(predictor_values, outcome_values, strict=True)
        if x is not None and y is not None
    ]
    coverage = FindingCoverage(
        eligible_days=len(facts),
        paired_days=len(pairs),
        predictor_observed_days=sum(v is not None for v in predictor_values),
        outcome_observed_days=sum(v is not None for v in outcome_values),
    )

    result: dict = {
        "hypothesis": hypothesis,
        "coverage": coverage,
        "effect_size": None,
        "p_value": None,
        "q_value": None,
        "pre_failure": None,
    }
    if len(pairs) < MIN_PAIRED_OBSERVATIONS:
        result["pre_failure"] = GateFailureReason.INSUFFICIENT_SAMPLE
        return result

    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    # 상수 입력은 순위가 정의되지 않는다 — scipy warning에 기대지 않고 명시적으로 거른다
    if len(set(xs)) <= 1 or len(set(ys)) <= 1:
        result["pre_failure"] = GateFailureReason.CONSTANT_INPUT
        return result

    test = spearmanr(xs, ys)  # 양측 검정 — 음의 상관도 유효 후보
    result["effect_size"] = max(-1.0, min(1.0, float(test.statistic)))
    result["p_value"] = max(0.0, min(1.0, float(test.pvalue)))
    return result


def _apply_gate(tested: dict) -> StatisticalFinding:
    hypothesis: HypothesisDefinition = tested["hypothesis"]
    coverage: FindingCoverage = tested["coverage"]

    if tested["pre_failure"] is not None:
        failure_reasons: tuple[GateFailureReason, ...] = (tested["pre_failure"],)
    else:
        # 실패 사유 순서는 결정론적으로 고정: 효과크기 → 유의성
        reasons: list[GateFailureReason] = []
        if abs(tested["effect_size"]) < MIN_ABS_SPEARMAN_RHO:
            reasons.append(GateFailureReason.EFFECT_TOO_SMALL)
        if tested["q_value"] > FDR_ALPHA:
            reasons.append(GateFailureReason.NOT_SIGNIFICANT)
        failure_reasons = tuple(reasons)

    return StatisticalFinding(
        hypothesis_key=hypothesis.key,
        test_type=hypothesis.test_type,
        n=coverage.paired_days,
        effect_size=tested["effect_size"],
        p_value=tested["p_value"],
        q_value=tested["q_value"],
        gate_passed=not failure_reasons,
        coverage=coverage,
        failure_reasons=failure_reasons,
    )


def benjamini_hochberg(p_values: list[float]) -> list[float]:
    """BH FDR 보정 — 입력 순서대로 q-value를 반환한다(단조·1.0 clamp)."""
    m = len(p_values)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda i: p_values[i])
    q_values = [0.0] * m
    running_min = 1.0
    for rank_index in range(m - 1, -1, -1):
        original_index = order[rank_index]
        adjusted = p_values[original_index] * m / (rank_index + 1)
        running_min = min(running_min, adjusted)
        q_values[original_index] = min(running_min, 1.0)
    return q_values
