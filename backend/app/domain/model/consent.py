from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class Consent:
    user_id: UUID
    version: str
    id: UUID = field(default_factory=uuid4)
    agreed_at: datetime = field(default_factory=datetime.now)
