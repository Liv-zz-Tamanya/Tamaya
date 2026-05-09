from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID, uuid4

from app.domain.model.emotion import Emotion


@dataclass
class Diary:
    id: UUID = field(default_factory=uuid4)
    diary_date: date = field(default_factory=date.today)
    title: str = ""
    content: str = ""
    emotion: Emotion = Emotion.CALM
    satisfaction: int = 3  # 1-5
    chat_session_id: UUID | None = None
    created_at: datetime = field(default_factory=datetime.now)
