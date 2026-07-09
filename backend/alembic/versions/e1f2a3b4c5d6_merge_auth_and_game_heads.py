"""PR12/PR13 alembic head 병합

Revision ID: e1f2a3b4c5d6
Revises: c9d0e1f2a3b4, d0e1f2a3b4c5
Create Date: 2026-07-09 00:00:00.000000

두 기능 브랜치가 같은 down_revision(b8c9d0e1f2a3)에서 갈라져
head가 둘로 나뉜 상태를 하나로 합친다.
"""

from collections.abc import Sequence

revision: str = "e1f2a3b4c5d6"
down_revision: str | Sequence[str] | None = ("c9d0e1f2a3b4", "d0e1f2a3b4c5")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
