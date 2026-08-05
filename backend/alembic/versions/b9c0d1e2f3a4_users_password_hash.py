"""users에 password_hash 추가 + 레거시 무비밀번호 계정 리셋

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
Create Date: 2026-08-05 00:00:00.000000

닉네임 단독 → 닉네임+비밀번호 인증 전환(데모 단계 결정: 레거시 계정은 리셋).
기존 users 행은 비밀번호가 없어 NOT NULL 컬럼과 공존할 수 없으므로 전부 삭제한다.
user_preferences는 FK ondelete CASCADE로 함께 정리된다.
일기·게임 등 앱 데이터는 device_id(= "nick-{nickname}") 키잉이라 삭제되지 않으며,
같은 닉네임으로 재가입하면 기존 데이터에 다시 연결된다.

실행:
  cd backend
  uv run alembic upgrade head
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b9c0d1e2f3a4"
down_revision: str | Sequence[str] | None = "a8b9c0d1e2f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DELETE FROM users")
    op.add_column("users", sa.Column("password_hash", sa.String(128), nullable=False))


def downgrade() -> None:
    op.drop_column("users", "password_hash")
