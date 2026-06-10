import uuid
from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class EventChunk:
    id: uuid.UUID
    chat_session_id: uuid.UUID
    diary_date: date
    text: str
    embedding: list[float]
    tags: list[str]
    event_type: str
    who: str | None = None  # 대화에 등장한 인물
    where: str | None = None  # 대화에 등장한 장소
    when: str | None = None  # 대화에 등장한 시간/날짜 표현
    created_at: datetime = field(default_factory=datetime.now)
