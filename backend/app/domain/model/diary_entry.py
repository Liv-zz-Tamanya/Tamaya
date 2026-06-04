from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID, uuid4


@dataclass
class DiaryEntry:
    """명세 F5 — 저장된 일기 (POST /v1/diary). 유저 스코프."""

    user_id: UUID
    entry_date: date
    body: str = ""
    moods: list[str] = field(default_factory=list)  # emoji[]
    keywords: list[str] = field(default_factory=list)
    tomorrow: str = ""
    daily_check_snapshot: dict = field(default_factory=dict)
    points: int = 0
    session_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.now)
