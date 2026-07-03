"""B-005/B-008: device_id 컬럼 추가 + 복합 UNIQUE 재설정 (multi-tenant 대응)

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-14 00:00:00.000000

배경:
- B-005/B-008: chat_sessions.session_date UNIQUE, diaries.diary_date UNIQUE 가 단일 사용자 가정.
- 2명 이상 동시 접속 시 즉시 IntegrityError → 502.
- device_id VARCHAR(64) 추가 후 (device_id, session_date) 복합 UNIQUE로 재설정.
- 기존 PoC 데이터: device_id = 'legacy_poc' 로 일괄 업데이트 후 제약 적용.

사용자 확인 후 실행:
  cd ~/dev/liv-zz-poc/backend && uv run alembic upgrade head
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. chat_sessions ──────────────────────────────────────────────────
    # device_id 컬럼 추가 (nullable 허용 → 기존 데이터 레거시 처리 후 NOT NULL 예정)
    op.add_column(
        "chat_sessions",
        sa.Column("device_id", sa.String(length=64), nullable=True),
    )
    # 기존 PoC 행 backfill
    op.execute("UPDATE chat_sessions SET device_id = 'legacy_poc' WHERE device_id IS NULL")
    # 단일 session_date UNIQUE 제약 제거
    op.drop_constraint("chat_sessions_session_date_key", "chat_sessions", type_="unique")
    # 복합 UNIQUE 추가
    op.create_unique_constraint(
        "uq_chat_sessions_device_session_date",
        "chat_sessions",
        ["device_id", "session_date"],
    )

    # ── 2. diaries ────────────────────────────────────────────────────────
    op.add_column(
        "diaries",
        sa.Column("device_id", sa.String(length=64), nullable=True),
    )
    op.execute("UPDATE diaries SET device_id = 'legacy_poc' WHERE device_id IS NULL")
    op.drop_constraint("diaries_diary_date_key", "diaries", type_="unique")
    op.create_unique_constraint(
        "uq_diaries_device_diary_date",
        "diaries",
        ["device_id", "diary_date"],
    )


def downgrade() -> None:
    # diaries
    op.drop_constraint("uq_diaries_device_diary_date", "diaries", type_="unique")
    op.create_unique_constraint("diaries_diary_date_key", "diaries", ["diary_date"])
    op.drop_column("diaries", "device_id")

    # chat_sessions
    op.drop_constraint("uq_chat_sessions_device_session_date", "chat_sessions", type_="unique")
    op.create_unique_constraint("chat_sessions_session_date_key", "chat_sessions", ["session_date"])
    op.drop_column("chat_sessions", "device_id")
