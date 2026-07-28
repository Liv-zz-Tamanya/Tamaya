"""인사이트 후보 선정·쿨다운·근거 날짜 — 순수 결정론 함수.

어떤 발견을 사용자에게 보여줄지는 LLM이 아니라 이 계층이 결정한다.
입력(findings + 최근 노출 key)만으로 출력이 정해지며 DB를 알지 못한다.
"""

from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from app.domain.service.insight_hypotheses import (
    PRE_TEST_FAILURE_REASONS,
    REGISTERED_HYPOTHESES,
    HypothesisDefinition,
    StatisticalFinding,
)
from app.domain.service.insight_models import DailyFact

# 주간 리포트 기준 최근 4주 동안 같은 hypothesis를 반복 노출하지 않는 초기 정책
INSIGHT_HYPOTHESIS_COOLDOWN_DAYS = 28
MAX_INSIGHT_CARDS = 2
MAX_EVIDENCE_DATES = 3

_REGISTRY_ORDER = {h.key: i for i, h in enumerate(REGISTERED_HYPOTHESES)}


class InsightSelectionOutcome(StrEnum):
    SELECTED = "selected"
    INSUFFICIENT_DATA = "insufficient_data"  # 검정 가능한 통계값이 하나도 없음
    NO_SIGNAL = "no_signal"  # 검정은 가능했으나 게이트 통과 후보 없음
    COOLDOWN = "cooldown"  # 통과 후보 전부가 최근 노출 제외


@dataclass(frozen=True)
class InsightSelectionResult:
    outcome: InsightSelectionOutcome
    selected: tuple[StatisticalFinding, ...]


def select_insight_candidates(
    findings: Sequence[StatisticalFinding],
    recently_exposed_hypothesis_keys: Collection[str],
    limit: int = MAX_INSIGHT_CARDS,
) -> InsightSelectionResult:
    """게이트 통과 후보를 쿨다운 제외 후 결정론 순서로 최대 limit개 선정한다.

    정렬: |effect| 내림차순 → q 오름차순 → 레지스트리 등록 순서.
    음의 상관도 부호를 보존한 채 후보가 될 수 있다.
    """
    testable = [
        f for f in findings if not (set(f.failure_reasons) & PRE_TEST_FAILURE_REASONS)
    ]
    if not testable:
        return InsightSelectionResult(InsightSelectionOutcome.INSUFFICIENT_DATA, ())

    passed = [f for f in testable if f.gate_passed]
    if not passed:
        return InsightSelectionResult(InsightSelectionOutcome.NO_SIGNAL, ())

    exposed = set(recently_exposed_hypothesis_keys)
    available = [f for f in passed if f.hypothesis_key not in exposed]
    if not available:
        return InsightSelectionResult(InsightSelectionOutcome.COOLDOWN, ())

    ordered = sorted(
        available,
        key=lambda f: (
            -abs(f.effect_size),
            f.q_value,
            _REGISTRY_ORDER.get(f.hypothesis_key, len(_REGISTRY_ORDER)),
        ),
    )
    return InsightSelectionResult(InsightSelectionOutcome.SELECTED, tuple(ordered[:limit]))


def select_evidence_dates(
    hypothesis: HypothesisDefinition,
    facts: Sequence[DailyFact],
    effect_sign: float,
    limit: int = MAX_EVIDENCE_DATES,
) -> tuple[date, ...]:
    """rho 방향과 정합하는 근거 탐색 날짜를 최대 limit개 고른다(결정론).

    통계 가설이나 게이트가 아니다 — Agent가 get_day_facts로 조회할 후보를
    LLM 대신 코드가 고르는 것뿐이다. paired 날짜만 쓰고 결측은 채우지 않는다.
    양의 rho는 predictor·satisfaction이 같은 방향으로, 음의 rho는 반대
    방향으로 함께 움직인 날짜가 우선한다(중심화 순위 곱 점수).
    """
    paired = [
        f
        for f in facts
        if getattr(f, hypothesis.predictor) is not None
        and getattr(f, hypothesis.outcome) is not None
    ]
    if not paired or effect_sign == 0:
        return ()

    predictor_ranks = _ranks([float(getattr(f, hypothesis.predictor)) for f in paired])
    outcome_ranks = _ranks([float(getattr(f, hypothesis.outcome)) for f in paired])
    center = (len(paired) - 1) / 2

    scored = []
    for fact, rank_x, rank_y in zip(paired, predictor_ranks, outcome_ranks, strict=True):
        alignment = (rank_x - center) * (rank_y - center)
        if effect_sign < 0:
            alignment = -alignment
        scored.append((fact.date, alignment))

    scored.sort(key=lambda item: (-item[1], item[0]))  # score 내림차순, 날짜 오름차순
    return tuple(day for day, _ in scored[:limit])


def _ranks(values: list[float]) -> list[float]:
    """0부터 시작하는 순위(동점은 입력 순서로 안정 결정 — 통계가 아니라 선택용)."""
    order = sorted(range(len(values)), key=lambda i: (values[i], i))
    ranks = [0.0] * len(values)
    for rank, index in enumerate(order):
        ranks[index] = float(rank)
    return ranks
