from __future__ import annotations

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

    assert "FROM event_chunks JOIN chat_sessions" in compiled
    assert "event_chunks.chat_session_id = chat_sessions.id" in compiled
    assert "chat_sessions.device_id = " in compiled
    assert "event_chunks.chat_session_id != " in compiled
    assert "ORDER BY event_chunks.embedding <=> " in compiled
    assert "LIMIT " in compiled
