"""코칭 AI 서비스 인터페이스 — 좁은 단일 메서드(coach).

기존 AiChatService(추상 6종)를 오염시키지 않도록 코칭 전용 인터페이스를 분리한다.
구현체(CLOVA mock/real)는 별도 슬라이스에서 제공한다.
"""

from abc import ABC, abstractmethod

from app.domain.model.chat_message import ChatMessage


class CoachingAiService(ABC):
    @abstractmethod
    async def coach(self, messages: list[ChatMessage], persona: str | None = None) -> str:
        """대화 맥락 기반 코칭 응답을 생성한다. persona는 비서 톤(예: 부모님)."""
        ...
