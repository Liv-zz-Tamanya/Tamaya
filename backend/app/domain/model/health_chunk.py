from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID, uuid4


@dataclass
class HealthChunk:
    record_date: date
    text: str
    embedding: list[float]
    data_types: list[str]
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.now)
