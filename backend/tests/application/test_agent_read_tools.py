from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.application.tool.read_tools import (
    AgentToolExecutionContext,
    SearchDiaryMemoriesInput,
    SearchHealthRecordsInput,
    create_read_tools,
    create_search_diary_memories_tool,
    create_search_health_records_tool,
)
from app.domain.model.event_chunk import EventChunk
from app.domain.model.health_chunk import HealthChunk


class _FakeDiaryMemoryQuery:
    def __init__(
        self,
        chunks: list[EventChunk] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.chunks = chunks or []
        self.error = error
        self.calls: list[dict] = []

    async def search_similar(
        self,
        device_id: str,
        query: str,
        exclude_session_id: UUID | None = None,
        limit: int = 5,
    ) -> list[EventChunk]:
        self.calls.append(
            {
                "device_id": device_id,
                "query": query,
                "exclude_session_id": exclude_session_id,
                "limit": limit,
            }
        )
        if self.error:
            raise self.error
        return self.chunks


class _FakeHealthRecordQuery:
    def __init__(
        self,
        chunks: list[HealthChunk] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.chunks = chunks or []
        self.error = error
        self.calls: list[dict] = []

    async def search_similar(
        self,
        device_id: str,
        query: str,
        limit: int = 5,
    ) -> list[HealthChunk]:
        self.calls.append({"device_id": device_id, "query": query, "limit": limit})
        if self.error:
            raise self.error
        return self.chunks


def _event_chunk(
    *,
    text: str,
    tags: list[str] | None = None,
    who: str | None = None,
    where: str | None = None,
    when: str | None = None,
) -> EventChunk:
    return EventChunk(
        id=uuid4(),
        chat_session_id=uuid4(),
        diary_date=date(2026, 7, 10),
        text=text,
        embedding=[0.1, 0.2],
        tags=tags or [],
        event_type="daily",
        who=who,
        where=where,
        when=when,
    )


def _health_chunk(*, text: str, data_types: list[str]) -> HealthChunk:
    return HealthChunk(
        id=uuid4(),
        device_id="dev-a",
        record_date=date(2026, 7, 11),
        text=text,
        embedding=[0.3, 0.4],
        data_types=data_types,
    )


def test_search_diary_memories_tool_contract_and_input_schema():
    tool = create_search_diary_memories_tool(
        _FakeDiaryMemoryQuery(),
        AgentToolExecutionContext(device_id="dev-a", session_id=uuid4()),
    )

    assert tool.name == "search_diary_memories"
    assert tool.description
    assert "Purpose:" in tool.description
    assert "Use when:" in tool.description
    assert "Do not use when:" in tool.description
    assert tool.return_direct is False
    assert set(tool.args_schema.model_json_schema()["properties"]) == {"query", "limit"}
    assert "device_id" not in tool.args_schema.model_json_schema()["properties"]
    assert "session_id" not in tool.args_schema.model_json_schema()["properties"]

    parsed = SearchDiaryMemoriesInput.model_validate({"query": "  발표 기억  "})
    assert parsed.query == "발표 기억"
    assert parsed.limit == 5

    for invalid_query in ("", "   "):
        with pytest.raises(ValidationError):
            SearchDiaryMemoriesInput.model_validate({"query": invalid_query})

    for invalid_limit in (0, 11):
        with pytest.raises(ValidationError):
            SearchDiaryMemoriesInput.model_validate({"query": "기억", "limit": invalid_limit})


async def test_search_diary_memories_tool_calls_query_service_and_returns_dto():
    session_id = uuid4()
    first = _event_chunk(
        text="민수와 회의실에서 발표 준비",
        tags=["발표", "회사"],
        who="민수",
        where="회의실",
        when="오전",
    )
    second = _event_chunk(text="혼자 산책하며 기분 전환", tags=[])
    query_service = _FakeDiaryMemoryQuery([first, second])
    tool = create_search_diary_memories_tool(
        query_service,
        AgentToolExecutionContext(device_id="dev-a", session_id=session_id),
    )

    result = await tool.ainvoke({"query": "  발표 기억  ", "limit": 2})

    assert query_service.calls == [
        {
            "device_id": "dev-a",
            "query": "발표 기억",
            "exclude_session_id": session_id,
            "limit": 2,
        }
    ]
    assert result == {
        "count": 2,
        "items": [
            {
                "id": str(first.id),
                "diary_date": "2026-07-10",
                "text": "민수와 회의실에서 발표 준비",
                "event_type": "daily",
                "who": "민수",
                "where": "회의실",
                "when": "오전",
                "tags": ["발표", "회사"],
            },
            {
                "id": str(second.id),
                "diary_date": "2026-07-10",
                "text": "혼자 산책하며 기분 전환",
                "event_type": "daily",
                "who": None,
                "where": None,
                "when": None,
                "tags": [],
            },
        ],
    }
    assert "embedding" not in result["items"][0]
    assert "created_at" not in result["items"][0]


async def test_search_diary_memories_tool_returns_empty_result_and_propagates_errors():
    empty_query = _FakeDiaryMemoryQuery([])
    tool = create_search_diary_memories_tool(
        empty_query,
        AgentToolExecutionContext(device_id="dev-a"),
    )

    assert await tool.ainvoke({"query": "기억"}) == {"count": 0, "items": []}

    failing_tool = create_search_diary_memories_tool(
        _FakeDiaryMemoryQuery(error=RuntimeError("query failed")),
        AgentToolExecutionContext(device_id="dev-a"),
    )

    with pytest.raises(RuntimeError, match="query failed"):
        await failing_tool.ainvoke({"query": "기억"})


def test_search_health_records_tool_contract_and_input_schema():
    tool = create_search_health_records_tool(
        _FakeHealthRecordQuery(),
        AgentToolExecutionContext(device_id="dev-a", session_id=uuid4()),
    )

    assert tool.name == "search_health_records"
    assert tool.description
    assert "Purpose:" in tool.description
    assert "Use when:" in tool.description
    assert "Do not use when:" in tool.description
    assert tool.return_direct is False
    assert set(tool.args_schema.model_json_schema()["properties"]) == {"query", "limit"}
    assert "device_id" not in tool.args_schema.model_json_schema()["properties"]
    assert "session_id" not in tool.args_schema.model_json_schema()["properties"]

    parsed = SearchHealthRecordsInput.model_validate({"query": "  걸음 수  "})
    assert parsed.query == "걸음 수"
    assert parsed.limit == 5

    for invalid_query in ("", "   "):
        with pytest.raises(ValidationError):
            SearchHealthRecordsInput.model_validate({"query": invalid_query})

    for invalid_limit in (0, 11):
        with pytest.raises(ValidationError):
            SearchHealthRecordsInput.model_validate({"query": "건강", "limit": invalid_limit})


async def test_search_health_records_tool_calls_query_service_and_returns_dto():
    first = _health_chunk(text="9,144걸음을 걸었어.", data_types=["steps"])
    second = _health_chunk(text="수면 시간이 7시간이었어.", data_types=["sleep"])
    query_service = _FakeHealthRecordQuery([first, second])
    tool = create_search_health_records_tool(
        query_service,
        AgentToolExecutionContext(device_id="dev-a", session_id=uuid4()),
    )

    result = await tool.ainvoke({"query": "  어제 활동  ", "limit": 2})

    assert query_service.calls == [{"device_id": "dev-a", "query": "어제 활동", "limit": 2}]
    assert result == {
        "count": 2,
        "items": [
            {
                "id": str(first.id),
                "record_date": "2026-07-11",
                "text": "9,144걸음을 걸었어.",
                "data_types": ["steps"],
            },
            {
                "id": str(second.id),
                "record_date": "2026-07-11",
                "text": "수면 시간이 7시간이었어.",
                "data_types": ["sleep"],
            },
        ],
    }
    assert "embedding" not in result["items"][0]
    assert "created_at" not in result["items"][0]


async def test_search_health_records_tool_returns_empty_result_and_propagates_errors():
    empty_query = _FakeHealthRecordQuery([])
    tool = create_search_health_records_tool(
        empty_query,
        AgentToolExecutionContext(device_id="dev-a"),
    )

    assert await tool.ainvoke({"query": "건강"}) == {"count": 0, "items": []}

    failing_tool = create_search_health_records_tool(
        _FakeHealthRecordQuery(error=RuntimeError("query failed")),
        AgentToolExecutionContext(device_id="dev-a"),
    )

    with pytest.raises(RuntimeError, match="query failed"):
        await failing_tool.ainvoke({"query": "건강"})


def test_create_read_tools_returns_request_scoped_tools_without_service_calls():
    diary_query = _FakeDiaryMemoryQuery()
    health_query = _FakeHealthRecordQuery()
    context = AgentToolExecutionContext(device_id="dev-a", session_id=uuid4())

    tools = create_read_tools(diary_query, health_query, context)
    next_tools = create_read_tools(diary_query, health_query, context)

    assert [tool.name for tool in tools] == ["search_diary_memories", "search_health_records"]
    assert len({tool.name for tool in tools}) == 2
    assert tools[0] is not next_tools[0]
    assert tools[1] is not next_tools[1]
    assert diary_query.calls == []
    assert health_query.calls == []
