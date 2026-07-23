"""평가 전용 DB에 fixture를 시드/리셋하는 CLI.

    uv run python -m evals.seed_fixtures              # 시드 (이미 있는 행은 skip)
    uv run python -m evals.seed_fixtures --reset      # eval 데이터 삭제 후 재시드
    uv run python -m evals.seed_fixtures --reset-only # 삭제만

안전장치:
- 대상 DB명이 운영 DB와 같거나 이름에 "eval"이 없으면 실행을 거부한다.
- reset은 fixture의 eval- 접두사 device_id 스코프 안에서만 삭제한다.
- 모든 id는 uuid5로 결정론 생성되어 재실행해도 중복 삽입되지 않는다.

임베딩은 프로덕션과 동일한 로컬 sentence-transformers 모델을 사용한다
(외부 API 아님 — 비용 0, 결정론적).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from pathlib import Path
from uuid import UUID, uuid5

from sqlalchemy import delete, select, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.application.service.embedding_service import EmbeddingService
from app.infrastructure.config.settings import settings
from app.infrastructure.persistence.models import (
    Base,
    ChatMessageModel,
    ChatSessionModel,
    EventChunkModel,
    HealthChunkModel,
)
from evals.fixture_schemas import EVAL_DEVICE_PREFIX
from evals.validate_fixtures import FIXTURE_DIR, FixtureSet, load_fixture_set

EVAL_FIXTURE_NAMESPACE = UUID("5d1f6b64-4d6c-4d4e-9a3b-2f8b7c1d9e42")
EMBEDDING_DIMENSIONS = 384  # persistence models의 Vector(384)와 일치해야 한다


def fixture_uuid(kind: str, key: str) -> UUID:
    """fixture 키에서 결정론적 UUID를 만든다 — 재시드 시 같은 행은 같은 id."""
    return uuid5(EVAL_FIXTURE_NAMESPACE, f"{kind}:{key}")


@dataclass
class SeedPlan:
    sessions: list[ChatSessionModel] = field(default_factory=list)
    chat_messages: list[ChatMessageModel] = field(default_factory=list)
    event_chunks: list[EventChunkModel] = field(default_factory=list)
    health_chunks: list[HealthChunkModel] = field(default_factory=list)


def build_seed_plan(fixtures: FixtureSet, embedding_service: EmbeddingService) -> SeedPlan:
    """fixture를 ORM 행으로 변환한다. 임베딩은 chunk 텍스트에 대해서만 생성."""
    chunk_texts = [chunk.text for day in fixtures.diary_days for chunk in day.gold_chunks]
    health_texts = [day.text for day in fixtures.health_days]
    embeddings = embedding_service.embed(chunk_texts + health_texts) if chunk_texts or health_texts else []
    for embedding in embeddings:
        if len(embedding) != EMBEDDING_DIMENSIONS:
            raise ValueError(
                f"임베딩 차원 오류: {len(embedding)} (expected {EMBEDDING_DIMENSIONS})"
            )
    chunk_embeddings = embeddings[: len(chunk_texts)]
    health_embeddings = embeddings[len(chunk_texts):]

    plan = SeedPlan()
    embedding_index = 0
    for day in fixtures.diary_days:
        session_id = fixture_uuid("chat-session", f"{day.device_id}:{day.session_date}")
        # created_at을 고정 시각으로 두어 재시드에도 동일한 정렬 순서를 보장한다
        base_time = datetime.combine(day.session_date, time(21, 0))
        plan.sessions.append(
            ChatSessionModel(
                id=session_id,
                device_id=day.device_id,
                session_date=day.session_date,
                max_turns=5,
                is_finalized=True,
                created_at=base_time,
            )
        )
        for index, message in enumerate(day.messages):
            plan.chat_messages.append(
                ChatMessageModel(
                    id=fixture_uuid("chat-message", f"{day.fixture_id}:{index}"),
                    session_id=session_id,
                    role=message.role,
                    content=message.content,
                    created_at=base_time + timedelta(minutes=index),
                )
            )
        for chunk in day.gold_chunks:
            plan.event_chunks.append(
                EventChunkModel(
                    id=fixture_uuid("event-chunk", chunk.chunk_id),
                    chat_session_id=session_id,
                    diary_date=day.session_date,
                    text=chunk.text,
                    embedding=chunk_embeddings[embedding_index],
                    tags=chunk.tags,
                    event_type=chunk.event_type,
                    who=chunk.who,
                    where=chunk.where,
                    when=chunk.when,
                    created_at=base_time + timedelta(minutes=30),
                )
            )
            embedding_index += 1
    for day, embedding in zip(fixtures.health_days, health_embeddings):
        plan.health_chunks.append(
            HealthChunkModel(
                id=fixture_uuid("health-chunk", day.fixture_id),
                device_id=day.device_id,
                record_date=day.record_date,
                text=day.text,
                embedding=embedding,
                data_types=list(day.data_types),
                created_at=datetime.combine(day.record_date, time(22, 0)),
            )
        )
    return plan


def split_new_rows(rows: Sequence, existing_ids: set[UUID]) -> tuple[list, list]:
    """(신규 행, 이미 존재해 skip할 행)으로 나눈다."""
    new_rows = [row for row in rows if row.id not in existing_ids]
    skipped = [row for row in rows if row.id in existing_ids]
    return new_rows, skipped


def require_eval_database_url(url_text: str) -> URL:
    """운영 DB 오염을 막는 이중 안전장치 — URL이 조건을 어기면 거부."""
    url = make_url(url_text)
    production = make_url(settings.database_url)
    if url == production:
        raise ValueError("평가 시드를 운영 database_url에 실행할 수 없습니다")
    if not url.database or "eval" not in url.database:
        raise ValueError(
            f"평가 DB 이름에는 'eval'이 포함되어야 합니다: {url.database!r}"
        )
    return url


async def ensure_database(url: URL) -> bool:
    """대상 database가 없으면 만든다. 만들었으면 True."""
    admin_url = url.set(database="postgres")
    engine = create_async_engine(
        admin_url.render_as_string(hide_password=False), isolation_level="AUTOCOMMIT"
    )
    try:
        async with engine.connect() as connection:
            exists = await connection.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": url.database},
            )
            if exists:
                return False
            await connection.execute(text(f'CREATE DATABASE "{url.database}"'))
            return True
    finally:
        await engine.dispose()


async def ensure_schema(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await connection.run_sync(Base.metadata.create_all)


async def seed(engine: AsyncEngine, plan: SeedPlan) -> dict[str, tuple[int, int]]:
    """plan을 삽입한다. 이미 존재하는 id는 skip. {table: (inserted, skipped)} 반환."""
    tables = [
        ("chat_sessions", ChatSessionModel, plan.sessions),
        ("chat_messages", ChatMessageModel, plan.chat_messages),
        ("event_chunks", EventChunkModel, plan.event_chunks),
        ("health_chunks", HealthChunkModel, plan.health_chunks),
    ]
    report: dict[str, tuple[int, int]] = {}
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        for table_name, model, rows in tables:
            ids = [row.id for row in rows]
            existing = set(
                (await session.execute(select(model.id).where(model.id.in_(ids)))).scalars()
            ) if ids else set()
            new_rows, skipped = split_new_rows(rows, existing)
            session.add_all(new_rows)
            # FK(session → message/chunk) 순서 보장을 위해 테이블 단위로 flush
            await session.flush()
            report[table_name] = (len(new_rows), len(skipped))
        await session.commit()
    return report


async def reset(engine: AsyncEngine, device_ids: Sequence[str]) -> dict[str, int]:
    """fixture 가상 사용자(eval- 접두사) 데이터만 삭제한다."""
    invalid = [device for device in device_ids if not device.startswith(EVAL_DEVICE_PREFIX)]
    if invalid:
        raise ValueError(f"eval- 접두사가 아닌 device_id는 삭제할 수 없습니다: {invalid}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        session_ids = select(ChatSessionModel.id).where(ChatSessionModel.device_id.in_(device_ids))
        deleted_chunks = await session.execute(
            delete(EventChunkModel).where(EventChunkModel.chat_session_id.in_(session_ids))
        )
        deleted_messages = await session.execute(
            delete(ChatMessageModel).where(ChatMessageModel.session_id.in_(session_ids))
        )
        deleted_sessions = await session.execute(
            delete(ChatSessionModel).where(ChatSessionModel.device_id.in_(device_ids))
        )
        deleted_health = await session.execute(
            delete(HealthChunkModel).where(HealthChunkModel.device_id.in_(device_ids))
        )
        await session.commit()
    return {
        "event_chunks": deleted_chunks.rowcount,
        "chat_messages": deleted_messages.rowcount,
        "chat_sessions": deleted_sessions.rowcount,
        "health_chunks": deleted_health.rowcount,
    }


async def _run(args: argparse.Namespace) -> int:
    url = require_eval_database_url(args.database_url)
    fixtures = load_fixture_set(args.fixture_dir)
    created = await ensure_database(url)
    if created:
        print(f"database 생성: {url.database}")
    engine = create_async_engine(url.render_as_string(hide_password=False))
    try:
        await ensure_schema(engine)
        if args.reset or args.reset_only:
            deleted = await reset(engine, fixtures.device_ids)
            print("reset 완료: " + ", ".join(f"{table} {count}행" for table, count in deleted.items()))
        if args.reset_only:
            return 0
        from app.infrastructure.external.embedding_service_impl import (
            SentenceTransformerEmbeddingService,
        )

        print("임베딩 생성 중 (로컬 sentence-transformers, 외부 API 호출 없음)...")
        plan = build_seed_plan(fixtures, SentenceTransformerEmbeddingService())
        report = await seed(engine, plan)
        for table_name, (inserted, skipped) in report.items():
            print(f"{table_name}: {inserted}행 삽입, {skipped}행 skip(이미 존재)")
        return 0
    finally:
        await engine.dispose()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="평가 전용 DB fixture 시드/리셋")
    parser.add_argument("--database-url", default=settings.eval_database_url)
    parser.add_argument("--fixture-dir", type=Path, default=FIXTURE_DIR)
    parser.add_argument("--reset", action="store_true", help="eval 데이터 삭제 후 재시드")
    parser.add_argument("--reset-only", action="store_true", help="삭제만 수행")
    args = parser.parse_args(argv)
    try:
        return asyncio.run(_run(args))
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"시드를 시작할 수 없습니다: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
