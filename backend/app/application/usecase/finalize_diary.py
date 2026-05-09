from uuid import UUID

from app.application.service.ai_chat_service import AiChatService
from app.application.usecase.extract_chunks import ExtractChunksUseCase
from app.domain.model.diary import Diary
from app.domain.model.emotion import Emotion
from app.domain.repository.chat_session_repository import ChatSessionRepository
from app.domain.repository.diary_repository import DiaryRepository


class FinalizeDiaryUseCase:
    def __init__(
        self,
        chat_repo: ChatSessionRepository,
        diary_repo: DiaryRepository,
        ai: AiChatService,
        extract_chunks: ExtractChunksUseCase,
    ) -> None:
        self._chat_repo = chat_repo
        self._diary_repo = diary_repo
        self._ai = ai
        self._extract_chunks = extract_chunks

    async def execute(self, session_id: UUID) -> Diary:
        session = await self._chat_repo.find_by_id(session_id)
        if not session:
            raise ValueError("세션을 찾을 수 없습니다.")

        existing = await self._diary_repo.find_by_date(session.session_date)
        if existing:
            raise ValueError("오늘의 일기가 이미 작성되었습니다.")

        session.finalize()

        diary_data = await self._ai.generate_diary(session.messages)

        emotion = Emotion(diary_data.get("emotion", "calm"))
        satisfaction = max(1, min(5, int(diary_data.get("satisfaction", 3))))

        diary = Diary(
            diary_date=session.session_date,
            title=diary_data.get("title", "오늘의 일기"),
            content=diary_data.get("content", ""),
            emotion=emotion,
            satisfaction=satisfaction,
            chat_session_id=session.id,
        )

        await self._chat_repo.save(session)
        await self._diary_repo.save(diary)

        await self._extract_chunks.execute(
            session_id=session.id,
            diary_date=session.session_date,
            messages=session.messages,
        )

        return diary
