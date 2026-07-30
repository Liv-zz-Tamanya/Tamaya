"""Retrieval 검색 평가 데이터셋의 Pydantic 스키마.

Agent를 제외하고 검색 service를 직접 호출하는 평가다. 정답 문서는
fixture의 chunk_id(diary) 또는 fixture_id(health)로 참조한다.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RetrievalKind(StrEnum):
    DIARY = "diary"
    HEALTH = "health"


class RetrievalEvalCase(BaseModel):
    """검색 질의 1건과 그 정답 문서 집합.

    relevant_chunk_ids가 비어 있으면 "관련 기록이 없어야 하는" 케이스로,
    검색 결과가 0건이어야 통과한다(예: 건강 데이터가 없는 사용자).
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    kind: RetrievalKind
    device_id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    relevant_chunk_ids: list[str] = Field(default_factory=list)
    category: str = Field(min_length=1)
    note: str | None = None
    # 구조화 날짜 조건(선택) — filter 모드 평가에서 search_similar에 그대로 전달된다.
    # LLM이 tool argument로 넘겼을 날짜를 dataset에 명시적으로 저장하는 자리다.
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def _validate_date_range(self) -> RetrievalEvalCase:
        if self.start_date is not None and self.end_date is not None:
            if self.start_date > self.end_date:
                raise ValueError("start_date must be <= end_date")
        return self
