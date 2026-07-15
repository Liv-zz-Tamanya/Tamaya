"""건강 세션과 데이터에 device_id 소유권 추가

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-07-15 00:00:00.000000

기존 소유자 없는 건강 데이터는 device_id NULL로 유지한다. 애플리케이션 조회는
인증된 device_id로만 필터링하므로 NULL 레거시 행은 실제 사용자 요청에 노출되지 않는다.

downgrade에서 전역 record_date/source_hash UNIQUE를 복구할 때 사용자별 중복 데이터가
이미 존재하면 DB 제약 충돌로 실패할 수 있다. 이를 피하기 위해 사용자 데이터를 삭제하지 않는다.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "b4c5d6e7f8a9"
down_revision: str | Sequence[str] | None = "a3b4c5d6e7f8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    _ensure_health_sessions_table()
    _ensure_health_daily_summaries_table()
    _ensure_health_chunks_table()

    if not _column_exists("health_sessions", "device_id"):
        op.add_column("health_sessions", sa.Column("device_id", sa.String(length=64), nullable=True))
    if not _index_exists("ix_health_sessions_device_id"):
        op.create_index("ix_health_sessions_device_id", "health_sessions", ["device_id"])

    if not _column_exists("health_daily_summaries", "device_id"):
        op.add_column(
            "health_daily_summaries",
            sa.Column("device_id", sa.String(length=64), nullable=True),
        )
    if _constraint_exists("health_daily_summaries_record_date_key"):
        op.drop_constraint(
            "health_daily_summaries_record_date_key",
            "health_daily_summaries",
            type_="unique",
        )
    if _constraint_exists("health_daily_summaries_source_hash_key"):
        op.drop_constraint(
            "health_daily_summaries_source_hash_key",
            "health_daily_summaries",
            type_="unique",
        )
    if not _index_exists("ix_health_daily_summaries_device_id"):
        op.create_index(
            "ix_health_daily_summaries_device_id", "health_daily_summaries", ["device_id"]
        )
    if not _constraint_exists("uq_health_daily_device_record_date"):
        op.create_unique_constraint(
            "uq_health_daily_device_record_date",
            "health_daily_summaries",
            ["device_id", "record_date"],
        )
    if not _constraint_exists("uq_health_daily_device_source_hash"):
        op.create_unique_constraint(
            "uq_health_daily_device_source_hash",
            "health_daily_summaries",
            ["device_id", "source_hash"],
        )
    if not _index_exists("ix_health_daily_device_record_date"):
        op.create_index(
            "ix_health_daily_device_record_date",
            "health_daily_summaries",
            ["device_id", "record_date"],
        )

    if not _column_exists("health_chunks", "device_id"):
        op.add_column("health_chunks", sa.Column("device_id", sa.String(length=64), nullable=True))
    if _index_exists("ix_health_chunks_record_date"):
        op.drop_index("ix_health_chunks_record_date", table_name="health_chunks")
    if not _index_exists("ix_health_chunks_device_id"):
        op.create_index("ix_health_chunks_device_id", "health_chunks", ["device_id"])
    if not _index_exists("ix_health_chunks_device_record_date"):
        op.create_index(
            "ix_health_chunks_device_record_date",
            "health_chunks",
            ["device_id", "record_date"],
        )


def downgrade() -> None:
    if _table_exists("health_chunks"):
        if _index_exists("ix_health_chunks_device_record_date"):
            op.drop_index("ix_health_chunks_device_record_date", table_name="health_chunks")
        if _index_exists("ix_health_chunks_device_id"):
            op.drop_index("ix_health_chunks_device_id", table_name="health_chunks")
        if _column_exists("health_chunks", "device_id"):
            op.drop_column("health_chunks", "device_id")
        if not _index_exists("ix_health_chunks_record_date"):
            op.create_index("ix_health_chunks_record_date", "health_chunks", ["record_date"])

    if _table_exists("health_daily_summaries"):
        if _index_exists("ix_health_daily_device_record_date"):
            op.drop_index("ix_health_daily_device_record_date", table_name="health_daily_summaries")
        if _index_exists("ix_health_daily_summaries_device_id"):
            op.drop_index("ix_health_daily_summaries_device_id", table_name="health_daily_summaries")
        if _constraint_exists("uq_health_daily_device_source_hash"):
            op.drop_constraint(
                "uq_health_daily_device_source_hash",
                "health_daily_summaries",
                type_="unique",
            )
        if _constraint_exists("uq_health_daily_device_record_date"):
            op.drop_constraint(
                "uq_health_daily_device_record_date",
                "health_daily_summaries",
                type_="unique",
            )
        if not _constraint_exists("health_daily_summaries_record_date_key"):
            op.create_unique_constraint(
                "health_daily_summaries_record_date_key",
                "health_daily_summaries",
                ["record_date"],
            )
        if not _constraint_exists("health_daily_summaries_source_hash_key"):
            op.create_unique_constraint(
                "health_daily_summaries_source_hash_key",
                "health_daily_summaries",
                ["source_hash"],
            )
        if _column_exists("health_daily_summaries", "device_id"):
            op.drop_column("health_daily_summaries", "device_id")

    if _table_exists("health_sessions"):
        if _index_exists("ix_health_sessions_device_id"):
            op.drop_index("ix_health_sessions_device_id", table_name="health_sessions")
        if _column_exists("health_sessions", "device_id"):
            op.drop_column("health_sessions", "device_id")


def _ensure_health_sessions_table() -> None:
    if _table_exists("health_sessions"):
        return
    op.create_table(
        "health_sessions",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("device_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "health_messages",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", PG_UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["session_id"], ["health_sessions.id"]),
    )


def _ensure_health_daily_summaries_table() -> None:
    if _table_exists("health_daily_summaries"):
        return
    op.create_table(
        "health_daily_summaries",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("device_id", sa.String(64), nullable=True),
        sa.Column("record_date", sa.Date, nullable=False),
        sa.Column("step_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("step_goal", sa.Integer, nullable=False, server_default="0"),
        sa.Column("step_goal_achieved", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("step_calories", sa.Float, nullable=False, server_default="0"),
        sa.Column("step_distance_m", sa.Float, nullable=False, server_default="0"),
        sa.Column("has_exercise", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("exercise_duration_sec", sa.Integer, nullable=False, server_default="0"),
        sa.Column("exercise_distance_m", sa.Float, nullable=False, server_default="0"),
        sa.Column("exercise_calories", sa.Float, nullable=False, server_default="0"),
        sa.Column("heart_rate_avg", sa.Float, nullable=True),
        sa.Column("heart_rate_min", sa.Float, nullable=True),
        sa.Column("heart_rate_max", sa.Float, nullable=True),
        sa.Column("floors_climbed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )


def _ensure_health_chunks_table() -> None:
    if _table_exists("health_chunks"):
        return
    op.create_table(
        "health_chunks",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("device_id", sa.String(64), nullable=True),
        sa.Column("record_date", sa.Date, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column("data_types", ARRAY(sa.String()), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    return bool(bind.execute(sa.text("SELECT to_regclass(:name)"), {"name": table_name}).scalar())


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    return bool(
        bind.execute(
            sa.text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = :table_name AND column_name = :column_name
                """
            ),
            {"table_name": table_name, "column_name": column_name},
        ).scalar()
    )


def _constraint_exists(constraint_name: str) -> bool:
    bind = op.get_bind()
    return bool(
        bind.execute(
            sa.text("SELECT 1 FROM pg_constraint WHERE conname = :name"),
            {"name": constraint_name},
        ).scalar()
    )


def _index_exists(index_name: str) -> bool:
    bind = op.get_bind()
    return bool(
        bind.execute(
            sa.text("SELECT 1 FROM pg_indexes WHERE indexname = :name"),
            {"name": index_name},
        ).scalar()
    )
