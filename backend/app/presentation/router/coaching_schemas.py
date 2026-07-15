"""코칭 라우터 DTO — role enum 강제 + 페이로드 상한(토큰 남용 방지)."""

from typing import Literal

from pydantic import BaseModel, Field


class CoachingHistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class CoachingMessageRequest(BaseModel):
    message: str = Field(max_length=2000)
    persona: str | None = Field(default=None, max_length=200)
    history: list[CoachingHistoryItem] = Field(default_factory=list, max_length=50)


class CoachingMessageResponse(BaseModel):
    reply: str
