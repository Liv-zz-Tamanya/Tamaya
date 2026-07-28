"""3턴 회고 모드 폐지 — 기존 3턴 세션을 5턴으로 이관

3턴 모드가 제품에서 제거되면서 ChatSession 도메인 모델이 max_turns=3을
거부한다. 남아 있는 3턴 row가 조회 시 도메인 검증에서 터지지 않도록
가장 가까운 정책(5턴)으로 올린다.

Revision ID: a8b9c0d1e2f3
Revises: e7f8a9b0c1d2
Create Date: 2026-07-28 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op


revision: str = "a8b9c0d1e2f3"
down_revision: str | Sequence[str] | None = "e7f8a9b0c1d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE chat_sessions SET max_turns = 5 WHERE max_turns = 3")


def downgrade() -> None:
    # 어떤 row가 3턴이었는지 복원할 수 없음 — 정책 폐지라 의도적으로 비가역.
    pass
