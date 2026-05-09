from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID, uuid4

from app.domain.model.chat_message import ChatMessage


@dataclass
class ChatSession:
    id: UUID = field(default_factory=uuid4)
    session_date: date = field(default_factory=date.today)
    messages: list[ChatMessage] = field(default_factory=list)
    is_finalized: bool = False
    created_at: datetime = field(default_factory=datetime.now)

    def add_message(self, role: str, content: str) -> ChatMessage:
        message = ChatMessage(role=role, content=content, created_at=datetime.now())
        self.messages.append(message)
        return message

    def finalize(self) -> None:
        if self.is_finalized:
            raise ValueError("이미 일기가 작성된 세션입니다.")
        if not self._has_enough_messages():
            raise ValueError("일기를 작성하기에 대화가 충분하지 않습니다. 조금 더 대화해 주세요.")
        self.is_finalized = True

    def _has_enough_messages(self) -> bool:
        user_messages = [m for m in self.messages if m.role == "user"]
        return len(user_messages) >= 2

    @property
    def user_message_count(self) -> int:
        return len([m for m in self.messages if m.role == "user"])

    @property
    def should_suggest_finalize(self) -> bool:
        return self.user_message_count >= 5 and not self.is_finalized
