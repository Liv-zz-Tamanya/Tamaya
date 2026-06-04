from datetime import date as date_type
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.model.character import Character
from app.domain.model.user import User

# ============================================================
# F1 — 인증
# ============================================================


class AnonymousAuthRequest(BaseModel):
    device_id: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: UUID
    kind: str
    name: str | None
    needs_onboarding: bool

    @classmethod
    def from_domain(cls, user: User) -> "UserResponse":
        return cls(id=user.id, kind=user.kind, name=user.name, needs_onboarding=user.needs_onboarding)


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: UserResponse
    onboarding_step: int = 0


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str


# ============================================================
# F1 — 온보딩 + 캐릭터
# ============================================================


class PrivacyConsentRequest(BaseModel):
    version: str = "v1"
    agreed_at: datetime | None = None


class PrivacyConsentResponse(BaseModel):
    ok: bool = True
    consent_id: UUID


class CharacterCreateRequest(BaseModel):
    name: str = Field(..., max_length=10)
    color: str
    personalities: list[str] = Field(default_factory=list)


class CharacterResponse(BaseModel):
    id: UUID
    name: str
    color: str
    personalities: list[str]
    level: int
    intimacy: int
    satiety: int
    vitality: int
    equipped_item: str | None

    @classmethod
    def from_domain(cls, c: Character) -> "CharacterResponse":
        return cls(
            id=c.id,
            name=c.name,
            color=c.color,
            personalities=c.personalities,
            level=c.level,
            intimacy=c.intimacy,
            satiety=c.satiety,
            vitality=c.vitality,
            equipped_item=c.equipped_item,
        )


class CharacterCreateResponse(BaseModel):
    character: CharacterResponse


class OnboardingCompleteResponse(BaseModel):
    ok: bool = True
    completed_at: datetime


# ============================================================
# F4 — 데일리 체크
# ============================================================


class DailyCheckBody(BaseModel):
    food: dict = Field(default_factory=lambda: {"done": False, "picks": []})
    water: int = 0
    sleep: dict = Field(default_factory=lambda: {"done": False, "quality": None})
    movement: dict = Field(default_factory=lambda: {"done": False, "bucket": None})
    sun: dict = Field(default_factory=lambda: {"done": False, "level": None})


class DailyCheckPutResponse(BaseModel):
    done_count: int
    max_count: int = 5
    points_awarded: int


class DailyCheckMonthResponse(BaseModel):
    days: dict[str, DailyCheckBody]


# ============================================================
# F5 — 일기 작성
# ============================================================


class DiarySessionStartRequest(BaseModel):
    mode: str = "chat"
    date: date_type


class QuestionResponse(BaseModel):
    text: str
    hint: str | None = None


class DiarySessionStartResponse(BaseModel):
    session_id: UUID
    day_memos: list[dict]
    first_question: QuestionResponse


class DiarySessionTurnRequest(BaseModel):
    turn: int = Field(..., ge=1, le=5)
    user_text: str = Field(..., min_length=1)


class DiarySessionTurnResponse(BaseModel):
    next_question: QuestionResponse | None = None
    is_final: bool
    auto_save: bool


class MoodSlice(BaseModel):
    label: str
    score: float
    color: str


class DiaryFinalizeResponse(BaseModel):
    mood_distribution: list[MoodSlice]
    primary_emoji: str
    keywords: list[str]
    diary_body: str
    tomorrow_one_thing: str
    actionable_chips: list[str]


class DiarySaveRequest(BaseModel):
    session_id: UUID | None = None
    date: date_type
    moods: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    body: str
    tomorrow: str = ""
    daily_check_snapshot: dict = Field(default_factory=dict)


class RewardResponse(BaseModel):
    points_delta: int
    streak_delta: int
    new_streak: int
    items_unlocked: list[str]
    level_up: bool
    item_drop: dict | None


class DiarySaveResponse(BaseModel):
    diary_id: UUID
    reward: RewardResponse


class DiaryEntryResponse(BaseModel):
    diary_id: UUID
    date: date_type
    moods: list[str]
    keywords: list[str]
    body: str
    tomorrow: str
    created_at: datetime
