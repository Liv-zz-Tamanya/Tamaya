import uuid
from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Boolean,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ChatSessionModel(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    is_finalized: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    messages: Mapped[list["ChatMessageModel"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="ChatMessageModel.created_at"
    )


class ChatMessageModel(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    session: Mapped["ChatSessionModel"] = relationship(back_populates="messages")


class DiaryModel(Base):
    __tablename__ = "diaries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    diary_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    emotion: Mapped[str] = mapped_column(String(20), nullable=False)
    satisfaction: Mapped[int] = mapped_column(Integer, nullable=False)
    chat_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class EventChunkModel(Base):
    __tablename__ = "event_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False
    )
    diary_date: Mapped[date] = mapped_column(Date, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    who: Mapped[str | None] = mapped_column(String(100), nullable=True)
    where: Mapped[str | None] = mapped_column(String(100), nullable=True)
    when: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class HealthDailySummaryModel(Base):
    __tablename__ = "health_daily_summaries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    step_count: Mapped[int] = mapped_column(Integer, default=0)
    step_goal: Mapped[int] = mapped_column(Integer, default=0)
    step_goal_achieved: Mapped[bool] = mapped_column(Boolean, default=False)
    step_calories: Mapped[float] = mapped_column(Float, default=0.0)
    step_distance_m: Mapped[float] = mapped_column(Float, default=0.0)
    has_exercise: Mapped[bool] = mapped_column(Boolean, default=False)
    exercise_duration_sec: Mapped[int] = mapped_column(Integer, default=0)
    exercise_distance_m: Mapped[float] = mapped_column(Float, default=0.0)
    exercise_calories: Mapped[float] = mapped_column(Float, default=0.0)
    heart_rate_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    heart_rate_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    heart_rate_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    floors_climbed: Mapped[int] = mapped_column(Integer, default=0)
    source_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class HealthChunkModel(Base):
    __tablename__ = "health_chunks"
    __table_args__ = (Index("ix_health_chunks_record_date", "record_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)
    data_types: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class HealthSessionModel(Base):
    __tablename__ = "health_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    messages: Mapped[list["HealthMessageModel"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="HealthMessageModel.created_at"
    )


class HealthMessageModel(Base):
    __tablename__ = "health_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("health_sessions.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    session: Mapped["HealthSessionModel"] = relationship(back_populates="messages")


# ============================================================
# F1·F4·F5 (P0) — 인증·온보딩·캐릭터 / 데일리체크 / 일기
# ============================================================


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="anonymous")
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    needs_onboarding: Mapped[bool] = mapped_column(Boolean, default=True)
    kakao_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class CharacterModel(Base):
    __tablename__ = "characters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(10), nullable=False)
    color: Mapped[str] = mapped_column(String(20), nullable=False)
    personalities: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    level: Mapped[int] = mapped_column(Integer, default=1)
    intimacy: Mapped[int] = mapped_column(Integer, default=0)
    satiety: Mapped[int] = mapped_column(Integer, default=50)
    vitality: Mapped[int] = mapped_column(Integer, default=50)
    equipped_item: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class ConsentModel(Base):
    __tablename__ = "consents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    agreed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class DailyCheckModel(Base):
    __tablename__ = "daily_checks"
    __table_args__ = (UniqueConstraint("user_id", "check_date", name="uq_daily_check_user_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    check_date: Mapped[date] = mapped_column(Date, nullable=False)
    food: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    water: Mapped[int] = mapped_column(Integer, default=0)
    sleep: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    movement: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    sun: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class DiarySessionModel(Base):
    __tablename__ = "diary_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    mode: Mapped[str] = mapped_column(String(20), default="chat")
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    turns: Mapped[list["DiaryTurnModel"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="DiaryTurnModel.created_at"
    )


class DiaryTurnModel(Base):
    __tablename__ = "diary_turns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("diary_sessions.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    turn: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    session: Mapped["DiarySessionModel"] = relationship(back_populates="turns")


class DiaryEntryModel(Base):
    __tablename__ = "diary_entries"
    __table_args__ = (UniqueConstraint("user_id", "entry_date", name="uq_diary_entry_user_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    moods: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    keywords: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    tomorrow: Mapped[str] = mapped_column(Text, nullable=False, default="")
    daily_check_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    points: Mapped[int] = mapped_column(Integer, default=0)
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("diary_sessions.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
