"""평가 전용 DB에 시드할 가상 사용자·Diary·Health fixture의 Pydantic 스키마.

실제 사용자 데이터가 아니라 전부 합성 데이터다. device_id는 반드시
``eval-`` 접두사를 가져야 하며, seed/reset은 이 접두사 스코프 안에서만 동작한다.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EVAL_DEVICE_PREFIX = "eval-"

# clova_client.CHUNK_EXTRACT_USER_REQUEST가 규정하는 event_type 어휘와 동일해야 한다.
EventType = Literal["work", "social", "emotion", "personal", "achievement"]

# scripts/ingest_health_data.HealthChunkBuilder._get_data_types와 동일한 어휘.
HealthDataType = Literal["steps", "exercise", "heart_rate", "floors"]


class VirtualUser(BaseModel):
    """평가 전용 가상 사용자. persona는 fixture 작성 시 일관성 유지용 메모다."""

    model_config = ConfigDict(extra="forbid")

    device_id: str = Field(min_length=len(EVAL_DEVICE_PREFIX) + 1, max_length=64)
    name: str = Field(min_length=1)
    persona: str = Field(min_length=1)


class FixtureMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class GoldChunk(BaseModel):
    """이 대화에서 추출되어야 할 정답 Event Chunk.

    seed 시 event_chunks 행이 되고, 이후 retrieval 평가(expected_document_ids)와
    chunk 생성 평가(PR3)의 정답 레이블로 재사용된다.
    """

    model_config = ConfigDict(extra="forbid")

    chunk_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    tags: list[str] = Field(min_length=1)
    event_type: EventType
    who: str | None = None
    where: str | None = None
    when: str | None = None


class DiaryDayFixture(BaseModel):
    """가상 사용자의 하루치 일기 대화 + 정답 chunk 묶음."""

    model_config = ConfigDict(extra="forbid")

    fixture_id: str = Field(min_length=1)
    device_id: str = Field(min_length=1)
    session_date: date
    messages: list[FixtureMessage] = Field(min_length=1)
    gold_chunks: list[GoldChunk] = Field(default_factory=list)


class HealthDayFixture(BaseModel):
    """가상 사용자의 하루치 건강 기록 chunk.

    text는 HealthChunkBuilder가 생성하는 한국어 자연어 형식을 따른다.
    """

    model_config = ConfigDict(extra="forbid")

    fixture_id: str = Field(min_length=1)
    device_id: str = Field(min_length=1)
    record_date: date
    text: str = Field(min_length=1)
    data_types: list[HealthDataType] = Field(min_length=1)
