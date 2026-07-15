from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID, uuid4


@dataclass
class HealthChunk:
    device_id: str
    record_date: date
    text: str
    embedding: list[float]
    data_types: list[str]
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if not self.device_id or not self.device_id.strip():
            raise ValueError("device_id는 필수입니다.")
        if len(self.device_id) > 64:
            raise ValueError("device_id는 64자를 초과할 수 없습니다.")
