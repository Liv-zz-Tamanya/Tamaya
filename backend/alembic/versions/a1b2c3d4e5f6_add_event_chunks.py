"""add event_chunks table with pgvector

Revision ID: a1b2c3d4e5f6
Revises: 5b81494e6cf8
Create Date: 2026-03-14 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import ARRAY

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "5b81494e6cf8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "event_chunks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("chat_session_id", sa.UUID(), nullable=False),
        sa.Column("diary_date", sa.Date(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column("tags", ARRAY(sa.String()), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["chat_session_id"], ["chat_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_event_chunks_diary_date",
        "event_chunks",
        ["diary_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_event_chunks_diary_date", table_name="event_chunks")
    op.drop_table("event_chunks")
