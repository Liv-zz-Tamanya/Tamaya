"""diaries.satisfaction_estimated 플래그 추가

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
Create Date: 2026-07-28 00:00:00.000000

satisfaction의 '모름'(LLM이 null을 내거나 값이 부적절해 백엔드가 채운 중립 50)과
실제 '중립 판단 50'을 구분한다. 인사이트 집계·상관분석에서 estimated 행을
제외하기 위한 전제. server_default가 있어 기존 행이 있어도 안전하다.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e7f8a9b0c1d2"
down_revision: str | Sequence[str] | None = "d6e7f8a9b0c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "diaries",
        sa.Column(
            "satisfaction_estimated",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    op.drop_column("diaries", "satisfaction_estimated")
