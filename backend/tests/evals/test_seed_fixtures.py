"""seed plan 생성·중복 방지·DB 안전장치 테스트 (DB 접근 없음, mock embedding)."""

import hashlib

import pytest

from app.infrastructure.config.settings import settings
from evals.seed_fixtures import (
    EMBEDDING_DIMENSIONS,
    build_seed_plan,
    fixture_uuid,
    require_eval_database_url,
    reset,
    split_new_rows,
)
from evals.validate_fixtures import FIXTURE_DIR, load_fixture_set


class FakeEmbedding:
    """텍스트 해시 기반의 결정론적 mock embedding — 모델 로드 없이 시드 로직을 검증한다."""

    def __init__(self, dimensions: int = EMBEDDING_DIMENSIONS) -> None:
        self._dimensions = dimensions
        self.calls: list[list[str]] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        return [self._vector(text) for text in texts]

    def _vector(self, text: str) -> list[float]:
        seed = hashlib.sha256(text.encode("utf-8")).digest()
        return [seed[i % len(seed)] / 255 for i in range(self._dimensions)]


@pytest.fixture(scope="module")
def fixtures():
    return load_fixture_set(FIXTURE_DIR)


def test_build_seed_plan_row_counts_match_fixtures(fixtures):
    plan = build_seed_plan(fixtures, FakeEmbedding())
    assert len(plan.sessions) == len(fixtures.diary_days)
    assert len(plan.chat_messages) == sum(len(day.messages) for day in fixtures.diary_days)
    assert len(plan.event_chunks) == sum(len(day.gold_chunks) for day in fixtures.diary_days)
    assert len(plan.health_chunks) == len(fixtures.health_days)


def test_build_seed_plan_embeds_each_text_once(fixtures):
    embedding = FakeEmbedding()
    plan = build_seed_plan(fixtures, embedding)
    # 임베딩은 배치 1회 호출 — chunk 텍스트와 health 텍스트가 정확히 한 번씩
    assert len(embedding.calls) == 1
    assert len(embedding.calls[0]) == len(plan.event_chunks) + len(plan.health_chunks)
    # 각 행의 임베딩이 자기 텍스트의 임베딩과 짝지어졌는지 확인
    for chunk in plan.event_chunks:
        assert chunk.embedding == embedding._vector(chunk.text)
    for chunk in plan.health_chunks:
        assert chunk.embedding == embedding._vector(chunk.text)


def test_build_seed_plan_ids_are_deterministic(fixtures):
    first = build_seed_plan(fixtures, FakeEmbedding())
    second = build_seed_plan(fixtures, FakeEmbedding())
    assert [row.id for row in first.event_chunks] == [row.id for row in second.event_chunks]
    assert [row.id for row in first.sessions] == [row.id for row in second.sessions]
    assert [row.id for row in first.chat_messages] == [row.id for row in second.chat_messages]
    assert [row.id for row in first.health_chunks] == [row.id for row in second.health_chunks]


def test_event_chunks_reference_seeded_sessions(fixtures):
    plan = build_seed_plan(fixtures, FakeEmbedding())
    session_ids = {session.id for session in plan.sessions}
    assert all(chunk.chat_session_id in session_ids for chunk in plan.event_chunks)
    assert all(message.session_id in session_ids for message in plan.chat_messages)


def test_wrong_embedding_dimension_is_rejected(fixtures):
    with pytest.raises(ValueError, match="임베딩 차원"):
        build_seed_plan(fixtures, FakeEmbedding(dimensions=3))


def test_fixture_uuid_separates_kinds():
    assert fixture_uuid("event-chunk", "x") != fixture_uuid("health-chunk", "x")
    assert fixture_uuid("event-chunk", "x") == fixture_uuid("event-chunk", "x")


def test_split_new_rows_skips_existing(fixtures):
    plan = build_seed_plan(fixtures, FakeEmbedding())
    existing = {plan.event_chunks[0].id, plan.event_chunks[1].id}
    new_rows, skipped = split_new_rows(plan.event_chunks, existing)
    assert len(skipped) == 2
    assert len(new_rows) == len(plan.event_chunks) - 2
    assert all(row.id not in existing for row in new_rows)


def test_production_database_url_is_rejected():
    with pytest.raises(ValueError, match="운영 database_url"):
        require_eval_database_url(settings.database_url)


def test_database_name_without_eval_is_rejected():
    with pytest.raises(ValueError, match="'eval'"):
        require_eval_database_url("postgresql+asyncpg://user:pw@localhost:5432/aidiary_backup")


def test_default_eval_database_url_is_accepted():
    url = require_eval_database_url(settings.eval_database_url)
    assert "eval" in url.database


async def test_reset_refuses_non_eval_device_ids():
    # 안전장치가 DB 접근 전에 발동하므로 engine 없이 검증 가능
    with pytest.raises(ValueError, match="eval- 접두사"):
        await reset(None, ["real-user-1"])
