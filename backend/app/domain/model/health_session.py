from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from app.domain.model.health_message import HealthMessage


@dataclass
class HealthSession:
    device_id: str
    messages: list[HealthMessage] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if not self.device_id or not self.device_id.strip():
            raise ValueError("device_id는 필수입니다.")
        if len(self.device_id) > 64:
            raise ValueError("device_id는 64자를 초과할 수 없습니다.")

    def add_message(self, role: str, content: str) -> HealthMessage:
        message = HealthMessage(role=role, content=content, created_at=datetime.now())
        self.messages.append(message)
        return message
