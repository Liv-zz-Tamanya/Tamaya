"""코칭 메시지 usecase — guardrail-first 합성 + best-effort 정성신호 추출 (G004-1).

stateless: 클라이언트가 보낸 history에 현재 사용자 메시지를 덧붙여 CoachingAgent로 흘려보낸다.
coach는 전체 맥락(history+현재)을 보고, guardrail은 현재 메시지로 판정한다.
대화 종료 후 정성신호 추출은 best-effort(실패해도 대화 흐름 보호).
"""

import logging
from datetime import datetime
from uuid import UUID, uuid4

from app.application.usecase.coaching_agent import CoachingAgent
from app.application.usecase.extract_signals import ExtractSignalsUseCase
from app.domain.model.chat_message import ChatMessage

logger = logging.getLogger(__name__)


class SendCoachingMessageUseCase:
    def __init__(
        self,
        agent: CoachingAgent,
        extract_signals: ExtractSignalsUseCase | None = None,
    ) -> None:
        self._agent = agent
        self._extract_signals = extract_signals

    async def execute(
        self,
        device_id: str | None,
        message: str,
        history: list[ChatMessage],
        session_id: UUID | None = None,
        persona: str | None = None,
    ) -> str:
        sid = session_id or uuid4()
        full_messages = [
            *history,
            ChatMessage(role="user", content=message, created_at=datetime.now()),
        ]

        reply = await self._agent.run(sid, full_messages, message, persona)

        # best-effort: 대화 한 턴이 끝나면 정성신호를 추출(실패해도 무시).
        if self._extract_signals is not None and device_id:
            convo = [
                *full_messages,
                ChatMessage(role="assistant", content=reply, created_at=datetime.now()),
            ]
            try:
                await self._extract_signals.execute(
                    device_id=device_id, session_id=sid, messages=convo
                )
            except (
                Exception
            ) as exc:  # best-effort — 예외 메시지에 대화 내용이 섞일 수 있어 타입만 로깅
                logger.warning(
                    "coaching signal extraction skipped (best-effort): %s", type(exc).__name__
                )

        return reply
