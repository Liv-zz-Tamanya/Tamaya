"""Retrieval 평가 결과·리포트의 Pydantic 모델."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from evals.retrieval_schemas import RetrievalKind


class RetrievedDoc(BaseModel):
    rank: int
    label: str
    relevant: bool = False
    leaked_from: str | None = None  # 다른 사용자 소유 chunk가 나온 경우 그 device_id


class RetrievalCaseResult(BaseModel):
    case_id: str
    kind: RetrievalKind
    device_id: str
    category: str
    query: str
    relevant_chunk_ids: list[str]
    retrieved: list[RetrievedDoc] = Field(default_factory=list)
    # 빈 정답(empty_expected) 케이스는 순위 지표를 계산하지 않는다
    rank_metrics_evaluable: bool = True
    hit_at_1: bool | None = None
    hit_at_3: bool | None = None
    hit_at_5: bool | None = None
    precision_at_k: float | None = None
    recall_at_k: float | None = None
    reciprocal_rank: float | None = None
    first_relevant_rank: int | None = None
    empty_expected: bool = False
    empty_check_passed: bool | None = None
    leaked_labels: list[str] = Field(default_factory=list)
    unknown_ids: list[str] = Field(default_factory=list)


class RetrievalSummary(BaseModel):
    case_count: int
    evaluable_cases: int
    hit_rate_at_1: float | None
    hit_rate_at_3: float | None
    hit_rate_at_5: float | None
    mean_precision_at_k: float | None
    mean_recall_at_k: float | None
    mrr: float | None
    empty_expected_cases: int
    empty_check_passed_cases: int
    leak_violation_cases: int
    unknown_result_cases: int


class RetrievalBaselineComparison(BaseModel):
    matched_cases: list[str]
    added_cases: list[str]
    removed_cases: list[str]
    improved_cases: list[str]
    regressed_cases: list[str]
    unchanged_cases: list[str]
    hit_rate_at_1_delta: float | None
    hit_rate_at_5_delta: float | None
    mean_recall_at_k_delta: float | None
    mrr_delta: float | None


class RetrievalRunReport(BaseModel):
    run_id: str
    started_at: datetime
    completed_at: datetime
    top_k: int
    embedding_model: str
    git_commit: str | None = None
    git_dirty: bool | None = None
    summary: RetrievalSummary
    by_kind: dict[str, RetrievalSummary]
    by_category: dict[str, RetrievalSummary]
    cases: list[RetrievalCaseResult]
    baseline_comparison: RetrievalBaselineComparison | None = None
