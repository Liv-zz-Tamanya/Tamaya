from dataclasses import dataclass
from datetime import date
from uuid import UUID

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field, field_validator, model_validator

from app.application.service.agent_execution_observability import (
    get_active_agent_execution_trace,
)
from app.application.service.diary_memory_query_service import DiaryMemoryQueryService
from app.application.service.health_record_query_service import HealthRecordQueryService
from app.domain.model.event_chunk import EventChunk
from app.domain.model.health_chunk import HealthChunk

MAX_TOOL_QUERY_LENGTH = 500
MAX_TOOL_SEARCH_LIMIT = 10


@dataclass(frozen=True)
class AgentToolExecutionContext:
    device_id: str
    session_id: UUID | None = None


_DATE_ARG_DESCRIPTION = (
    "Optional ISO date (YYYY-MM-DD). If the user explicitly mentioned a date, preserve it "
    "here as a structured argument — never drop it, never widen it, and never guess a date "
    "the user did not state. Use start_date == end_date for a single exact date."
)


class _DateRangeSearchInput(BaseModel):
    """query + 선택적 날짜 범위 — 날짜는 임베딩이 아니라 SQL 필터로 처리된다."""

    start_date: date | None = Field(default=None, description=_DATE_ARG_DESCRIPTION)
    end_date: date | None = Field(default=None, description=_DATE_ARG_DESCRIPTION)

    @field_validator("query", mode="before", check_fields=False)
    @classmethod
    def normalize_query(cls, value: str) -> str:
        if isinstance(value, str):
            value = value.strip()
        if value == "":
            raise ValueError("query must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_date_range(self) -> "_DateRangeSearchInput":
        if self.start_date is not None and self.end_date is not None:
            if self.start_date > self.end_date:
                raise ValueError("start_date must be on or before end_date")
        return self


class SearchDiaryMemoriesInput(_DateRangeSearchInput):
    query: str = Field(
        ...,
        min_length=1,
        max_length=MAX_TOOL_QUERY_LENGTH,
        description="Semantic search query for the user's past diary memories.",
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=MAX_TOOL_SEARCH_LIMIT,
        description="Maximum number of diary memories to return.",
    )


class SearchHealthRecordsInput(_DateRangeSearchInput):
    query: str = Field(
        ...,
        min_length=1,
        max_length=MAX_TOOL_QUERY_LENGTH,
        description="Semantic search query for the user's past health records.",
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=MAX_TOOL_SEARCH_LIMIT,
        description="Maximum number of health records to return.",
    )


class DiaryMemoryToolItem(BaseModel):
    id: str
    diary_date: date
    text: str
    event_type: str
    who: str | None
    where: str | None
    when: str | None
    tags: list[str]


class SearchDiaryMemoriesResult(BaseModel):
    count: int
    items: list[DiaryMemoryToolItem]


class HealthRecordToolItem(BaseModel):
    id: str
    record_date: date
    text: str
    data_types: list[str]


class SearchHealthRecordsResult(BaseModel):
    count: int
    items: list[HealthRecordToolItem]


SEARCH_DIARY_MEMORIES_DESCRIPTION = (
    "Purpose: search the user's saved diary memories for past events, emotions, people, or places "
    "that are not in the current conversation. Use when: an answer needs a prior diary event or "
    "pattern because the user explicitly asks to find, verify, recall, or compare saved past records. Do not use "
    "when: the user is discussing a current event or emotion; the current conversation can continue "
    "with reflection or a follow-up question; past or repetition is only implied; the information is "
    "already in the conversation; the request is about health records; or saved memories would only be "
    "helpful rather than required; never infer a saved-record lookup from uncertainty alone. Input: a semantic query, optional limit, "
    "and optional start_date/end_date (ISO). Date policy: if the user stated a date, pass it as "
    "start_date/end_date and keep it exactly — do not drop, widen, or guess dates; when unsure, "
    "leave dates empty. If no records exist for the given dates the result is empty — do not "
    "retry with different dates. Output: matching diary memories only."
)

SEARCH_HEALTH_RECORDS_DESCRIPTION = (
    "Purpose: search the user's saved health records for prior activity or health-state history "
    "that is not in the current conversation. Use when: an answer needs stored sleep, symptom, "
    "medication, or other health history as evidence. Do not use when: general health support or "
    "empathy is enough; the information is already in the conversation; the request is about diary "
    "memories; or the same-quality answer does not require stored records. Input: a semantic query, "
    "optional limit, and optional start_date/end_date (ISO). Date policy: if the user stated a "
    "date, pass it as start_date/end_date and keep it exactly — do not drop, widen, or guess "
    "dates; when unsure, leave dates empty. If no records exist for the given dates the result is "
    "empty — do not retry with different dates. Output: matching health records only; never "
    "diagnose or prescribe."
)


def create_search_diary_memories_tool(
    query_service: DiaryMemoryQueryService,
    execution_context: AgentToolExecutionContext,
) -> BaseTool:
    async def search_diary_memories(
        query: str,
        limit: int = 5,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict:
        chunks = await query_service.search_similar(
            device_id=execution_context.device_id,
            query=query,
            exclude_session_id=execution_context.session_id,
            limit=limit,
            start_date=start_date,
            end_date=end_date,
        )
        trace = get_active_agent_execution_trace()
        if trace is not None:
            trace.record_retrieval_result("search_diary_memories", len(chunks))
        return _diary_memories_result(chunks).model_dump(mode="json")

    return StructuredTool.from_function(
        coroutine=search_diary_memories,
        name="search_diary_memories",
        description=SEARCH_DIARY_MEMORIES_DESCRIPTION,
        args_schema=SearchDiaryMemoriesInput,
        return_direct=False,
    )


def create_search_health_records_tool(
    query_service: HealthRecordQueryService,
    execution_context: AgentToolExecutionContext,
) -> BaseTool:
    async def search_health_records(
        query: str,
        limit: int = 5,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict:
        chunks = await query_service.search_similar(
            device_id=execution_context.device_id,
            query=query,
            limit=limit,
            start_date=start_date,
            end_date=end_date,
        )
        trace = get_active_agent_execution_trace()
        if trace is not None:
            trace.record_retrieval_result("search_health_records", len(chunks))
        return _health_records_result(chunks).model_dump(mode="json")

    return StructuredTool.from_function(
        coroutine=search_health_records,
        name="search_health_records",
        description=SEARCH_HEALTH_RECORDS_DESCRIPTION,
        args_schema=SearchHealthRecordsInput,
        return_direct=False,
    )


def create_read_tools(
    diary_query_service: DiaryMemoryQueryService,
    health_query_service: HealthRecordQueryService,
    execution_context: AgentToolExecutionContext,
) -> list[BaseTool]:
    return [
        create_search_diary_memories_tool(diary_query_service, execution_context),
        create_search_health_records_tool(health_query_service, execution_context),
    ]


def _diary_memories_result(chunks: list[EventChunk]) -> SearchDiaryMemoriesResult:
    items = [
        DiaryMemoryToolItem(
            id=str(chunk.id),
            diary_date=chunk.diary_date,
            text=chunk.text,
            event_type=chunk.event_type,
            who=chunk.who,
            where=chunk.where,
            when=chunk.when,
            tags=chunk.tags,
        )
        for chunk in chunks
    ]
    return SearchDiaryMemoriesResult(count=len(items), items=items)


def _health_records_result(chunks: list[HealthChunk]) -> SearchHealthRecordsResult:
    items = [
        HealthRecordToolItem(
            id=str(chunk.id),
            record_date=chunk.record_date,
            text=chunk.text,
            data_types=chunk.data_types,
        )
        for chunk in chunks
    ]
    return SearchHealthRecordsResult(count=len(items), items=items)
