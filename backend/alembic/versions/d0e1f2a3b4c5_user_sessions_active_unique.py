"""활성 user_session 중복 방지 인덱스 추가

Revision ID: d0e1f2a3b4c5
Revises: b8c9d0e1f2a3
Create Date: 2026-07-09 00:00:00.000000

변경:
  - 활성 device 세션 partial unique index
  - 활성 kakao 세션 partial unique index
  - 단일 identity(device_id xor kakao_id) check constraint
  - 기존 중복 active 세션 정리
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d0e1f2a3b4c5"
down_revision: str | Sequence[str] | None = "b8c9d0e1f2a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM user_sessions
        WHERE (device_id IS NULL AND kakao_id IS NULL)
           OR (device_id IS NOT NULL AND kakao_id IS NOT NULL)
        """
    )

    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY device_id
                       ORDER BY issued_at DESC, id DESC
                   ) AS rn
            FROM user_sessions
            WHERE device_id IS NOT NULL
              AND revoked_at IS NULL
        )
        UPDATE user_sessions AS target
        SET revoked_at = now()
        FROM ranked
        WHERE target.id = ranked.id
          AND ranked.rn > 1
        """
    )

    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY kakao_id
                       ORDER BY issued_at DESC, id DESC
                   ) AS rn
            FROM user_sessions
            WHERE kakao_id IS NOT NULL
              AND revoked_at IS NULL
        )
        UPDATE user_sessions AS target
        SET revoked_at = now()
        FROM ranked
        WHERE target.id = ranked.id
          AND ranked.rn > 1
        """
    )

    op.create_index(
        "uq_user_sessions_active_device",
        "user_sessions",
        ["device_id"],
        unique=True,
        postgresql_where=sa.text("revoked_at IS NULL AND device_id IS NOT NULL"),
    )
    op.create_index(
        "uq_user_sessions_active_kakao",
        "user_sessions",
        ["kakao_id"],
        unique=True,
        postgresql_where=sa.text("revoked_at IS NULL AND kakao_id IS NOT NULL"),
    )
    op.create_check_constraint(
        "ck_user_sessions_single_identity",
        "user_sessions",
        "(device_id IS NOT NULL) <> (kakao_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_user_sessions_single_identity", "user_sessions", type_="check")
    op.drop_index("uq_user_sessions_active_kakao", table_name="user_sessions")
    op.drop_index("uq_user_sessions_active_device", table_name="user_sessions")
