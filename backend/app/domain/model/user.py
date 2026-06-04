from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class User:
    id: UUID = field(default_factory=uuid4)
    kind: str = "anonymous"  # "anonymous" | "kakao"
    name: str | None = None
    needs_onboarding: bool = True
    kakao_id: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
