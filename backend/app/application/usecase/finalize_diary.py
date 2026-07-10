import logging
from uuid import UUID

from app.application.service.ai_chat_service import AiChatService
from app.application.usecase.diary_keywords import normalize_diary_keywords
from app.application.usecase.extract_chunks import ExtractChunksUseCase
from app.domain.model.diary import Diary
from app.domain.model.emotion import Emotion
from app.domain.repository.chat_session_repository import ChatSessionRepository
from app.domain.repository.diary_repository import DiaryRepository

logger = logging.getLogger(__name__)


class FinalizeDiaryUseCase:
    def __init__(
        self,
        chat_repo: ChatSessionRepository,
        diary_repo: DiaryRepository,
        ai: AiChatService,
        extract_chunks: ExtractChunksUseCase,
        db=None,  # GameProgressUseCase용 DB 세션 (optional — best-effort)
    ) -> None:
        self._chat_repo = chat_repo
        self._diary_repo = diary_repo
        self._ai = ai
        self._extract_chunks = extract_chunks
        self._db = db

    async def execute(self, session_id: UUID, device_id: str | None = None) -> Diary:
        session = await self._chat_repo.find_by_id(session_id)
        if not session:
            raise ValueError("세션을 찾을 수 없습니다.")

        # 하루 1개 정책은 diary_repo.save 의 upsert로 보장(재회고 시 오늘 일기 갱신).
        session.finalize()

        diary_data = await self._ai.generate_diary(session.messages)

        emotion = Emotion(diary_data.get("emotion", "calm"))
        # BUG-07: satisfaction 0~100 통일 (DEC-020)
        satisfaction = max(0, min(100, int(diary_data.get("satisfaction", 50))))

        diary = Diary(
            device_id=session.device_id,
            diary_date=session.session_date,
            title=diary_data.get("title", "오늘의 일기"),
            content=diary_data.get("content", ""),
            emotion=emotion,
            satisfaction=satisfaction,
            keywords=normalize_diary_keywords(diary_data.get("keywords")),
            chat_session_id=session.id,
        )

        await self._chat_repo.save(session)
        await self._diary_repo.save(diary)

        await self._extract_chunks.execute(
            session_id=session.id,
            diary_date=session.session_date,
            messages=session.messages,
        )

        # DEC-022.B: 키우기 게임 best-effort 통합
        # device_id 없으면 스킵 (Phase 0 PoC 호환)
        if device_id and self._db is not None:
            try:
                from app.application.usecase.game_diary_complete import GameProgressUseCase

                game_uc = GameProgressUseCase(self._db)
                new_rewards = await game_uc.on_diary_complete(device_id, session.session_date)
                if new_rewards:
                    logger.info("game rewards unlocked: %s for device %s", new_rewards, device_id)
            except Exception as exc:
                logger.warning("game integration skipped (best-effort): %s", exc)

        return diary
