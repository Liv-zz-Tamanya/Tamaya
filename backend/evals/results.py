"""평가 실행 결과·리포트의 Pydantic 모델."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.application.usecase.personal_assistant_agent import PersonalAssistantMode
from evals.schemas import ExpectedDecision, ExpectedGuardrail


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
