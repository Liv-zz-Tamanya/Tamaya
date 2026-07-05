from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID, uuid4

from app.domain.model.emotion import Emotion


@dataclass
class Diary:
    id: UUID = field(default_factory=uuid4)
    device_id: str | None = None  # 일기 소유자 (익명 device 인증 identity)
    diary_date: date = field(default_factory=date.today)
    title: str = ""
    content: str = ""
    emotion: Emotion = Emotion.CALM
    satisfaction: int = 50  # BUG-07: 0-100 (DEC-020)
    chat_session_id: UUID | None = None
    created_at: datetime = field(default_factory=datetime.now)
