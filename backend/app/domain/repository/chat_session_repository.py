from abc import ABC, abstractmethod
from datetime import date
from uuid import UUID

from app.domain.model.chat_session import ChatSession


class ChatSessionRepository(ABC):
    @abstractmethod
    async def save(self, session: ChatSession) -> ChatSession: ...

    @abstractmethod
    async def find_by_id(self, session_id: UUID) -> ChatSession | None: ...

    @abstractmethod
    async def find_by_date(self, session_date: date) -> ChatSession | None: ...
