from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.model.chat_message import ChatMessage
from app.domain.model.chat_session import ChatSession
from app.domain.model.diary import Diary


class ChatMessageResponse(BaseModel):
    role: str
    content: str
    created_at: datetime

    @classmethod
    def from_domain(cls, msg: ChatMessage) -> "ChatMessageResponse":
        return cls(role=msg.role, content=msg.content, created_at=msg.created_at)


class ChatSessionResponse(BaseModel):
    id: UUID
    session_date: date
    messages: list[ChatMessageResponse]
    max_turns: int
    is_finalized: bool
    user_message_count: int
    should_suggest_finalize: bool
    created_at: datetime

    @classmethod
    def from_domain(cls, session: ChatSession) -> "ChatSessionResponse":
        return cls(
            id=session.id,
            session_date=session.session_date,
            messages=[ChatMessageResponse.from_domain(m) for m in session.messages],
            max_turns=session.max_turns,
            is_finalized=session.is_finalized,
            user_message_count=session.user_message_count,
            should_suggest_finalize=session.should_suggest_finalize,
            created_at=session.created_at,
        )


class StartChatSessionRequest(BaseModel):
    max_turns: Literal[3, 5] = Field(default=ChatSession.DEFAULT_MAX_TURNS)
    reset: bool = False


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class SendMessageResponse(BaseModel):
    user_message: ChatMessageResponse
    ai_message: ChatMessageResponse
    should_suggest_finalize: bool
    diary: "DiaryResponse | None" = None


class DiaryResponse(BaseModel):
    id: UUID
    diary_date: date
    title: str
    content: str
    emotion: str
    satisfaction: int
    chat_session_id: UUID | None
    created_at: datetime

    @classmethod
    def from_domain(cls, diary: Diary) -> "DiaryResponse":
        return cls(
            id=diary.id,
            diary_date=diary.diary_date,
            title=diary.title,
            content=diary.content,
            emotion=diary.emotion.value,
            satisfaction=diary.satisfaction,
            chat_session_id=diary.chat_session_id,
            created_at=diary.created_at,
        )


class DiaryListResponse(BaseModel):
    items: list[DiaryResponse]
    total: int
