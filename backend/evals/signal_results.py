"""정성신호 추출 평가 결과·리포트의 Pydantic 모델."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class BehaviorMatch(BaseModel):
    behavior_id: str
    extracted_behavior: str
    gold_polarity: int
    extracted_polarity: int
    polarity_match: bool


class SignalCaseResult(BaseModel):
    fixture_id: str
    device_id: str
    run_number: int = Field(default=1, ge=1)
    extracted_emotion: str | None = None
    emotion_plausible: bool | None = None
    matches: list[BehaviorMatch] = Field(default_factory=list)
    missed_behavior_ids: list[str] = Field(default_factory=list)
    hallucinated_behaviors: list[str] = Field(default_factory=list)
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    extraction_none: bool = False  # 클라이언트가 None 반환(파싱 실패 흡수)
    execution_error: str | None = None


class SignalSummary(BaseModel):
    case_runs: int
    completed_runs: int
    execution_error_runs: int
    extraction_none_runs: int
    behavior_precision: float | None
    behavior_recall: float | None
    behavior_f1: float | None
    true_positives: int
    false_positives: int
    false_negatives: int
    polarity_accuracy: float | None
    emotion_plausible_rate: float | None
    hallucination_runs: int
    empty_contract_cases: int
    empty_contract_passed: int


class SignalRunReport(BaseModel):
    run_id: str
    started_at: datetime
    completed_at: datetime
    model: str
    prompt_hash: str
    repeat: int
    git_commit: str | None = None
    git_dirty: bool | None = None
    summary: SignalSummary
    by_device: dict[str, SignalSummary]
    cases: list[SignalCaseResult]
