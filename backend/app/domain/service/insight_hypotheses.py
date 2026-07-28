"""인사이트 가설 사전 등록 레지스트리와 통계 결과 모델 — 순수 Python.

가설은 이 레지스트리에서만 평가한다. 런타임 데이터에서 가설을 만들거나
컬럼 조합을 자동 탐색하지 않는다 — 사후 가설 탐색(p-hacking)을 막는 정책이다.
통계 게이트를 통과하기 전에는 어떤 인사이트 카드도 사용자에게 노출하지 않는다.

검정 실행(scipy)은 application 계층(insight_statistics)에 있다 —
domain에는 정의·정책·결과 모델만 둔다.
"""

from dataclasses import dataclass
from enum import StrEnum

# 통계 정책 상수 — BASELINE_MIN_OBSERVED_DAYS(30)는 기준선 안정성용이라
# 목적이 다르므로 재사용하지 않는다.
MIN_PAIRED_OBSERVATIONS = 20
FDR_ALPHA = 0.05
MIN_ABS_SPEARMAN_RHO = 0.30


class InsightTestType(StrEnum):
    SPEARMAN = "spearman"


class HypothesisPairing(StrEnum):
    SAME_DATE = "same_date"


@dataclass(frozen=True)
class HypothesisDefinition:
    key: str
    test_type: InsightTestType
    predictor: str  # DailyFact 필드명
    outcome: str  # DailyFact 필드명
    pairing: HypothesisPairing


REGISTERED_HYPOTHESES: tuple[HypothesisDefinition, ...] = (
    # record_date가 기상일이므로 same-date 페어링이
    # '지난밤 수면 → 오늘 만족도'를 의미한다.
    HypothesisDefinition(
        key="sleep_satisfaction",
        test_type=InsightTestType.SPEARMAN,
        predictor="sleep_minutes",
        outcome="satisfaction",
        pairing=HypothesisPairing.SAME_DATE,
    ),
    HypothesisDefinition(
        key="steps_satisfaction",
        test_type=InsightTestType.SPEARMAN,
        predictor="steps",
        outcome="satisfaction",
        pairing=HypothesisPairing.SAME_DATE,
    ),
)


class GateFailureReason(StrEnum):
    INSUFFICIENT_SAMPLE = "insufficient_sample"
    CONSTANT_INPUT = "constant_input"
    EFFECT_TOO_SMALL = "effect_too_small"
    NOT_SIGNIFICANT = "not_significant"


# 검정 전 abstention(통계값 없음) vs 검정 후 gate 탈락(통계값 존재) — 섞일 수 없다
PRE_TEST_FAILURE_REASONS = frozenset(
    {GateFailureReason.INSUFFICIENT_SAMPLE, GateFailureReason.CONSTANT_INPUT}
)
POST_TEST_FAILURE_REASONS = frozenset(
    {GateFailureReason.EFFECT_TOO_SMALL, GateFailureReason.NOT_SIGNIFICANT}
)


@dataclass(frozen=True)
class FindingCoverage:
    eligible_days: int  # 입력 facts 전체 일수
    paired_days: int  # predictor·outcome 모두 존재해 검정에 쓴 일수
    predictor_observed_days: int
    outcome_observed_days: int


@dataclass(frozen=True)
class StatisticalFinding:
    """가설 1개의 검정 결과. PR-C가 Agent 입력으로 그대로 주입할 구조다.

    effect_size는 부호 있는 Spearman rho — 음의 상관도 유효 후보다.
    표본 부족·상수 입력이면 검정을 수행하지 않아 통계값이 None이다.
    """

    hypothesis_key: str
    test_type: InsightTestType
    n: int
    effect_size: float | None
    p_value: float | None
    q_value: float | None
    gate_passed: bool
    coverage: FindingCoverage
    failure_reasons: tuple[GateFailureReason, ...]

    def __post_init__(self) -> None:
        if self.n != self.coverage.paired_days:
            raise ValueError("n은 coverage.paired_days와 같아야 합니다.")
        if self.gate_passed != (not self.failure_reasons):
            raise ValueError("gate_passed는 failure_reasons가 비어 있을 때만 True여야 합니다.")
        if self.gate_passed and None in (self.effect_size, self.p_value, self.q_value):
            raise ValueError("gate 통과 결과는 effect_size·p_value·q_value가 모두 있어야 합니다.")
        reasons = set(self.failure_reasons)
        statistics_values = (self.effect_size, self.p_value, self.q_value)
        if reasons & PRE_TEST_FAILURE_REASONS and reasons & POST_TEST_FAILURE_REASONS:
            raise ValueError("검정 전 사유와 검정 후 사유는 한 finding에 섞일 수 없습니다.")
        if reasons & PRE_TEST_FAILURE_REASONS and any(v is not None for v in statistics_values):
            raise ValueError("검정 전 abstention은 effect_size·p_value·q_value가 모두 None이어야 합니다.")
        if reasons & POST_TEST_FAILURE_REASONS and any(v is None for v in statistics_values):
            raise ValueError("검정 후 gate 탈락은 effect_size·p_value·q_value가 모두 있어야 합니다.")
        for name in ("p_value", "q_value"):
            value = getattr(self, name)
            if value is not None and not 0.0 <= value <= 1.0:
                raise ValueError(f"{name}은 0~1 범위여야 합니다: {value}")
        if self.effect_size is not None and not -1.0 <= self.effect_size <= 1.0:
            raise ValueError(f"effect_size는 -1~1 범위여야 합니다: {self.effect_size}")
