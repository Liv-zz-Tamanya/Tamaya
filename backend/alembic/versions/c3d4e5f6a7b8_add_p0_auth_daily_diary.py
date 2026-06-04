"""add P0 tables: users, characters, consents, daily_checks, diary_sessions/turns/entries

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-04 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("kind", sa.String(length=20), nullable=False, server_default="anonymous"),
        sa.Column("name", sa.String(length=50), nullable=True),
        sa.Column("needs_onboarding", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("kakao_id", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("kakao_id", name="uq_users_kakao_id"),
    )

    op.create_table(
        "characters",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(length=10), nullable=False),
        sa.Column("color", sa.String(length=20), nullable=False),
        sa.Column("personalities", ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("intimacy", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("satiety", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("vitality", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("equipped_item", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", name="uq_characters_user_id"),
    )

    op.create_table(
        "consents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("version", sa.String(length=20), nullable=False),
        sa.Column("agreed_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "daily_checks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("check_date", sa.Date(), nullable=False),
        sa.Column("food", JSONB(), nullable=False, server_default="{}"),
        sa.Column("water", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sleep", JSONB(), nullable=False, server_default="{}"),
        sa.Column("movement", JSONB(), nullable=False, server_default="{}"),
        sa.Column("sun", JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "check_date", name="uq_daily_check_user_date"),
    )

    op.create_table(
        "diary_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False, server_default="chat"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "diary_turns",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("diary_sessions.id"), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("turn", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "diary_entries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("moods", ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("keywords", ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("tomorrow", sa.Text(), nullable=False, server_default=""),
        sa.Column("daily_check_snapshot", JSONB(), nullable=False, server_default="{}"),
        sa.Column("points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("diary_sessions.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "entry_date", name="uq_diary_entry_user_date"),
    )


def downgrade() -> None:
    op.drop_table("diary_entries")
    op.drop_table("diary_turns")
    op.drop_table("diary_sessions")
    op.drop_table("daily_checks")
    op.drop_table("consents")
    op.drop_table("characters")
    op.drop_table("users")
