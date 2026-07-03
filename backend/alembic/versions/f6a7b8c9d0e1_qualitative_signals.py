"""정성신호 테이블 신설 (G002 Backend-Insight)

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-06-08 00:00:00.000000

신규 테이블:
  - qualitative_signals: 코칭 대화에서 추출한 정성신호(정서 + 건강행동 언급).
    device_id 키잉(User 테이블 없음), session_id는 coaching_sessions 부재로 FK 없음.
    behavior_mentions는 JSONB([{behavior, polarity}]). 벡터 컬럼 없음(구조화 데이터).
    (device_id, recorded_date) 복합 인덱스로 주/월 기간 집계를 가속.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision: str = "f6a7b8c9d0e1"
down_revision: str | Sequence[str] | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "qualitative_signals",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("device_id", sa.String(64), nullable=False),
        sa.Column("session_id", PG_UUID(as_uuid=True), nullable=True),
        sa.Column("emotion", sa.String(20), nullable=False),
        sa.Column("behavior_mentions", JSONB, nullable=False, server_default="[]"),
        sa.Column("recorded_date", sa.Date, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_qualitative_signals_device_date",
        "qualitative_signals",
        ["device_id", "recorded_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_qualitative_signals_device_date", table_name="qualitative_signals")
    op.drop_table("qualitative_signals")
