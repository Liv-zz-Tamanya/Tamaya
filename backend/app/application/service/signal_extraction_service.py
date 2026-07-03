"""정성신호 추출 서비스 인터페이스 — 좁은 단일 메서드(extract_signal).

기존 AiChatService(일기 계약)를 오염시키지 않도록 코칭 정성신호 전용 인터페이스를
분리한다(슬라이스1 CoachingAiService와 동일한 원칙). 구현체는 infrastructure에 둔다.
"""

from abc import ABC, abstractmethod

from app.domain.model.chat_message import ChatMessage


class SignalExtractionService(ABC):
    @abstractmethod
    async def extract_signal(self, messages: list[ChatMessage]) -> dict | None:
        """대화 맥락에서 정성신호 1건을 추출한다.

        반환 형식: ``{"emotion": str, "behavior_mentions": [{"behavior": str, "polarity": int}]}``.
        추출할 신호가 없거나(예: mock 모드) 파싱 실패 시 ``None``(best-effort).
        """
        ...
