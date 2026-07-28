"""insight_reports 캐시 테이블 신설 (인사이트 개편 PR-C)

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
Create Date: 2026-07-28 00:00:00.000000

생성형 주간 인사이트 리포트를 (device_id, period_type, period_key) 단위로
캐시한다 — 같은 기간 재호출 시 LLM 비용이 다시 발생하지 않는다.
payload/model_meta JSONB에 통계 후보·선정·카드 스냅샷과 생성 메타를 저장해
PR-D 평가와 재현성 확인의 근거로 쓴다.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision: str = "b9c0d1e2f3a4"
down_revision: str | Sequence[str] | None = "a8b9c0d1e2f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "insight_reports",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("device_id", sa.String(64), nullable=False),
        sa.Column("period_type", sa.String(20), nullable=False),
        sa.Column("period_key", sa.String(20), nullable=False),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column("model_meta", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "device_id", "period_type", "period_key", name="uq_insight_reports_period"
        ),
    )
    op.create_index(
        "ix_insight_reports_device_created", "insight_reports", ["device_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_insight_reports_device_created", table_name="insight_reports")
    op.drop_table("insight_reports")
