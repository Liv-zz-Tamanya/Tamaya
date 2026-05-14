from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class HealthMessage:
    role: str
    content: str
    created_at: datetime
