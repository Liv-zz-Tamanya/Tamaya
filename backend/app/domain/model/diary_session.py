from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID, uuid4


@dataclass
class DiaryTurn:
    role: str  # "user" | "bot"
    content: str
    turn: int  # 1..5 (user 기준). bot 질문은 직전 turn 번호 공유
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class DiarySession:
    """명세 F5 — 5턴 ChatDiary 세션."""

    user_id: UUID
    session_date: date
    mode: str = "chat"  # "chat" | "short" | "voice"
    status: str = "active"  # "active" | "finalized" | "saved"
    turns: list[DiaryTurn] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.now)

    def add_turn(self, role: str, content: str, turn: int) -> None:
        self.turns.append(DiaryTurn(role=role, content=content, turn=turn))

    @property
    def user_turn_count(self) -> int:
        return sum(1 for t in self.turns if t.role == "user")
