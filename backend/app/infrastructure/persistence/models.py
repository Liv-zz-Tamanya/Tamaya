import uuid
from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ChatSessionModel(Base):
    __tablename__ = "chat_sessions"
    # B-005: device_id + session_date 복합 UNIQUE (alembic c3d4e5f6a7b8)
    __table_args__ = (
        UniqueConstraint("device_id", "session_date", name="uq_chat_sessions_device_session_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_finalized: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    messages: Mapped[list["ChatMessageModel"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessageModel.created_at",
    )


class ChatMessageModel(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    session: Mapped["ChatSessionModel"] = relationship(back_populates="messages")


class DiaryModel(Base):
    __tablename__ = "diaries"
    # B-008: device_id + diary_date 복합 UNIQUE (alembic c3d4e5f6a7b8)
    __table_args__ = (
        UniqueConstraint("device_id", "diary_date", name="uq_diaries_device_diary_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    diary_date: Mapped[date] = mapped_column(Date, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    emotion: Mapped[str] = mapped_column(String(20), nullable=False)
    # BUG-07: satisfaction 0-100 (DEC-020)
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


class UserSessionModel(Base):
    """
    DEC-023: 동시접속 strict 1세션 — JWT jti 블랙리스트 + 세션 상태.
    신규 로그인 시 기존 레코드 revoked_at = now(), 새 레코드 insert.
    보호 라우트 요청마다 jti 조회 → revoked_at IS NOT NULL → 401.
    """

    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # device_id (익명) 또는 kakao_id (OAuth 사용자) 중 하나
    device_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    kakao_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    jti: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None


class UserModel(Base):
    """닉네임 기반 데모 계정 — 닉네임 UNIQUE로 회원가입/로그인을 식별한다.
    비밀번호 없는 데모용. 앱 데이터는 여전히 device_id(= f"nick-{nickname}")로 키잉된다."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nickname: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class HealthSessionModel(Base):
    __tablename__ = "health_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    messages: Mapped[list["HealthMessageModel"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="HealthMessageModel.created_at",
    )


class HealthMessageModel(Base):
    __tablename__ = "health_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("health_sessions.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    session: Mapped["HealthSessionModel"] = relationship(back_populates="messages")


# ─── 정성신호 도메인 (G002 Backend-Insight) ────────────────────────────────────


class QualitativeSignalModel(Base):
    """코칭 대화에서 추출한 정성신호 — device_id 키잉(User 테이블 없음).

    session_id는 coaching_sessions 테이블 부재로 FK 없이 단순 UUID로 둔다.
    behavior_mentions는 [{"behavior": str, "polarity": int}] 형태의 JSONB.
    (device_id, recorded_date) 복합 인덱스로 주/월 기간 집계를 가속한다.
    """

    __tablename__ = "qualitative_signals"
    __table_args__ = (Index("ix_qualitative_signals_device_date", "device_id", "recorded_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[str] = mapped_column(String(64), nullable=False)
    session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    emotion: Mapped[str] = mapped_column(String(20), nullable=False)
    behavior_mentions: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)
    recorded_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class ClovaSettingModel(Base):
    """BYOK CLOVA 설정 — device_id별 마스킹 키 프리뷰. 원문 키는 저장하지 않는다."""

    __tablename__ = "clova_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # unique=True가 암묵적 인덱스를 만들므로 index=True는 중복(autogenerate drift 방지).
    device_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    masked_key: Mapped[str] = mapped_column(String(64), nullable=False)
    has_key: Mapped[bool] = mapped_column(Boolean, default=False)
    # onupdate로 키 재저장 시 갱신 시각을 반영한다(upsert 업데이트 경로 정합).
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )


# ─── 키우기 게임 도메인 (DEC-019, DEC-022.B) ───────────────────────────────────


class GameProgressModel(Base):
    """
    device_id 1개당 1레코드.
    level = (total_diaries // 10) + 1
    affinity = 0~100 (일기 1건당 +2, DEC-020 BUG-07 정합)
    """

    __tablename__ = "game_progress"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    total_diaries: Mapped[int] = mapped_column(Integer, default=0)
    points: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=1)
    affinity: Mapped[int] = mapped_column(Integer, default=0)  # 0–100
    last_diary_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class RewardInventoryModel(Base):
    """
    reward_id: FE rewardSystem.ts REWARDS[].id ('churu_1', 'toy_ball', …)
    device_id + reward_id 복합 UNIQUE — 보상 중복 지급 방지
    """

    __tablename__ = "reward_inventory"
    __table_args__ = (UniqueConstraint("device_id", "reward_id", name="uq_device_reward"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reward_id: Mapped[str] = mapped_column(String(50), nullable=False)
    reward_type: Mapped[str] = mapped_column(String(20), nullable=False)
    claimed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
