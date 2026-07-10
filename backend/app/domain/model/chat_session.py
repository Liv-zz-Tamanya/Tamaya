from dataclasses import dataclass, field
from datetime import date, datetime
from typing import ClassVar
from uuid import UUID, uuid4

from app.domain.model.chat_message import ChatMessage


@dataclass
class ChatSession:
    # 회고 대화는 3턴/5턴 두 정책만 허용한다.
    DEFAULT_MAX_TURNS: ClassVar[int] = 5
    SHORT_MAX_TURNS: ClassVar[int] = 3
    ALLOWED_MAX_TURNS: ClassVar[tuple[int, int]] = (SHORT_MAX_TURNS, DEFAULT_MAX_TURNS)

    id: UUID = field(default_factory=uuid4)
    device_id: str | None = None  # 세션 소유자 (익명 device 인증 identity)
    session_date: date = field(default_factory=date.today)
    messages: list[ChatMessage] = field(default_factory=list)
    max_turns: int = DEFAULT_MAX_TURNS
    is_finalized: bool = False
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if self.max_turns not in self.ALLOWED_MAX_TURNS:
            raise ValueError("지원하지 않는 회고 턴 수입니다.")

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
        # 마지막 턴 직전부터 마무리를 향해 대화를 좁혀간다.
        return self.user_message_count >= self.max_turns - 1 and not self.is_finalized

    @property
    def must_finalize(self) -> bool:
        # 설정된 턴 수에 도달하면 사용자 의도와 무관하게 무조건 일기로 마무리한다.
        return self.user_message_count >= self.max_turns and not self.is_finalized
