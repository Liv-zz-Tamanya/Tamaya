"""나의건강기록 수입 테이블 신설 (인사이트 개편 PR-A)

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-07-27 00:00:00.000000

신규 테이블:
  - sleep_records: 수면 측정(분). 측정일이 희소해 health_daily_summaries와 분리 —
    '기록 없는 날'과 '0분'을 구분한다. (device_id, record_date) UNIQUE로 재수입 멱등.
  - medical_visits: 진료이력 이벤트 행(같은 날 여러 기관 가능). 병명·진단 정보는
    수집하지 않는다. (device_id, visit_date, institution, visit_type) UNIQUE로 멱등.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision: str = "d6e7f8a9b0c1"
down_revision: str | Sequence[str] | None = "c5d6e7f8a9b0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sleep_records",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("device_id", sa.String(64), nullable=False),
        sa.Column("record_date", sa.Date(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column(
            "source", sa.String(20), nullable=False, server_default="myhealthrecord"
        ),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "device_id", "record_date", name="uq_sleep_records_device_record_date"
        ),
    )
    op.create_index("ix_sleep_records_device_id", "sleep_records", ["device_id"])
    op.create_index(
        "ix_sleep_records_device_record_date",
        "sleep_records",
        ["device_id", "record_date"],
    )

    op.create_table(
        "medical_visits",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("device_id", sa.String(64), nullable=False),
        sa.Column("visit_date", sa.Date(), nullable=False),
        sa.Column("visit_type", sa.String(20), nullable=False),
        sa.Column("institution", sa.String(100), nullable=False),
        sa.Column("location", sa.String(100), nullable=True),
        sa.Column("visit_days", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("prescription_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("medication_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "device_id", "visit_date", "institution", "visit_type",
            name="uq_medical_visits_dedupe",
        ),
    )
    op.create_index("ix_medical_visits_device_id", "medical_visits", ["device_id"])
    op.create_index(
        "ix_medical_visits_device_visit_date",
        "medical_visits",
        ["device_id", "visit_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_medical_visits_device_visit_date", table_name="medical_visits")
    op.drop_index("ix_medical_visits_device_id", table_name="medical_visits")
    op.drop_table("medical_visits")
    op.drop_index("ix_sleep_records_device_record_date", table_name="sleep_records")
    op.drop_index("ix_sleep_records_device_id", table_name="sleep_records")
    op.drop_table("sleep_records")
