"""PersonalAssistantAgent의 도구 선택 및 가드레일 오프라인 평가 실행기."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import subprocess
import sys
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from app.application.service.agent_execution_observability import (
    AgentExecutionRecord,
    AgentTerminationReason,
    AgentTraceDetail,
)
from app.application.service.coaching_prompt import build_coaching_system_prompt
from app.application.service.diary_chat_prompt import (
    DiaryConversationContext,
    build_diary_chat_system_prompt,
)
from app.application.service.health_chat_prompt import build_health_chat_system_prompt
from app.application.tool.read_tools import (
    AgentToolExecutionContext,
    create_read_tools,
    create_search_health_records_tool,
)
from app.application.usecase.personal_assistant_agent import PersonalAssistantMode
from app.application.usecase.personal_assistant_agent_factory import PersonalAssistantAgentFactory
from app.infrastructure.config.dependencies import (
    get_model_retry_policy,
    get_tool_calling_chat_model,
)
from app.infrastructure.config.settings import settings
from evals.schemas import ExpectedDecision, ExpectedGuardrail, PersonalAssistantEvalCase
from evals.validate_dataset import DATASET_FILENAMES

EVAL_DEVICE_ID = "personal-assistant-eval-device"
EVAL_SESSION_NAMESPACE = UUID("72a8b1ba-9f7b-4a13-9d32-c6d7ee1080fd")
EXECUTION_ERROR_REASONS = frozenset(
    {
        AgentTerminationReason.TIMEOUT,
        AgentTerminationReason.PROVIDER_ERROR,
        AgentTerminationReason.TOOL_ERROR,
        AgentTerminationReason.CANCELLED,
        AgentTerminationReason.UNEXPECTED_ERROR,
    }
)


class EvaluationCaseResult(BaseModel):
    run_number: int = Field(default=1, ge=1)
    case_id: str
    dataset_name: str
    mode: PersonalAssistantMode
    category: str
    input: str
    expected_tools: list[str]
    forbidden_tools: list[str]
    expected_decision: ExpectedDecision | None = None
    actual_decision: ExpectedDecision | None = None
    decision_check_passed: bool | None = None
    decision_evaluable: bool = False
    decision_skip_reason: str | None = None
    actual_tools: list[str] = Field(default_factory=list)
    missing_expected_tools: list[str] = Field(default_factory=list)
    called_forbidden_tools: list[str] = Field(default_factory=list)
    expected_guardrail: ExpectedGuardrail
    actual_guardrail: str | None = None
    guardrail_verdict: str | None = None
    termination_reason: str | None = None
    tool_check_passed: bool = False
    guardrail_check_passed: bool = False
    combined_passed: bool = False
    execution_error: str | None = None
    trace_id: str | None = None
    llm_calls: int | None = None
    tool_rounds: int | None = None
    execution_duration_ms: int | None = None
    model_duration_ms: int | None = None
    tool_duration_ms: int | None = None
    retry_attempts: int | None = None
    provider_error_category: str | None = None
    timeout_stage: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    tool_calls: list[ToolCallTrace] = Field(default_factory=list)
    llm_call_traces: list[LlmCallTrace] = Field(default_factory=list)
    first_finish_reason: str | None = None
    first_response_content: str | None = None
    final_response_content: str | None = None
    expected_document_ids: list[str]
    document_evaluation_status: str = "not_evaluated"


class ToolCallTrace(BaseModel):
    round: int
    call_id: str | None = None
    name: str
    arguments: dict[str, Any] | None = None
    arguments_parse_error: str | None = None


class LlmCallTrace(BaseModel):
    call_number: int
    finish_reason: str | None = None
    response_content: str | None = None
    tool_calls: list[ToolCallTrace] = Field(default_factory=list)
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    duration_ms: int | None = None


class EvaluationSummary(BaseModel):
    total_cases: int
    completed_cases: int
    execution_error_cases: int
    tool_check_passed_cases: int
    tool_check_rate: float
    guardrail_check_passed_cases: int
    guardrail_check_rate: float
    combined_passed_cases: int
    combined_rate: float
    forbidden_tool_violation_cases: int
    decision_check_cases: int
    decision_check_passed_cases: int
    decision_check_rate: float | None
    no_tool_cases: int
    no_tool_accuracy: float | None
    tool_call_cases: int
    tool_call_accuracy: float | None
    unnecessary_tool_call_cases: int
    decision_skipped_cases: int
    decision_skipped_input_guardrail_blocked_cases: int
    decision_skipped_execution_error_cases: int
    decision_skipped_agent_not_invoked_cases: int


class CaseStabilityResult(BaseModel):
    case_id: str
    dataset_name: str
    mode: PersonalAssistantMode
    category: str
    total_runs: int
    completed_runs: int
    passed_runs: int
    failed_runs: int
    case_pass_rate: float
    tool_check_pass_rate: float
    guardrail_check_pass_rate: float
    forbidden_tool_violation_runs: int
    forbidden_tool_violation_rate: float
    execution_error_runs: int
    execution_error_rate: float
    status: str
    actual_tool_selected_runs: dict[str, int]
    actual_tool_selection_rates: dict[str, float]
    termination_reason_frequency: dict[str, int]
    provider_error_category_frequency: dict[str, int]
    average_execution_duration_ms: float | None
    p95_execution_duration_ms: int | None
    average_total_tokens: float | None


class StabilitySummary(BaseModel):
    selected_case_count: int
    repeat_count: int
    total_executions: int
    stable_passed_cases: int
    flaky_cases: int
    stable_failed_cases: int
    average_case_pass_rate: float
    execution_error_runs: int
    execution_error_rate: float
    forbidden_tool_violation_runs: int
    forbidden_tool_violation_rate: float


class ToolConfusionMatrix(BaseModel):
    true_positive: int = 0
    false_positive: int = 0
    false_negative: int = 0
    true_negative: int = 0
    unlabeled: int = 0
    precision: float | None = None
    recall: float | None = None


class BaselineComparison(BaseModel):
    matched_cases: list[str]
    added_cases: list[str]
    removed_cases: list[str]
    improved_cases: list[str]
    regressed_cases: list[str]
    unchanged_cases: list[str]
    average_case_pass_rate_delta: float | None
    forbidden_tool_violation_rate_delta: float | None
    execution_error_rate_delta: float | None


class EvaluationModelConfig(BaseModel):
    provider: str
    model: str | None
    temperature: float | None
    top_p: float | None = None
    seed: int | None = None
    parallel_tool_calls: bool | None = None
    max_tokens: int | None = None
    timeout_seconds: float | None = None


class PromptMetadata(BaseModel):
    prompt_hash: str
    tool_schema_hash: str
    git_commit: str | None = None
    git_dirty: bool | None = None


class EvaluationRunReport(BaseModel):
    run_id: str
    started_at: datetime
    completed_at: datetime
    selected_datasets: list[str]
    summary: EvaluationSummary
    by_mode: dict[str, EvaluationSummary]
    by_category: dict[str, EvaluationSummary]
    cases: list[EvaluationCaseResult]
    model_settings: EvaluationModelConfig
    prompt_metadata: PromptMetadata
    stability_summary: StabilitySummary
    case_stability: list[CaseStabilityResult]
    tool_confusion_matrix: dict[str, ToolConfusionMatrix]
    baseline_comparison: BaselineComparison | None = None


class EvaluationRecorder:
    """한 Agent 실행의 terminal record를 명시적으로 분리해 보관한다."""

    def __init__(self) -> None:
        self._records: list[AgentExecutionRecord] = []

    def record(self, record: AgentExecutionRecord) -> None:
        self._records.append(record)

    def reset(self) -> None:
        self._records.clear()

    def only_record(self) -> AgentExecutionRecord:
        if len(self._records) != 1:
            raise RuntimeError(f"evaluation recorder expected exactly one record, got {len(self._records)}")
        return self._records[0]


class _EmptyDiaryQuery:
    async def search_similar(
        self, device_id: str, query: str, exclude_session_id: UUID | None = None, limit: int = 5
    ) -> list[object]:
        return []


class _EmptyHealthQuery:
    async def search_similar(self, device_id: str, query: str, limit: int = 5) -> list[object]:
        return []


def messages_for_case(case: PersonalAssistantEvalCase) -> list[BaseMessage]:
    messages: list[BaseMessage] = []
    for item in case.history:
        if item.role == "user":
            messages.append(HumanMessage(content=item.content))
        elif item.role == "assistant":
            messages.append(AIMessage(content=item.content))
        else:
            raise ValueError(f"case {case.id}: unsupported history role: {item.role}")
    messages.append(HumanMessage(content=case.input))
    return messages


def load_cases(dataset_dir: Path, datasets: Sequence[str] | None = None) -> list[tuple[str, PersonalAssistantEvalCase]]:
    selected = set(datasets or dataset_names())
    loaded: list[tuple[str, PersonalAssistantEvalCase]] = []
    for filename in DATASET_FILENAMES:
        name = filename.removesuffix("_cases.jsonl")
        if name not in selected:
            continue
        path = dataset_dir / filename
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                raise ValueError(f"{path}:{line_number}: empty JSONL row")
            loaded.append((name, PersonalAssistantEvalCase.model_validate_json(line)))
    return loaded


def dataset_names() -> list[str]:
    return [filename.removesuffix("_cases.jsonl") for filename in DATASET_FILENAMES]


def select_cases(
    cases: Iterable[tuple[str, PersonalAssistantEvalCase]], case_id: str | None, limit: int | None
) -> list[tuple[str, PersonalAssistantEvalCase]]:
    selected = [(dataset, case) for dataset, case in cases if case_id is None or case.id == case_id]
    if case_id is not None and not selected:
        raise ValueError(f"case not found: {case_id}")
    return selected[:limit] if limit is not None else selected


def evaluate_record(
    case: PersonalAssistantEvalCase, dataset_name: str, record: AgentExecutionRecord | None, error: Exception | None,
    run_number: int = 1,
) -> EvaluationCaseResult:
    tool_calls = _tool_call_traces_from_record(record)
    llm_call_traces = _llm_call_traces_from_record(record)
    actual_tools = [call.name for call in tool_calls] if tool_calls else list(record.tool_names) if record else []
    actual_set = set(actual_tools)
    missing = sorted(set(case.expected_tools) - actual_set)
    forbidden = sorted(set(case.forbidden_tools) & actual_set)
    reason = record.termination_reason if record else None
    execution_error = str(error) if error else None
    if reason in EXECUTION_ERROR_REASONS:
        execution_error = execution_error or f"agent terminated: {reason.value}"
    actual_guardrail = (
        "BLOCK" if reason in {AgentTerminationReason.INPUT_GUARDRAIL_BLOCKED, AgentTerminationReason.OUTPUT_GUARDRAIL_BLOCKED}
        else "PASS" if record and execution_error is None else None
    )
    guardrail_passed = actual_guardrail == case.expected_guardrail.value and execution_error is None
    expected_decision = _expected_decision(case)
    decision_evaluable, decision_skip_reason = _decision_evaluation_state(
        expected_decision,
        record,
        execution_error,
    )
    actual_decision = (
        ExpectedDecision.TOOL_CALL if actual_tools else ExpectedDecision.NO_TOOL
    ) if decision_evaluable else None
    decision_check = actual_decision == expected_decision if decision_evaluable else None
    return EvaluationCaseResult(
        run_number=run_number, case_id=case.id, dataset_name=dataset_name, mode=case.mode, category=case.category, input=case.input,
        expected_tools=case.expected_tools, forbidden_tools=case.forbidden_tools, expected_decision=expected_decision,
        actual_decision=actual_decision, decision_check_passed=decision_check, decision_evaluable=decision_evaluable,
        decision_skip_reason=decision_skip_reason, actual_tools=actual_tools,
        missing_expected_tools=missing, called_forbidden_tools=forbidden, expected_guardrail=case.expected_guardrail,
        actual_guardrail=actual_guardrail, guardrail_verdict=record.guardrail_verdict if record else None,
        termination_reason=reason.value if reason else None, tool_check_passed=not missing and not forbidden,
        guardrail_check_passed=guardrail_passed, combined_passed=not missing and not forbidden and guardrail_passed,
        execution_error=execution_error, trace_id=record.trace_id if record else None, llm_calls=record.llm_calls if record else None,
        tool_rounds=record.tool_rounds if record else None, execution_duration_ms=record.execution_duration_ms if record else None,
        model_duration_ms=record.model_duration_ms if record else None, tool_duration_ms=record.tool_duration_ms if record else None,
        retry_attempts=record.retry_attempts if record else None, provider_error_category=record.provider_error_category if record else None,
        timeout_stage=record.timeout_stage if record else None, input_tokens=record.input_tokens if record else None,
        output_tokens=record.output_tokens if record else None, total_tokens=record.total_tokens if record else None,
        tool_calls=tool_calls, llm_call_traces=llm_call_traces,
        first_finish_reason=record.first_finish_reason if record else None,
        first_response_content=record.first_response_content if record else None,
        final_response_content=record.final_response_content if record else None,
        expected_document_ids=case.expected_document_ids,
    )


def _tool_call_traces_from_record(record: AgentExecutionRecord | None) -> list[ToolCallTrace]:
    if record is None:
        return []
    return [ToolCallTrace.model_validate(asdict(tool_call)) for tool_call in record.tool_calls]


def _llm_call_traces_from_record(record: AgentExecutionRecord | None) -> list[LlmCallTrace]:
    if record is None:
        return []
    return [
        LlmCallTrace.model_validate({
            **asdict(trace),
            "tool_calls": [asdict(tool_call) for tool_call in trace.tool_calls],
        })
        for trace in record.llm_call_traces
    ]


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


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator * 100, 1) if denominator else 0.0


def _nullable_rate(numerator: int, denominator: int) -> float | None:
    return _rate(numerator, denominator) if denominator else None


def _expected_decision(case: PersonalAssistantEvalCase) -> ExpectedDecision | None:
    if case.expected_decision is not None:
        return case.expected_decision
    if case.expected_tools:
        return ExpectedDecision.TOOL_CALL
    if case.forbidden_tools:
        return ExpectedDecision.NO_TOOL
    return None


def _decision_evaluation_state(
    expected_decision: ExpectedDecision | None,
    record: AgentExecutionRecord | None,
    execution_error: str | None,
) -> tuple[bool, str | None]:
    if expected_decision is None:
        return False, "expected_decision_missing"
    if execution_error is not None:
        return False, "execution_error"
    if record is None or record.llm_calls == 0:
        if record and record.termination_reason == AgentTerminationReason.INPUT_GUARDRAIL_BLOCKED:
            return False, "input_guardrail_blocked"
        return False, "agent_not_invoked"
    return True, None


async def run_cases(cases: Sequence[tuple[str, PersonalAssistantEvalCase]], model=None, fail_fast: bool = False) -> list[EvaluationCaseResult]:
    return await run_repeated_cases(cases, model=model, fail_fast=fail_fast)


async def run_repeated_cases(
    cases: Sequence[tuple[str, PersonalAssistantEvalCase]],
    model=None,
    fail_fast: bool = False,
    repeat: int = 1,
) -> list[EvaluationCaseResult]:
    model = model or _real_evaluation_model()
    recorder = EvaluationRecorder()
    factory = PersonalAssistantAgentFactory(
        model,
        _EmptyDiaryQuery(),
        _EmptyHealthQuery(),
        execution_recorder=recorder,
        trace_detail=AgentTraceDetail.FULL,
    )
    results: list[EvaluationCaseResult] = []
    for dataset_name, case in cases:
        for run_number in range(1, repeat + 1):
            recorder.reset()
            error: Exception | None = None
            try:
                agent = factory.create(device_id=EVAL_DEVICE_ID, session_id=uuid5(EVAL_SESSION_NAMESPACE, f"{case.id}:{run_number}"), mode=case.mode)
                await agent.run(messages=messages_for_case(case), mode=case.mode,
                    diary_context=DiaryConversationContext(max_turns=5, current_user_turn=1, suggest_finalize=False) if case.mode == PersonalAssistantMode.DIARY else None,
                    coaching_context={"persona": None} if case.mode == PersonalAssistantMode.COACHING else None)
            except Exception as exc:
                error = exc
            try:
                record = recorder.only_record()
            except RuntimeError as recorder_error:
                record = None
                error = error or recorder_error
            results.append(evaluate_record(case, dataset_name, record, error, run_number))
            if error and fail_fast:
                return results
    return results


def _real_evaluation_model():
    if settings.clova_mock_mode or not settings.clova_api_key.strip():
        raise RuntimeError("Real CLOVA credentials are required. Set CLOVA_MOCK_MODE=false and CLOVA_API_KEY before running evaluation.")
    return get_tool_calling_chat_model(
        x_clova_api_key=None,
        retry_policy=get_model_retry_policy(),
    )


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


def _average(values: Sequence[int | float]) -> float | None:
    return round(sum(values) / len(values), 1) if values else None


def _p95(values: Sequence[int]) -> int | None:
    """Nearest-rank p95: sort ascending and choose ceil(0.95 * n)-th value."""
    return sorted(values)[math.ceil(0.95 * len(values)) - 1] if values else None


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


def _delta(current: float | None, baseline: float | None) -> float | None:
    return round(current - baseline, 1) if current is not None and baseline is not None else None


def _model_config_metadata(model: object | None) -> EvaluationModelConfig:
    delegate = _unwrap_model(model)
    model_name = getattr(delegate, "_model", None)
    temperature = getattr(delegate, "_temperature", None)
    max_tokens = getattr(delegate, "_max_tokens", None)
    timeout = getattr(delegate, "_timeout", None)
    provider = "mock" if delegate.__class__.__name__ == "MockToolCallingChatModel" else "clova"
    return EvaluationModelConfig(
        provider=provider,
        model=model_name if isinstance(model_name, str) else settings.clova_model,
        temperature=temperature if isinstance(temperature, int | float) else settings.clova_agent_temperature,
        top_p=None,
        seed=None,
        parallel_tool_calls=None,
        max_tokens=max_tokens if isinstance(max_tokens, int) else settings.clova_agent_max_tokens,
        timeout_seconds=timeout if isinstance(timeout, int | float) else settings.clova_agent_timeout_seconds,
    )


def _unwrap_model(model: object | None) -> object:
    current = model
    seen: set[int] = set()
    while current is not None and id(current) not in seen and hasattr(current, "_delegate"):
        seen.add(id(current))
        current = current._delegate
    return current if current is not None else object()


def _prompt_metadata(modes: Sequence[PersonalAssistantMode]) -> PromptMetadata:
    return PromptMetadata(
        prompt_hash=_hash_json(_prompt_payload(modes)),
        tool_schema_hash=_hash_json(_tool_schema_payload(modes)),
        **_git_metadata(),
    )


def _modes_for_datasets(datasets: Sequence[str]) -> list[PersonalAssistantMode]:
    modes: list[PersonalAssistantMode] = []
    for dataset in datasets:
        try:
            mode = PersonalAssistantMode(dataset)
        except ValueError:
            continue
        if mode not in modes:
            modes.append(mode)
    return modes


def _prompt_payload(modes: Sequence[PersonalAssistantMode]) -> dict[str, Any]:
    prompts: dict[str, str] = {}
    for mode in modes:
        if mode == PersonalAssistantMode.DIARY:
            prompts[mode.value] = build_diary_chat_system_prompt(
                max_turns=5,
                current_user_turn=1,
                suggest_finalize=False,
                tool_calling_enabled=True,
            )
        elif mode == PersonalAssistantMode.HEALTH:
            prompts[mode.value] = build_health_chat_system_prompt(tool_calling_enabled=True)
        elif mode == PersonalAssistantMode.COACHING:
            prompts[mode.value] = build_coaching_system_prompt(persona=None)
    return {
        "system_prompts": prompts,
        "tool_schemas": _tool_schema_payload(modes),
    }


def _tool_schema_payload(modes: Sequence[PersonalAssistantMode]) -> list[dict[str, Any]]:
    context = AgentToolExecutionContext(
        device_id=EVAL_DEVICE_ID,
        session_id=uuid5(EVAL_SESSION_NAMESPACE, "prompt-metadata"),
    )
    tools: list[BaseTool] = []
    for mode in modes:
        if mode == PersonalAssistantMode.DIARY:
            tools.extend(create_read_tools(_EmptyDiaryQuery(), _EmptyHealthQuery(), context))
        elif mode == PersonalAssistantMode.HEALTH:
            tools.append(create_search_health_records_tool(_EmptyHealthQuery(), context))
    return [_tool_schema(tool) for tool in sorted(tools, key=lambda item: item.name)]


def _tool_schema(tool: BaseTool) -> dict[str, Any]:
    args_schema = tool.args_schema.model_json_schema() if tool.args_schema is not None else {}
    return {
        "name": tool.name,
        "description": tool.description,
        "parameters": args_schema,
    }


def _hash_json(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _git_metadata() -> dict[str, str | bool | None]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "diff", "--quiet"],
            check=False,
            capture_output=True,
            text=True,
        ).returncode != 0
    except (OSError, subprocess.SubprocessError):
        return {"git_commit": None, "git_dirty": None}
    return {"git_commit": commit or None, "git_dirty": dirty}


def load_baseline(path: Path) -> list[CaseStabilityResult]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return [CaseStabilityResult.model_validate(item) for item in raw["case_stability"]]
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"incompatible baseline report {path}: expected case_stability: {exc}") from exc


def build_report(
    results: list[EvaluationCaseResult],
    datasets: list[str],
    started_at: datetime,
    repeat: int = 1,
    baseline: Sequence[CaseStabilityResult] | None = None,
    model: object | None = None,
) -> EvaluationRunReport:
    stability = case_stability(results)
    return EvaluationRunReport(run_id=started_at.strftime("%Y%m%dT%H%M%SZ"), started_at=started_at,
        completed_at=datetime.now(UTC), selected_datasets=datasets, summary=summarize(results),
        by_mode={key: summarize([r for r in results if r.mode.value == key]) for key in sorted({r.mode.value for r in results})},
        by_category={key: summarize([r for r in results if r.category == key]) for key in sorted({r.category for r in results})}, cases=results,
        model_settings=_model_config_metadata(model),
        prompt_metadata=_prompt_metadata(_modes_for_datasets(datasets)),
        stability_summary=stability_summary(stability, repeat), case_stability=stability,
        tool_confusion_matrix=tool_confusion_matrix(results), baseline_comparison=compare_baseline(stability, baseline) if baseline is not None else None)


def write_report(report: EvaluationRunReport, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = report.model_dump(mode="json")
    payload["model_config"] = payload.pop("model_settings")
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def print_summary(report: EvaluationRunReport) -> None:
    summary = report.summary
    stability = report.stability_summary
    print("\nPersonal Assistant Evaluation\n")
    print(f"Selected cases: {stability.selected_case_count}\nRepeat: {stability.repeat_count}\nTotal executions: {summary.total_cases}")
    print(f"Completed: {summary.completed_cases}\nExecution errors: {summary.execution_error_cases}\n")
    print(f"Tool checks: {summary.tool_check_passed_cases}/{summary.completed_cases} ({summary.tool_check_rate}%)")
    print(f"Guardrail checks: {summary.guardrail_check_passed_cases}/{summary.completed_cases} ({summary.guardrail_check_rate}%)")
    print(f"Combined: {summary.combined_passed_cases}/{summary.completed_cases} ({summary.combined_rate}%)")
    print(f"Forbidden tool violations: {summary.forbidden_tool_violation_cases}")
    if summary.decision_check_cases:
        print(f"Decision checks: {summary.decision_check_passed_cases}/{summary.decision_check_cases} ({summary.decision_check_rate}%)")
        print(f"NO_TOOL accuracy: {summary.no_tool_accuracy}% ({summary.no_tool_cases} cases)")
        print(f"TOOL_CALL accuracy: {summary.tool_call_accuracy}% ({summary.tool_call_cases} cases)")
        print(f"Unnecessary tool calls: {summary.unnecessary_tool_call_cases}")
    if summary.decision_skipped_cases:
        print(f"Decision skipped: {summary.decision_skipped_cases}")
        print(f"- input guardrail blocked: {summary.decision_skipped_input_guardrail_blocked_cases}")
        print(f"- execution error: {summary.decision_skipped_execution_error_cases}")
        print(f"- agent not invoked: {summary.decision_skipped_agent_not_invoked_cases}")
    print(f"Stable pass cases: {stability.stable_passed_cases}\nFlaky cases: {stability.flaky_cases}\nStable fail cases: {stability.stable_failed_cases}")
    if stability.flaky_cases:
        print("\nFlaky cases:")
        for item in report.case_stability:
            if item.status == "flaky":
                print(f"- {item.case_id}: {item.passed_runs}/{item.total_runs} passed, tools={item.actual_tool_selected_runs}")
    if report.baseline_comparison:
        comparison = report.baseline_comparison
        print(f"\nBaseline comparison:\nImproved: {len(comparison.improved_cases)}\nRegressed: {len(comparison.regressed_cases)}\nAdded: {len(comparison.added_cases)}\nRemoved: {len(comparison.removed_cases)}")
    failures = [r for r in report.cases if not r.combined_passed]
    if failures:
        print("\nFailed cases:")
        for result in failures:
            detail = result.execution_error or (f"missing {', '.join(result.missing_expected_tools)}" if result.missing_expected_tools else f"forbidden {', '.join(result.called_forbidden_tools)}" if result.called_forbidden_tools else f"expected {result.expected_guardrail.value}, actual {result.actual_guardrail}")
            print(f"- {result.case_id}: {detail}{_failure_args_summary(result)}")


def _failure_args_summary(result: EvaluationCaseResult) -> str:
    calls = [call for call in result.tool_calls if call.arguments]
    if not calls:
        return ""
    payload = [
        {"name": call.name, "arguments": call.arguments}
        for call in calls
    ]
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if len(text) > 240:
        text = text[:237] + "..."
    return f"\n  args={text}"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run PersonalAssistantAgent evaluation")
    parser.add_argument("--dataset", choices=[*dataset_names(), "all"], default="all")
    parser.add_argument("--case-id")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--fail-on-mismatch", action="store_true")
    parser.add_argument("--fail-on-regression", action="store_true")
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    if args.repeat < 1:
        parser.error("--repeat must be at least 1")
    if args.fail_on_regression and args.baseline is None:
        parser.error("--fail-on-regression requires --baseline")
    datasets = dataset_names() if args.dataset == "all" else [args.dataset]
    try:
        cases = select_cases(load_cases(Path(__file__).parent / "datasets", datasets), args.case_id, args.limit)
        baseline = load_baseline(args.baseline) if args.baseline else None
        print("This run calls the real LLM API and may incur cost. Production DB and user data are not used.")
        started_at = datetime.now(UTC)
        model = _real_evaluation_model()
        report = build_report(
            asyncio.run(run_repeated_cases(cases, model=model, fail_fast=args.fail_fast, repeat=args.repeat)),
            datasets,
            started_at,
            args.repeat,
            baseline,
            model,
        )
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Evaluation could not start: {exc}", file=sys.stderr)
        return 2
    output = args.output or Path(__file__).parent / "reports" / f"{report.run_id}-personal-assistant-eval.json"
    write_report(report, output)
    print_summary(report)
    print(f"\nReport: {output}")
    mismatch = args.fail_on_mismatch and any(not r.combined_passed for r in report.cases)
    regression = args.fail_on_regression and report.baseline_comparison and report.baseline_comparison.regressed_cases
    return 1 if mismatch or regression else 0


if __name__ == "__main__":
    raise SystemExit(main())
