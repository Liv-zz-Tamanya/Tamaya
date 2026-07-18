"""닉네임 사용자별 밤 채팅 설정 API."""

from datetime import datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.config.database import get_db
from app.infrastructure.persistence.models import UserModel, UserPreferenceModel
from app.presentation.auth_deps import get_current_nickname_user

DEFAULT_OPEN_TIME = time(19, 0)
DEFAULT_TIMEZONE = "Asia/Seoul"
MIN_OPEN_TIME = time(18, 0)

router = APIRouter(prefix="/api/v1/me/preferences", tags=["preferences"])


def _format_time(value: time) -> str:
    return value.strftime("%H:%M")


class NightChatPreferenceResponse(BaseModel):
    open_time: str
    timezone: str

    @classmethod
    def from_values(cls, open_time: time, timezone: str) -> "NightChatPreferenceResponse":
        return cls(open_time=_format_time(open_time), timezone=timezone)


class NightChatPreferenceUpdate(BaseModel):
    open_time: str
    timezone: str

    @field_validator("open_time")
    @classmethod
    def validate_open_time(cls, value: str) -> str:
        try:
            parsed = datetime.strptime(value, "%H:%M").time()
        except ValueError as exc:
            raise ValueError("open_time은 HH:mm 형식이어야 합니다.") from exc
        if parsed < MIN_OPEN_TIME:
            raise ValueError("밤 채팅 시작 시간은 18:00~23:59 사이여야 합니다.")
        return value

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("유효한 IANA timezone이어야 합니다.") from exc
        return value

    @property
    def parsed_open_time(self) -> time:
        return datetime.strptime(self.open_time, "%H:%M").time()


@router.get("/night-chat", response_model=NightChatPreferenceResponse)
async def get_night_chat_preference(
    user: UserModel = Depends(get_current_nickname_user),
    db: AsyncSession = Depends(get_db),
) -> NightChatPreferenceResponse:
    preference = await db.scalar(
        select(UserPreferenceModel).where(UserPreferenceModel.user_id == user.id)
    )
    if preference is None:
        return NightChatPreferenceResponse.from_values(DEFAULT_OPEN_TIME, DEFAULT_TIMEZONE)
    return NightChatPreferenceResponse.from_values(
        preference.night_chat_open_time, preference.timezone
    )


@router.put("/night-chat", response_model=NightChatPreferenceResponse)
async def update_night_chat_preference(
    body: NightChatPreferenceUpdate,
    user: UserModel = Depends(get_current_nickname_user),
    db: AsyncSession = Depends(get_db),
) -> NightChatPreferenceResponse:
    stmt = insert(UserPreferenceModel).values(
        user_id=user.id,
        night_chat_open_time=body.parsed_open_time,
        timezone=body.timezone,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[UserPreferenceModel.user_id],
        set_={
            "night_chat_open_time": body.parsed_open_time,
            "timezone": body.timezone,
            "updated_at": datetime.now(),
        },
    )
    try:
        await db.execute(stmt)
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "밤 채팅 설정을 저장하지 못했습니다."
        )
    return NightChatPreferenceResponse.from_values(body.parsed_open_time, body.timezone)
