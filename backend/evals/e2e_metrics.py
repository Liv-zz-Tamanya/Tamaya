"""E2E 평가 — 실패 단계 분류와 집계.

분류는 파이프라인 순서(실행 → tool 선택 → 검색 → 답변)를 따르고,
한 실행은 처음 실패한 단계 하나로만 분류된다.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from evals.e2e_results import (
    E2ECaseResult,
    E2ECaseStability,
    E2EFailureStage,
    E2ESummary,
)
from evals.e2e_schemas import E2EEvalCase
from evals.generation_judge import JudgeVerdict
from evals.schemas import ExpectedDecision

GUARDRAIL_TERMINATIONS = frozenset({"input_guardrail_blocked", "output_guardrail_blocked"})


def classify_stage(
    case: E2EEvalCase,
    actual_tools: Sequence[str],
    retrieved_labels: Sequence[str],
    leaked_labels: Sequence[str],
    execution_error: str | None,
    termination_reason: str | None,
    completeness: float | None,
    verdict: JudgeVerdict | None,
) -> E2EFailureStage:
    if execution_error is not None:
        return E2EFailureStage.EXECUTION_ERROR
    if termination_reason in GUARDRAIL_TERMINATIONS:
        return E2EFailureStage.GUARDRAIL_BLOCKED
    called = set(actual_tools)
    if case.expected_decision == ExpectedDecision.NO_TOOL:
        return E2EFailureStage.TOOL_OVER_CALL if called else E2EFailureStage.PASS
    if not called:
        return E2EFailureStage.TOOL_UNDER_CALL
    if called & set(case.forbidden_tools):
        return E2EFailureStage.WRONG_TOOL
    if set(case.expected_tools) - called:
        return E2EFailureStage.WRONG_TOOL
    if leaked_labels:
        return E2EFailureStage.CROSS_USER_LEAK
    if not case.relevant_chunk_ids:
        # 기록이 없어야 하는 케이스: 지어내지 않고 abstain해야 통과
        if verdict is not None and (not verdict.abstained or verdict.unsupported_claims):
            return E2EFailureStage.ABSTENTION_FAIL
        return E2EFailureStage.PASS
    retrieved = set(retrieved_labels)
    missing = [chunk_id for chunk_id in case.relevant_chunk_ids if chunk_id not in retrieved]
    if missing:
        if len(missing) == len(case.relevant_chunk_ids):
            return E2EFailureStage.RETRIEVAL_MISS
        return E2EFailureStage.RETRIEVAL_PARTIAL
    if verdict is not None and verdict.unsupported_claims:
        return E2EFailureStage.UNSUPPORTED_CLAIM
    if completeness is not None and completeness < 1.0:
        return E2EFailureStage.INCOMPLETE_ANSWER
    return E2EFailureStage.PASS


def summarize_e2e(results: Sequence[E2ECaseResult]) -> E2ESummary:
    durations = [r.execution_duration_ms for r in results if r.execution_duration_ms is not None]
    tokens = [r.total_tokens for r in results if r.total_tokens is not None]
    stage_counts: dict[str, int] = {}
    for result in results:
        stage_counts[result.stage.value] = stage_counts.get(result.stage.value, 0) + 1
    passed = sum(result.passed for result in results)
    return E2ESummary(
        case_runs=len(results),
        passed_runs=passed,
        pass_rate=round(passed / len(results) * 100, 1) if results else 0.0,
        stage_counts=dict(sorted(stage_counts.items())),
        mean_execution_duration_ms=round(sum(durations) / len(durations), 1) if durations else None,
        p50_execution_duration_ms=_percentile(durations, 0.5),
        p95_execution_duration_ms=_percentile(durations, 0.95),
        mean_total_tokens=round(sum(tokens) / len(tokens), 1) if tokens else None,
        total_tokens_sum=sum(tokens),
        judge_error_runs=sum(result.judge_error is not None for result in results),
    )


def e2e_case_stability(results: Sequence[E2ECaseResult]) -> list[E2ECaseStability]:
    grouped: dict[str, list[E2ECaseResult]] = {}
    for result in results:
        grouped.setdefault(result.case_id, []).append(result)
    stability: list[E2ECaseStability] = []
    for case_id, runs in grouped.items():
        passed = sum(run.passed for run in runs)
        status = "stable_pass" if passed == len(runs) else "stable_fail" if passed == 0 else "flaky"
        frequency: dict[str, int] = {}
        for run in runs:
            frequency[run.stage.value] = frequency.get(run.stage.value, 0) + 1
        stability.append(
            E2ECaseStability(
                case_id=case_id,
                total_runs=len(runs),
                passed_runs=passed,
                status=status,
                stage_frequency=dict(sorted(frequency.items())),
            )
        )
    return stability


def _percentile(values: Sequence[int], quantile: float) -> int | None:
    """Nearest-rank percentile (기존 러너의 p95 계산과 동일한 방식)."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(math.ceil(quantile * len(ordered)) - 1, 0)]
