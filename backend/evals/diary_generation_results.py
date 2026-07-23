"""일기 생성 품질 평가 결과·리포트의 Pydantic 모델."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class EventCoverage(BaseModel):
    """gold chunk(핵심 사건) 1건이 일기 본문에 반영됐는지."""

    chunk_id: str
    best_similarity: float | None = None
    covered: bool = False


class SentenceGrounding(BaseModel):
    """일기 문장 1개의 근거 분류.

    - grounded: gold chunk 또는 사용자 발화에 근거
    - assistant_only: assistant 발화에만 근거 — 발화 혼동 의심
    - ungrounded: 어디에도 근거 없음 — 원문에 없는 사건 의심
    """

    sentence: str
    status: str
    best_source: str | None = None
    best_similarity: float | None = None


class DiaryCaseResult(BaseModel):
    fixture_id: str
    device_id: str
    run_number: int = Field(default=1, ge=1)
    title: str | None = None
    content: str | None = None
    emotion: str | None = None
    satisfaction: int | None = None
    keywords: list[str] = Field(default_factory=list)
    invalid_json: bool = False
    schema_errors: list[str] = Field(default_factory=list)
    sentence_count: int | None = None
    sentence_count_ok: bool | None = None
    event_coverage: list[EventCoverage] = Field(default_factory=list)
    event_recall: float | None = None
    sentences: list[SentenceGrounding] = Field(default_factory=list)
    ungrounded_sentences: int = 0
    assistant_confusion_sentences: int = 0
    generic_keywords: list[str] = Field(default_factory=list)
    ungrounded_keywords: list[str] = Field(default_factory=list)
    emotion_plausible: bool | None = None
    execution_error: str | None = None


class DiarySummary(BaseModel):
    case_runs: int
    completed_runs: int
    execution_error_runs: int
    invalid_json_runs: int
    schema_violation_runs: int
    mean_event_recall: float | None
    missed_event_total: int
    ungrounded_sentence_runs: int
    ungrounded_sentence_total: int
    assistant_confusion_runs: int
    assistant_confusion_total: int
    sentence_count_ok_rate: float | None
    emotion_plausible_rate: float | None
    generic_keyword_runs: int
    ungrounded_keyword_runs: int


class DiaryRunReport(BaseModel):
    run_id: str
    started_at: datetime
    completed_at: datetime
    model: str
    prompt_hash: str
    embedding_model: str
    similarity_threshold: float
    repeat: int
    git_commit: str | None = None
    git_dirty: bool | None = None
    summary: DiarySummary
    by_device: dict[str, DiarySummary]
    cases: list[DiaryCaseResult]
