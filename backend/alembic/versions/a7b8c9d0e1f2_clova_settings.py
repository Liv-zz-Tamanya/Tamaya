"""BYOK CLOVA 설정 테이블 신설 (G003 BYOK-CLOVA)

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-06-08 00:00:00.000000

신규 테이블:
  - clova_settings: device_id별 마스킹 키 프리뷰(••••last4) + has_key 플래그.
    원문 CLOVA 키는 서버에 저장하지 않는다(BYOK — 클라이언트가 보관, 요청별 헤더 전송).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision: str = "a7b8c9d0e1f2"
down_revision: str | Sequence[str] | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "clova_settings",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("device_id", sa.String(64), nullable=False, unique=True),
        sa.Column("masked_key", sa.String(64), nullable=False),
        sa.Column("has_key", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("clova_settings")
