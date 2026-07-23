"""케이스 결과 집계 지표 — summary, 반복 안정성, confusion matrix, baseline 비교."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence

from evals.results import (
    BaselineComparison,
    CaseStabilityResult,
    EvaluationCaseResult,
    EvaluationSummary,
    StabilitySummary,
    ToolConfusionMatrix,
)
from evals.schemas import ExpectedDecision


def summarize(results: Sequence[EvaluationCaseResult]) -> EvaluationSummary:
    total = len(results)
    errors = sum(result.execution_error is not None for result in results)
    completed = total - errors
    tool = sum(result.tool_check_passed for result in results if result.execution_error is None)
    guardrail = sum(result.guardrail_check_passed for result in results if result.execution_error is None)
    combined = sum(result.combined_passed for result in results)
    decision_results = [result for result in results if result.decision_check_passed is not None]
    no_tool = [result for result in decision_results if result.expected_decision == ExpectedDecision.NO_TOOL]
    tool_call = [result for result in decision_results if result.expected_decision == ExpectedDecision.TOOL_CALL]
    skipped = [result for result in results if result.expected_decision and not result.decision_evaluable]
    return EvaluationSummary(total_cases=total, completed_cases=completed, execution_error_cases=errors,
        tool_check_passed_cases=tool, tool_check_rate=_rate(tool, completed), guardrail_check_passed_cases=guardrail,
        guardrail_check_rate=_rate(guardrail, completed), combined_passed_cases=combined, combined_rate=_rate(combined, completed),
        forbidden_tool_violation_cases=sum(bool(result.called_forbidden_tools) for result in results),
        decision_check_cases=len(decision_results), decision_check_passed_cases=sum(result.decision_check_passed for result in decision_results),
        decision_check_rate=_nullable_rate(sum(result.decision_check_passed for result in decision_results), len(decision_results)),
        no_tool_cases=len(no_tool), no_tool_accuracy=_nullable_rate(sum(result.decision_check_passed for result in no_tool), len(no_tool)),
        tool_call_cases=len(tool_call), tool_call_accuracy=_nullable_rate(sum(result.decision_check_passed for result in tool_call), len(tool_call)),
        unnecessary_tool_call_cases=sum(result.expected_decision == ExpectedDecision.NO_TOOL and result.actual_decision == ExpectedDecision.TOOL_CALL for result in results),
        decision_skipped_cases=len(skipped),
        decision_skipped_input_guardrail_blocked_cases=sum(result.decision_skip_reason == "input_guardrail_blocked" for result in skipped),
        decision_skipped_execution_error_cases=sum(result.decision_skip_reason == "execution_error" for result in skipped),
        decision_skipped_agent_not_invoked_cases=sum(result.decision_skip_reason == "agent_not_invoked" for result in skipped))


def case_stability(results: Sequence[EvaluationCaseResult]) -> list[CaseStabilityResult]:
    grouped: dict[str, list[EvaluationCaseResult]] = {}
    for result in results:
        grouped.setdefault(result.case_id, []).append(result)
    summaries: list[CaseStabilityResult] = []
    for case_id, runs in grouped.items():
        first = runs[0]
        total = len(runs)
        passed = sum(run.combined_passed for run in runs)
        errors = sum(run.execution_error is not None for run in runs)
        forbidden = sum(bool(run.called_forbidden_tools) for run in runs)
        selected = Counter(tool for run in runs for tool in set(run.actual_tools))
        terminations = Counter(run.termination_reason for run in runs if run.termination_reason)
        provider_errors = Counter(run.provider_error_category for run in runs if run.provider_error_category)
        durations = [run.execution_duration_ms for run in runs if run.execution_duration_ms is not None]
        tokens = [run.total_tokens for run in runs if run.total_tokens is not None]
        status = "stable_pass" if passed == total else "stable_fail" if passed == 0 else "flaky"
        summaries.append(CaseStabilityResult(
            case_id=case_id, dataset_name=first.dataset_name, mode=first.mode, category=first.category,
            total_runs=total, completed_runs=total - errors, passed_runs=passed, failed_runs=total - passed,
            case_pass_rate=_rate(passed, total), tool_check_pass_rate=_rate(sum(run.tool_check_passed for run in runs), total),
            guardrail_check_pass_rate=_rate(sum(run.guardrail_check_passed for run in runs), total),
            forbidden_tool_violation_runs=forbidden, forbidden_tool_violation_rate=_rate(forbidden, total),
            execution_error_runs=errors, execution_error_rate=_rate(errors, total), status=status,
            actual_tool_selected_runs=dict(sorted(selected.items())),
            actual_tool_selection_rates={tool: _rate(count, total) for tool, count in sorted(selected.items())},
            termination_reason_frequency=dict(sorted(terminations.items())),
            provider_error_category_frequency=dict(sorted(provider_errors.items())),
            average_execution_duration_ms=_average(durations), p95_execution_duration_ms=_p95(durations),
            average_total_tokens=_average(tokens),
        ))
    return summaries


def stability_summary(summaries: Sequence[CaseStabilityResult], repeat: int) -> StabilitySummary:
    total = sum(item.total_runs for item in summaries)
    errors = sum(item.execution_error_runs for item in summaries)
    forbidden = sum(item.forbidden_tool_violation_runs for item in summaries)
    return StabilitySummary(selected_case_count=len(summaries), repeat_count=repeat, total_executions=total,
        stable_passed_cases=sum(item.status == "stable_pass" for item in summaries),
        flaky_cases=sum(item.status == "flaky" for item in summaries),
        stable_failed_cases=sum(item.status == "stable_fail" for item in summaries),
        average_case_pass_rate=_average([item.case_pass_rate for item in summaries]) or 0.0,
        execution_error_runs=errors, execution_error_rate=_rate(errors, total),
        forbidden_tool_violation_runs=forbidden, forbidden_tool_violation_rate=_rate(forbidden, total))


def tool_confusion_matrix(results: Sequence[EvaluationCaseResult]) -> dict[str, ToolConfusionMatrix]:
    tools = sorted({tool for result in results for tool in result.expected_tools + result.forbidden_tools})
    matrix: dict[str, ToolConfusionMatrix] = {}
    for tool in tools:
        counts = Counter()
        for result in results:
            if result.execution_error is not None:
                counts["unlabeled"] += 1
                continue
            actual = tool in set(result.actual_tools)
            if tool in result.expected_tools:
                counts["true_positive" if actual else "false_negative"] += 1
            elif tool in result.forbidden_tools:
                counts["false_positive" if actual else "true_negative"] += 1
            else:
                counts["unlabeled"] += 1
        precision_denominator = counts["true_positive"] + counts["false_positive"]
        recall_denominator = counts["true_positive"] + counts["false_negative"]
        matrix[tool] = ToolConfusionMatrix(**counts,
            precision=_rate(counts["true_positive"], precision_denominator) if precision_denominator else None,
            recall=_rate(counts["true_positive"], recall_denominator) if recall_denominator else None)
    return matrix


def compare_baseline(current: Sequence[CaseStabilityResult], baseline: Sequence[CaseStabilityResult]) -> BaselineComparison:
    now = {item.case_id: item for item in current}
    before = {item.case_id: item for item in baseline}
    matched = sorted(now.keys() & before.keys())
    improved: list[str] = []
    regressed: list[str] = []
    unchanged: list[str] = []
    for case_id in matched:
        current_case, baseline_case = now[case_id], before[case_id]
        regression = (current_case.case_pass_rate < baseline_case.case_pass_rate or
            current_case.forbidden_tool_violation_rate > baseline_case.forbidden_tool_violation_rate or
            current_case.execution_error_rate > baseline_case.execution_error_rate or
            (baseline_case.status == "stable_pass" and current_case.status != "stable_pass") or
            (baseline_case.status == "flaky" and current_case.status == "stable_fail"))
        if regression:
            regressed.append(case_id)
        elif current_case.case_pass_rate > baseline_case.case_pass_rate:
            improved.append(case_id)
        else:
            unchanged.append(case_id)
    return BaselineComparison(matched_cases=matched, added_cases=sorted(now.keys() - before.keys()),
        removed_cases=sorted(before.keys() - now.keys()), improved_cases=improved, regressed_cases=regressed,
        unchanged_cases=unchanged,
        average_case_pass_rate_delta=_delta(_average([item.case_pass_rate for item in current]), _average([item.case_pass_rate for item in baseline])),
        forbidden_tool_violation_rate_delta=_delta(_rate(sum(item.forbidden_tool_violation_runs for item in current), sum(item.total_runs for item in current)), _rate(sum(item.forbidden_tool_violation_runs for item in baseline), sum(item.total_runs for item in baseline))),
        execution_error_rate_delta=_delta(_rate(sum(item.execution_error_runs for item in current), sum(item.total_runs for item in current)), _rate(sum(item.execution_error_runs for item in baseline), sum(item.total_runs for item in baseline))))


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator * 100, 1) if denominator else 0.0


def _nullable_rate(numerator: int, denominator: int) -> float | None:
    return _rate(numerator, denominator) if denominator else None


def _average(values: Sequence[int | float]) -> float | None:
    return round(sum(values) / len(values), 1) if values else None


def _p95(values: Sequence[int]) -> int | None:
    """Nearest-rank p95: sort ascending and choose ceil(0.95 * n)-th value."""
    return sorted(values)[math.ceil(0.95 * len(values)) - 1] if values else None


def _delta(current: float | None, baseline: float | None) -> float | None:
    return round(current - baseline, 1) if current is not None and baseline is not None else None
