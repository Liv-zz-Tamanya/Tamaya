"""B-009: embedding Vector(384) → Vector(1024) — NCP Embedding v2 대응

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-14 00:00:00.000000

배경:
- NCP Embedding v2 출력 차원 = 1024 (sentence-transformers PoC 384와 상이)
- pgvector ALTER COLUMN 미지원 → DROP + ADD 필수
- PoC 임베딩 데이터 소실 (실증 전 단계이므로 사용자 승인 조건 확인 후 실행)

⚠️  사용자 승인 필수 (DEC-022 Q1):
  to-BE.md에 한 줄 추가 후 실행:
  # DEC-022.B009: embedding DROP 승인 YYYY-MM-DD

실행:
  cd ~/dev/liv-zz-poc/backend && uv run alembic upgrade d4e5f6a7b8c9
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # NCP Embedding v2 키 수령 후에만 실제 dim 변경 실행.
    # 그 전엔 NoOp (사용자 승인 토큰 환경변수 확인).
    import os
    if os.getenv("DEC_022_B009_APPROVED") != "true":
        return  # NoOp: 384 유지, head까지 무사 통과
    # event_chunks: 384 → 1024
    conn = op.get_bind()
    if conn.execute(sa.text("SELECT to_regclass('event_chunks')")).scalar():
        op.drop_column("event_chunks", "embedding")
        op.add_column(
            "event_chunks",
            sa.Column("embedding", Vector(1024), nullable=False, server_default=sa.text("array_fill(0, ARRAY[1024])::vector")),
        )
    # health_chunks: 384 → 1024 (테이블 존재 시에만)
    if conn.execute(sa.text("SELECT to_regclass('health_chunks')")).scalar():
        op.drop_column("health_chunks", "embedding")
        op.add_column(
            "health_chunks",
            sa.Column("embedding", Vector(1024), nullable=False, server_default=sa.text("array_fill(0, ARRAY[1024])::vector")),
        )


def downgrade() -> None:
    op.drop_column("health_chunks", "embedding")
    op.add_column(
        "health_chunks",
        sa.Column("embedding", Vector(384), nullable=False, server_default=sa.text("array_fill(0, ARRAY[384])::vector")),
    )
    op.drop_column("event_chunks", "embedding")
    op.add_column(
        "event_chunks",
        sa.Column("embedding", Vector(384), nullable=False, server_default=sa.text("array_fill(0, ARRAY[384])::vector")),
    )
