"""정성신호 추출 usecase — best-effort 오케스트레이션 (G002-2).

코칭 턴 이후 호출되어 CLOVA로 정성신호를 추출하고 QualitativeSignal로 영속한다.
finalize_diary의 best-effort 패턴을 따라, 추출/저장 실패가 코칭 대화를 깨지 않도록
모든 예외를 흡수하고 로깅만 한다.
"""

import logging
from uuid import UUID

from app.application.service.signal_extraction_service import SignalExtractionService
from app.domain.model.chat_message import ChatMessage
from app.domain.model.emotion import Emotion
from app.domain.model.qualitative_signal import BehaviorMention, QualitativeSignal
from app.domain.repository.qualitative_signal_repository import QualitativeSignalRepository

logger = logging.getLogger(__name__)


class ExtractSignalsUseCase:
    def __init__(
        self,
        service: SignalExtractionService,
        repo: QualitativeSignalRepository,
    ) -> None:
        self._service = service
        self._repo = repo

    async def execute(
        self,
        device_id: str,
        session_id: UUID,
        messages: list[ChatMessage],
    ) -> None:
        try:
            data = await self._service.extract_signal(messages)
            if not data:
                return

            signal = self._to_signal(data)
            if signal is None:
                return

            await self._repo.save(device_id, session_id, signal)
        except Exception as exc:  # best-effort: 대화 흐름을 깨지 않음
            logger.warning("signal extraction skipped (best-effort): %s", exc)

    @staticmethod
    def _to_signal(data: dict) -> QualitativeSignal | None:
        try:
            emotion = Emotion(data["emotion"])
        except (KeyError, ValueError):
            return None  # 잘못된/누락된 emotion → 신호 폐기

        mentions = tuple(
            BehaviorMention(behavior=m["behavior"], polarity=int(m["polarity"]))
            for m in data.get("behavior_mentions", [])
            if isinstance(m, dict) and "behavior" in m and "polarity" in m
        )
        return QualitativeSignal(emotion=emotion, behavior_mentions=mentions)
