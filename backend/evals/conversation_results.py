"""대화 품질·Output Safety 평가 결과·리포트의 Pydantic 모델."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.application.usecase.personal_assistant_agent import PersonalAssistantMode
from evals.conversation_judge import ConversationVerdict
from evals.conversation_schemas import ConversationCategory


class ConversationCaseResult(BaseModel):
    case_id: str
    mode: PersonalAssistantMode
    category: ConversationCategory
    input: str
    run_number: int = Field(default=1, ge=1)
    answer: str | None = None
    blocked: bool = False  # input/output guardrail 차단
    termination_reason: str | None = None
    actual_tools: list[str] = Field(default_factory=list)
    prescriptive_content: bool = False
    judge: ConversationVerdict | None = None
    judge_error: str | None = None
    passed: bool | None = None
    fail_reasons: list[str] = Field(default_factory=list)
    total_tokens: int | None = None
    execution_duration_ms: int | None = None
    execution_error: str | None = None


class ConversationCategorySummary(BaseModel):
    case_runs: int
    passed_runs: int
    pass_rate: float | None
    blocked_runs: int
    judge_error_runs: int


class ConversationSummary(BaseModel):
    case_runs: int
    completed_runs: int
    execution_error_runs: int
    judge_error_runs: int
    blocked_runs: int
    passed_runs: int
    pass_rate: float | None
    by_category: dict[str, ConversationCategorySummary]


class ConversationRunReport(BaseModel):
    run_id: str
    started_at: datetime
    completed_at: datetime
    model: str
    judge_model: str
    prompt_hash: str
    judge_prompt_hash: str
    repeat: int
    git_commit: str | None = None
    git_dirty: bool | None = None
    summary: ConversationSummary
    cases: list[ConversationCaseResult]
