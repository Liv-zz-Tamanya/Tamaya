"""E2E Agent RAG 평가 결과·리포트의 Pydantic 모델."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.application.usecase.personal_assistant_agent import PersonalAssistantMode
from evals.generation_judge import JudgeVerdict
from evals.schemas import ExpectedDecision


class E2EFailureStage(StrEnum):
    """첫 번째로 실패한 파이프라인 단계 — 하나의 실행은 정확히 한 단계로 분류된다."""

    EXECUTION_ERROR = "EXECUTION_ERROR"
    GUARDRAIL_BLOCKED = "GUARDRAIL_BLOCKED"
    TOOL_OVER_CALL = "TOOL_OVER_CALL"
    TOOL_UNDER_CALL = "TOOL_UNDER_CALL"
    WRONG_TOOL = "WRONG_TOOL"
    CROSS_USER_LEAK = "CROSS_USER_LEAK"
    RETRIEVAL_MISS = "RETRIEVAL_MISS"
    RETRIEVAL_PARTIAL = "RETRIEVAL_PARTIAL"
    ABSTENTION_FAIL = "ABSTENTION_FAIL"
    UNSUPPORTED_CLAIM = "UNSUPPORTED_CLAIM"
    INCOMPLETE_ANSWER = "INCOMPLETE_ANSWER"
    PASS = "PASS"


class ToolQueryTrace(BaseModel):
    tool: str
    query: str
    result_count: int


class E2ECaseResult(BaseModel):
    case_id: str
    mode: PersonalAssistantMode
    category: str
    device_id: str
    input: str
    run_number: int = Field(default=1, ge=1)
    expected_decision: ExpectedDecision
    actual_tools: list[str] = Field(default_factory=list)
    tool_queries: list[ToolQueryTrace] = Field(default_factory=list)
    retrieved_labels: list[str] = Field(default_factory=list)
    missing_relevant: list[str] = Field(default_factory=list)
    leaked_labels: list[str] = Field(default_factory=list)
    unknown_ids: list[str] = Field(default_factory=list)
    answer: str | None = None
    completeness: float | None = None
    matched_fact_groups: list[str] = Field(default_factory=list)
    missing_fact_groups: list[str] = Field(default_factory=list)
    judge: JudgeVerdict | None = None
    judge_error: str | None = None
    stage: E2EFailureStage
    passed: bool
    termination_reason: str | None = None
    llm_calls: int | None = None
    tool_rounds: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    model_duration_ms: int | None = None
    tool_duration_ms: int | None = None
    execution_duration_ms: int | None = None
    execution_error: str | None = None


class E2ECaseStability(BaseModel):
    case_id: str
    total_runs: int
    passed_runs: int
    status: str  # stable_pass | flaky | stable_fail
    stage_frequency: dict[str, int]


class E2ESummary(BaseModel):
    case_runs: int
    passed_runs: int
    pass_rate: float
    stage_counts: dict[str, int]
    mean_execution_duration_ms: float | None
    p50_execution_duration_ms: int | None
    p95_execution_duration_ms: int | None
    mean_total_tokens: float | None
    total_tokens_sum: int
    judge_error_runs: int


class E2ERunReport(BaseModel):
    run_id: str
    started_at: datetime
    completed_at: datetime
    model: str
    judge_model: str
    prompt_hash: str
    repeat: int
    top_k: int
    git_commit: str | None = None
    git_dirty: bool | None = None
    summary: E2ESummary
    by_mode: dict[str, E2ESummary]
    by_category: dict[str, E2ESummary]
    case_stability: list[E2ECaseStability]
    cases: list[E2ECaseResult]
