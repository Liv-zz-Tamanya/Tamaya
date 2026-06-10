"""CoachingSession — 코칭 대화 어그리거트.

diary용 ChatSession과 분리된 격리 도메인. device_id로 키잉하며(별도 User 테이블 없음),
대화 메시지와 동적 루틴 제안을 담는다. 코칭은 일기 정리를 강제하지 않으므로
finalize/should_suggest_finalize 같은 diary 불변식을 두지 않는다.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID, uuid4

from app.domain.model.chat_message import ChatMessage
from app.domain.model.routine import RoutineKind, RoutineSuggestion


@dataclass
class CoachingSession:
    device_id: str
    id: UUID = field(default_factory=uuid4)
    session_date: date = field(default_factory=date.today)
    messages: list[ChatMessage] = field(default_factory=list)
    routine_suggestions: list[RoutineSuggestion] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def add_message(self, role: str, content: str) -> ChatMessage:
        message = ChatMessage(role=role, content=content, created_at=datetime.now())
        self.messages.append(message)
        return message

    def add_routine_suggestion(self, kind: RoutineKind, nudge_text: str) -> RoutineSuggestion:
        suggestion = RoutineSuggestion(kind=kind, nudge_text=nudge_text)
        self.routine_suggestions.append(suggestion)
        return suggestion
