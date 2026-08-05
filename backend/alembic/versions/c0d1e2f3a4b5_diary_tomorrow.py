"""diaries.tomorrow 컬럼 추가

Revision ID: c0d1e2f3a4b5
Revises: b9c0d1e2f3a4
Create Date: 2026-08-06 00:00:00.000000

일기 생성 시 대화에서 언급된 '내일 한 가지'를 저장한다. FE가 마지막 사용자
답변을 그대로 쓰던 휴리스틱(고정 5턴 스크립트 유산)을 대체하는 필드.
언급이 없으면 NULL — LLM이 지어내지 않는다는 프롬프트 규칙과 정합.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c0d1e2f3a4b5"
down_revision: str | Sequence[str] | None = "b9c0d1e2f3a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("diaries", sa.Column("tomorrow", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("diaries", "tomorrow")
