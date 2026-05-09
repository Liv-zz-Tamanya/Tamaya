from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ChatMessage:
    role: str  # "user", "assistant", "system"
    content: str
    created_at: datetime
