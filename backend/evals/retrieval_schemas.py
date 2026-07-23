"""Retrieval 검색 평가 데이터셋의 Pydantic 스키마.

Agent를 제외하고 검색 service를 직접 호출하는 평가다. 정답 문서는
fixture의 chunk_id(diary) 또는 fixture_id(health)로 참조한다.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


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
