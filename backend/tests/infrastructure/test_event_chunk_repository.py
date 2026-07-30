from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from app.infrastructure.persistence.event_chunk_repository_impl import EventChunkRepositoryImpl


class _FakeScalars:
    def all(self):
        return []


class _FakeResult:
    def scalars(self):
        return _FakeScalars()


class _CapturingDb:
    def __init__(self) -> None:
        self.statement = None

    async def execute(self, statement):
        self.statement = statement
        return _FakeResult()


@pytest.mark.asyncio
async def test_event_chunk_search_scopes_sql_by_device_before_similarity_limit():
    db = _CapturingDb()
    repo = EventChunkRepositoryImpl(db)
    excluded_session_id = uuid4()

    await repo.search_similar(
        device_id="dev-a",
        embedding=[0.1] * 384,
        limit=3,
        exclude_session_id=excluded_session_id,
    )

    compiled = str(db.statement.compile(dialect=postgresql.dialect()))
    params = db.statement.compile(dialect=postgresql.dialect()).params

    assert "FROM event_chunks JOIN chat_sessions" in compiled
    assert "event_chunks.chat_session_id = chat_sessions.id" in compiled
    assert "chat_sessions.device_id = " in compiled
    assert "event_chunks.chat_session_id != " in compiled
    assert "ORDER BY event_chunks.embedding <=> " in compiled
    assert "LIMIT " in compiled
    assert params["device_id_1"] == "dev-a"
    assert params["chat_session_id_1"] == excluded_session_id
    assert params["param_1"] == 3


@pytest.mark.asyncio
async def test_event_chunk_search_applies_date_range_with_device_and_session_filters():
    db = _CapturingDb()
    repo = EventChunkRepositoryImpl(db)
    excluded_session_id = uuid4()

    await repo.search_similar(
        device_id="dev-a",
        embedding=[0.1] * 384,
        limit=15,
        exclude_session_id=excluded_session_id,
        start_date=date(2026, 7, 20),
        end_date=date(2026, 7, 21),
    )

    compiled = str(db.statement.compile(dialect=postgresql.dialect()))
    params = db.statement.compile(dialect=postgresql.dialect()).params

    # 날짜는 임베딩이 아니라 SQL 조건 — 기존 격리 조건과 함께 적용된다
    assert "chat_sessions.device_id = " in compiled
    assert "event_chunks.chat_session_id != " in compiled
    assert "event_chunks.diary_date >= " in compiled
    assert "event_chunks.diary_date <= " in compiled
    assert params["diary_date_1"] == date(2026, 7, 20)
    assert params["diary_date_2"] == date(2026, 7, 21)
    assert params["param_1"] == 15


@pytest.mark.asyncio
async def test_event_chunk_search_exact_date_uses_equal_bounds():
    db = _CapturingDb()
    repo = EventChunkRepositoryImpl(db)

    await repo.search_similar(
        device_id="dev-a",
        embedding=[0.1] * 384,
        start_date=date(2026, 7, 20),
        end_date=date(2026, 7, 20),
    )

    params = db.statement.compile(dialect=postgresql.dialect()).params
    assert params["diary_date_1"] == params["diary_date_2"] == date(2026, 7, 20)


@pytest.mark.asyncio
async def test_event_chunk_search_without_dates_has_no_date_condition():
    db = _CapturingDb()
    repo = EventChunkRepositoryImpl(db)

    await repo.search_similar(device_id="dev-a", embedding=[0.1] * 384)

    compiled = str(db.statement.compile(dialect=postgresql.dialect()))
    # 날짜 미지정 시 WHERE에 날짜 조건이 없어야 한다(기존 검색 동작 유지)
    assert "diary_date >= " not in compiled
    assert "diary_date <= " not in compiled
