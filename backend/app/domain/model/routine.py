"""루틴 제안 — 코칭 대화에서 동적으로 emit되는 제안 기록 (고정 체크리스트 아님)."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4


class RoutineKind(StrEnum):
    SLEEP = "sleep"
    MEAL = "meal"
    EXERCISE = "exercise"
    MEDICATION = "medication"


@dataclass(frozen=True)
class RoutineSuggestion:
    kind: RoutineKind
    nudge_text: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.now)
