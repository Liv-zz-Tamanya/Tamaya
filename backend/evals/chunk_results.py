"""Event Chunk 생성 평가 결과·리포트의 Pydantic 모델."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ExtractedChunk(BaseModel):
    """LLM이 추출한 chunk 1건 — 프로덕션 파서(extract_event_chunks)의 dict를 정규화."""

    text: str
    tags: list[str] = Field(default_factory=list)
    event_type: str | None = None
    who: str | None = None
    where: str | None = None
    when: str | None = None

    @classmethod
    def from_raw(cls, raw: Any) -> ExtractedChunk | None:
        """계약을 어긴 행(text 없음 등)은 None — 호출부가 invalid_rows로 집계한다."""
        if not isinstance(raw, dict):
            return None
        text = raw.get("text")
        if not isinstance(text, str) or not text.strip():
            return None
        tags = raw.get("tags")
        return cls(
            text=text.strip(),
            tags=[tag for tag in tags if isinstance(tag, str)] if isinstance(tags, list) else [],
            event_type=raw.get("event_type") if isinstance(raw.get("event_type"), str) else None,
            who=raw.get("who") if isinstance(raw.get("who"), str) else None,
            where=raw.get("where") if isinstance(raw.get("where"), str) else None,
            when=raw.get("when") if isinstance(raw.get("when"), str) else None,
        )


class ChunkMatch(BaseModel):
    gold_chunk_id: str
    extracted_index: int
    extracted_text: str
    similarity: float
    event_type_match: bool
    who_match: bool
    where_match: bool
    when_match: bool


class MissedGold(BaseModel):
    """추출되지 않은 정답 사건(누락). merged=True면 다른 추출문에 흡수된 병합 의심."""

    chunk_id: str
    text: str
    best_similarity: float | None = None
    merged: bool = False


class UnmatchedExtracted(BaseModel):
    """정답과 매칭되지 않은 추출문. over_split=True면 이미 매칭된 정답의 중복 추출,
    False면 대화에 근거가 없는 환각 의심."""

    index: int
    text: str
    best_gold_id: str | None = None
    best_similarity: float | None = None
    over_split: bool = False


class ChunkCaseResult(BaseModel):
    fixture_id: str
    device_id: str
    run_number: int = Field(default=1, ge=1)
    gold_count: int = 0
    extracted_count: int = 0
    invalid_rows: int = 0
    matches: list[ChunkMatch] = Field(default_factory=list)
    missed: list[MissedGold] = Field(default_factory=list)
    unmatched: list[UnmatchedExtracted] = Field(default_factory=list)
    recall: float | None = None
    precision: float | None = None
    execution_error: str | None = None


class ChunkSummary(BaseModel):
    case_runs: int
    completed_runs: int
    execution_error_runs: int
    gold_total: int
    extracted_total: int
    matched_total: int
    mean_recall: float | None
    mean_precision: float | None
    missed_total: int
    merged_total: int
    over_split_total: int
    hallucinated_total: int
    invalid_row_total: int
    mean_similarity: float | None
    event_type_accuracy: float | None
    who_accuracy: float | None
    where_accuracy: float | None
    when_accuracy: float | None


class ChunkRunReport(BaseModel):
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
    summary: ChunkSummary
    by_device: dict[str, ChunkSummary]
    cases: list[ChunkCaseResult]
