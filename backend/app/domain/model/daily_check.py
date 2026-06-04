from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID, uuid4

MAX_COUNT = 5


@dataclass
class DailyCheck:
    """명세 F4 — 데일리 체크. 각 항목은 명세 PUT body shape 그대로 JSON으로 저장."""

    user_id: UUID
    check_date: date
    food: dict = field(default_factory=lambda: {"done": False, "picks": []})
    water: int = 0  # 0..8
    sleep: dict = field(default_factory=lambda: {"done": False, "quality": None})
    movement: dict = field(default_factory=lambda: {"done": False, "bucket": None})
    sun: dict = field(default_factory=lambda: {"done": False, "level": None})
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @property
    def done_count(self) -> int:
        count = 0
        if self.food.get("done"):
            count += 1
        if self.water and self.water > 0:
            count += 1
        if self.sleep.get("done"):
            count += 1
        if self.movement.get("done"):
            count += 1
        if self.sun.get("done"):
            count += 1
        return count
