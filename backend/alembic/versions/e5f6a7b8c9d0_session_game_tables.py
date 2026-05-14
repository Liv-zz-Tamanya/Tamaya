"""Session strict 1세션 + 키우기 게임 테이블 신설

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-14 00:00:00.000000

신규 테이블:
  - user_sessions: DEC-023 동시접속 strict 1세션 (JWT jti 블랙리스트)
  - game_progress: DEC-019 키우기 게임 진행 상태
  - reward_inventory: 보상 인벤토리

⚠️  사전 조건:
  - d4e5f6a7b8c9 (B-009 embedding 1024) 가 먼저 적용되었거나 skip 해야 함.
  - B-009 미실행 상태라면:
      alembic upgrade c3d4e5f6a7b8  (device_id UNIQUE)
      alembic upgrade e5f6a7b8c9d0  (이 파일, d4e5f6a7b8c9 건너뜀)

사용자 GO 후 실행 명령 (B-009 미실행 전제):
  cd ~/dev/liv-zz-poc/backend
  uv run alembic upgrade c3d4e5f6a7b8   # device_id UNIQUE (이미 완료 시 스킵)
  uv run alembic upgrade e5f6a7b8c9d0   # 세션 + 게임 테이블

  또는 B-009까지 포함 upgrade head:
  uv run alembic upgrade head
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. user_sessions (DEC-023: 동시접속 strict 1세션) ──────────────────────
    op.create_table(
        "user_sessions",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("device_id", sa.String(64), nullable=True, index=True),
        sa.Column("kakao_id", sa.String(64), nullable=True, index=True),
        sa.Column("jti", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("issued_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("revoked_at", sa.DateTime, nullable=True),
    )

    # ── 2. game_progress (DEC-019: 키우기 게임) ────────────────────────────────
    op.create_table(
        "game_progress",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("device_id", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("current_streak", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_diaries", sa.Integer, nullable=False, server_default="0"),
        sa.Column("points", sa.Integer, nullable=False, server_default="0"),
        sa.Column("level", sa.Integer, nullable=False, server_default="1"),
        sa.Column("affinity", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_diary_date", sa.Date, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # ── 3. reward_inventory (DEC-019: 보상 인벤토리) ──────────────────────────
    op.create_table(
        "reward_inventory",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("device_id", sa.String(64), nullable=False, index=True),
        sa.Column("reward_id", sa.String(50), nullable=False),
        sa.Column("reward_type", sa.String(20), nullable=False),
        sa.Column("claimed_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("is_used", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("used_at", sa.DateTime, nullable=True),
        sa.UniqueConstraint("device_id", "reward_id", name="uq_device_reward"),
    )


def downgrade() -> None:
    op.drop_table("reward_inventory")
    op.drop_table("game_progress")
    op.drop_table("user_sessions")
