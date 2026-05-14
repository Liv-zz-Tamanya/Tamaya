from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from app.domain.model.health_message import HealthMessage


@dataclass
class HealthSession:
    messages: list[HealthMessage] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.now)

    def add_message(self, role: str, content: str) -> HealthMessage:
        message = HealthMessage(role=role, content=content, created_at=datetime.now())
        self.messages.append(message)
        return message
