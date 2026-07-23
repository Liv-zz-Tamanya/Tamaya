"""RAG 답변 생성 평가 결과·리포트의 Pydantic 모델."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from evals.generation_judge import JudgeVerdict
from evals.generation_schemas import GenerationCategory, GenerationMode


class GenerationCaseResult(BaseModel):
    case_id: str
    mode: GenerationMode
    category: GenerationCategory
    device_id: str
    question: str
    context_labels: list[str] = Field(default_factory=list)
    run_number: int = Field(default=1, ge=1)
    answer: str | None = None
    answered: bool = False
    re_search: bool = False  # 문서를 주었는데도 또 tool을 호출하려 한 경우
    completeness: float | None = None
    matched_fact_groups: list[str] = Field(default_factory=list)
    missing_fact_groups: list[str] = Field(default_factory=list)
    judge: JudgeVerdict | None = None
    judge_error: str | None = None
    prescriptive_content: bool = False  # 결정론 검사(medical_guardrail)
    passed: bool | None = None  # abstention/boundary/bait만 이분 판정
    execution_error: str | None = None


class GenerationSummary(BaseModel):
    case_runs: int
    answered_runs: int
    re_search_runs: int
    execution_error_runs: int
    judge_error_runs: int
    mean_completeness: float | None
    faithful_rate: float | None
    unsupported_claim_runs: int
    abstention_cases: int
    abstention_passed: int
    boundary_cases: int
    boundary_passed: int
    bait_cases: int
    bait_passed: int
    prescriptive_content_runs: int


class GenerationRunReport(BaseModel):
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
    summary: GenerationSummary
    by_category: dict[str, GenerationSummary]
    cases: list[GenerationCaseResult]
