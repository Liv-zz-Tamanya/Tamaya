"""add who/where/when to event_chunks

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-14 00:00:00.000001

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("event_chunks", sa.Column("who", sa.String(length=100), nullable=True))
    op.add_column("event_chunks", sa.Column("where", sa.String(length=100), nullable=True))
    op.add_column("event_chunks", sa.Column("when", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("event_chunks", "when")
    op.drop_column("event_chunks", "where")
    op.drop_column("event_chunks", "who")
