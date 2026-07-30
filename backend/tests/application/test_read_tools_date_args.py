"""검색 tool의 날짜 argument 스키마 — 보존·검증·미지정 호환 검증."""

from __future__ import annotations

from datetime import date

import pytest

from app.application.tool.read_tools import (
    AgentToolExecutionContext,
    SearchDiaryMemoriesInput,
    SearchHealthRecordsInput,
    create_search_diary_memories_tool,
)

CONTEXT = AgentToolExecutionContext(device_id="dev-1")


class _CapturingDiaryQuery:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def search_similar(self, device_id, query, exclude_session_id=None, limit=5,
                             start_date=None, end_date=None):
        self.calls.append({
            "device_id": device_id, "query": query, "limit": limit,
            "start_date": start_date, "end_date": end_date,
        })
        return []


def test_schema_accepts_iso_dates():
    parsed = SearchDiaryMemoriesInput(
        query="발표", start_date="2026-07-20", end_date="2026-07-20"
    )
    assert parsed.start_date == date(2026, 7, 20)
    assert parsed.end_date == date(2026, 7, 20)


def test_schema_defaults_to_no_dates():
    parsed = SearchHealthRecordsInput(query="걸음수")
    assert parsed.start_date is None and parsed.end_date is None


def test_schema_rejects_inverted_range():
    with pytest.raises(ValueError):
        SearchDiaryMemoriesInput(query="발표", start_date="2026-07-21", end_date="2026-07-20")
    with pytest.raises(ValueError):
        SearchHealthRecordsInput(query="걸음", start_date="2026-07-21", end_date="2026-07-20")


async def test_tool_preserves_date_arguments_to_service():
    query_service = _CapturingDiaryQuery()
    tool = create_search_diary_memories_tool(query_service, CONTEXT)

    result = await tool.coroutine(
        query="발표", start_date=date(2026, 7, 20), end_date=date(2026, 7, 20)
    )

    call = query_service.calls[0]
    assert call["start_date"] == date(2026, 7, 20)
    assert call["end_date"] == date(2026, 7, 20)
    # 날짜 조건에 결과가 없으면 빈 결과 그대로 — 다른 날짜 fallback 없음
    assert result == {"count": 0, "items": []}


def test_tool_description_states_date_policy():
    tool = create_search_diary_memories_tool(_CapturingDiaryQuery(), CONTEXT)
    assert "do not drop, widen, or guess" in tool.description
    assert "do not\nretry with different dates" in tool.description or "do not retry with different dates" in tool.description
