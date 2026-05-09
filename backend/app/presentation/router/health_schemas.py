from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.model.health_message import HealthMessage
from app.domain.model.health_session import HealthSession


class HealthMessageResponse(BaseModel):
    role: str
    content: str
    created_at: datetime

    @classmethod
    def from_domain(cls, msg: HealthMessage) -> "HealthMessageResponse":
        return cls(role=msg.role, content=msg.content, created_at=msg.created_at)


class HealthSessionResponse(BaseModel):
    id: UUID
    messages: list[HealthMessageResponse]
    created_at: datetime

    @classmethod
    def from_domain(cls, session: HealthSession) -> "HealthSessionResponse":
        return cls(
            id=session.id,
            messages=[HealthMessageResponse.from_domain(m) for m in session.messages],
            created_at=session.created_at,
        )


class SendHealthMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class SendHealthMessageResponse(BaseModel):
    user_message: HealthMessageResponse
    ai_message: HealthMessageResponse
