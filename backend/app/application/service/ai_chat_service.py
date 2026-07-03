from abc import ABC, abstractmethod

from app.domain.model.chat_message import ChatMessage


class AiChatService(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        suggest_finalize: bool = False,
        memories: list[str] | None = None,
    ) -> str: ...

    @abstractmethod
    async def generate_diary(self, messages: list[ChatMessage]) -> dict: ...

    @abstractmethod
    async def detect_finalize_intent(self, user_message: str) -> bool: ...

    @abstractmethod
    async def generate_closing_message(self, messages: list[ChatMessage]) -> str: ...

    @abstractmethod
    async def classify_memory_need(self, user_message: str) -> bool: ...

    @abstractmethod
    async def extract_event_chunks(self, messages: list[ChatMessage]) -> list[dict]: ...
