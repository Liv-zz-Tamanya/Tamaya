from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from app.infrastructure.persistence.health_chunk_repository_impl import HealthChunkRepositoryImpl
from app.infrastructure.persistence.health_record_repository_impl import HealthRecordRepositoryImpl
from app.infrastructure.persistence.health_session_repository_impl import (
    HealthSessionRepositoryImpl,
)
from app.infrastructure.persistence.models import HealthDailySummaryModel


class _FakeScalars:
    def all(self):
        return []


class _FakeResult:
    def scalar(self):
        return False

    def scalar_one_or_none(self):
        return None

    def scalars(self):
        return _FakeScalars()


class _CapturingDb:
    def __init__(self) -> None:
        self.statement = None

    async def execute(self, statement):
        self.statement = statement
        return _FakeResult()


@pytest.mark.asyncio
async def test_health_session_lookup_filters_by_session_and_device():
    db = _CapturingDb()
    repo = HealthSessionRepositoryImpl(db)
    session_id = uuid4()

    await repo.find_by_id(session_id, "dev-a")

    compiled = db.statement.compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert "health_sessions.id = " in sql
    assert "health_sessions.device_id = " in sql
    assert compiled.params["id_1"] == session_id
    assert compiled.params["device_id_1"] == "dev-a"


@pytest.mark.asyncio
async def test_health_chunk_similarity_search_filters_by_device_before_limit():
    db = _CapturingDb()
    repo = HealthChunkRepositoryImpl(db)

    await repo.search_similar(device_id="dev-a", embedding=[0.1] * 384, limit=3)

    compiled = db.statement.compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert "WHERE health_chunks.device_id = " in sql
    assert "ORDER BY health_chunks.embedding <=> " in sql
    assert "LIMIT " in sql
    assert compiled.params["device_id_1"] == "dev-a"
    assert compiled.params["param_1"] == 3


@pytest.mark.asyncio
async def test_health_record_source_hash_check_is_scoped_by_device():
    db = _CapturingDb()
    repo = HealthRecordRepositoryImpl(db)

    await repo.source_hash_exists("dev-a", "hash-x")

    compiled = db.statement.compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert "health_daily_summaries.device_id = " in sql
    assert "health_daily_summaries.source_hash = " in sql
    assert compiled.params["device_id_1"] == "dev-a"
    assert compiled.params["source_hash_1"] == "hash-x"


def test_health_daily_summary_uses_device_scoped_uniques():
    constraints = {
        constraint.name: tuple(constraint.columns.keys())
        for constraint in HealthDailySummaryModel.__table__.constraints
    }

    assert constraints["uq_health_daily_device_record_date"] == ("device_id", "record_date")
    assert constraints["uq_health_daily_device_source_hash"] == ("device_id", "source_hash")
    assert not any(columns == ("record_date",) for columns in constraints.values())
    assert not any(columns == ("source_hash",) for columns in constraints.values())
