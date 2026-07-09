"""게임 일기 완료 처리 이력 테이블 신설

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-07-09 00:00:00.000000

신규 테이블:
  - game_diary_completions: device_id + diary_date 단위 멱등 처리 이력
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "c9d0e1f2a3b4"
down_revision: str | Sequence[str] | None = "b8c9d0e1f2a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "game_diary_completions",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("device_id", sa.String(64), nullable=False),
        sa.Column("diary_date", sa.Date, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("device_id", "diary_date", name="uq_game_diary_completion"),
    )
    op.create_index(
        "ix_game_diary_completions_device_id",
        "game_diary_completions",
        ["device_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_game_diary_completions_device_id", table_name="game_diary_completions")
    op.drop_table("game_diary_completions")
