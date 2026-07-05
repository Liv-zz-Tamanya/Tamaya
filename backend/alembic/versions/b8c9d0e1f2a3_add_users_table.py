"""닉네임 기반 데모 계정 테이블 신설

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-07-05 00:00:00.000000

신규 테이블:
  - users: 닉네임 UNIQUE 데모 계정 (회원가입/로그인 통합 식별)

실행:
  cd backend
  uv run alembic upgrade head
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "b8c9d0e1f2a3"
down_revision: str | Sequence[str] | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("nickname", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("nickname", name="uq_users_nickname"),
    )
    op.create_index("ix_users_nickname", "users", ["nickname"])


def downgrade() -> None:
    op.drop_index("ix_users_nickname", table_name="users")
    op.drop_table("users")
