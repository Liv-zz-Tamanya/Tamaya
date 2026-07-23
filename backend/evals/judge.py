"""한 Agent 실행 record를 케이스 기대값과 대조해 판정한다."""

from __future__ import annotations

from dataclasses import asdict

from app.application.service.agent_execution_observability import (
    AgentExecutionRecord,
    AgentTerminationReason,
)
from evals.results import EvaluationCaseResult, LlmCallTrace, ToolCallTrace
from evals.schemas import ExpectedDecision, PersonalAssistantEvalCase

EXECUTION_ERROR_REASONS = frozenset(
    {
        AgentTerminationReason.TIMEOUT,
        AgentTerminationReason.PROVIDER_ERROR,
        AgentTerminationReason.TOOL_ERROR,
        AgentTerminationReason.CANCELLED,
        AgentTerminationReason.UNEXPECTED_ERROR,
    }
)


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
