from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID, uuid4


@dataclass
class HealthDailySummary:
    record_date: date
    step_count: int
    step_goal: int
    step_goal_achieved: bool
    step_calories: float
    step_distance_m: float
    has_exercise: bool
    exercise_duration_sec: int
    exercise_distance_m: float
    exercise_calories: float
    heart_rate_avg: float | None
    heart_rate_min: float | None
    heart_rate_max: float | None
    floors_climbed: int
    source_hash: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.now)
