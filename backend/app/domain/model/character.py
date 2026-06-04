from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

# 명세 F1.3 — 캐릭터 생성 옵션
CHARACTER_COLORS = ["#f5e6cf", "#d8a777", "#a66838", "#6b3e1f", "#3a2414"]
CHARACTER_PERSONALITIES = ["차분한", "수다쟁이", "시크", "다정한", "장난꾸러기"]


@dataclass
class Character:
    user_id: UUID
    name: str
    color: str
    personalities: list[str] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)
    level: int = 1
    intimacy: int = 0
    satiety: int = 50
    vitality: int = 50
    equipped_item: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
