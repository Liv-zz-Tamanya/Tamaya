import asyncio
from uuid import UUID

from app.application.service.ai_chat_service import AiChatService
from app.application.usecase.chat_agent import ChatAgent
from app.application.usecase.extract_chunks import ExtractChunksUseCase
from app.domain.model.chat_message import ChatMessage
from app.domain.model.chat_session import ChatSession
from app.domain.model.diary import Diary
from app.domain.model.emotion import Emotion
from app.domain.repository.chat_session_repository import ChatSessionRepository
from app.domain.repository.diary_repository import DiaryRepository


class SendMessageUseCase:
    def __init__(
        self,
        repo: ChatSessionRepository,
        ai: AiChatService,
        diary_repo: DiaryRepository,
        chat_agent: ChatAgent,
        extract_chunks: ExtractChunksUseCase,
    ) -> None:
        self._repo = repo
        self._ai = ai
        self._diary_repo = diary_repo
        self._chat_agent = chat_agent
        self._extract_chunks = extract_chunks

    async def execute(
        self, session_id: UUID, content: str
    ) -> tuple[ChatMessage, ChatMessage, bool, Diary | None]:
        session = await self._repo.find_by_id(session_id)
        if not session:
            raise ValueError("세션을 찾을 수 없습니다.")
        if session.is_finalized:
            raise ValueError("이미 완료된 세션입니다.")

        user_msg = session.add_message("user", content)

        if session.should_suggest_finalize:
            intent = await self._ai.detect_finalize_intent(content)
            if intent:
                user_msg, ai_msg, diary = await self._handle_auto_finalize(session, user_msg)
                return user_msg, ai_msg, False, diary

        ai_response = await self._chat_agent.run(
            session_id=session.id,
            messages=session.messages,
            current_user_message=content,
            suggest_finalize=session.should_suggest_finalize,
        )
        ai_msg = session.add_message("assistant", ai_response)
        await self._repo.save(session)
        return user_msg, ai_msg, session.should_suggest_finalize, None

    async def _handle_auto_finalize(
        self, session: ChatSession, user_msg: ChatMessage
    ) -> tuple[ChatMessage, ChatMessage, Diary]:
        existing = await self._diary_repo.find_by_date(session.session_date)
        if existing:
            raise ValueError("오늘의 일기가 이미 작성되었습니다.")

        closing_text, diary_data = await asyncio.gather(
            self._ai.generate_closing_message(session.messages),
            self._ai.generate_diary(session.messages),
        )

        ai_msg = session.add_message("assistant", closing_text)
        session.finalize()

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

        await self._repo.save(session)
        await self._diary_repo.save(diary)

        await self._extract_chunks.execute(
            session_id=session.id,
            diary_date=session.session_date,
            messages=session.messages,
        )

        return user_msg, ai_msg, diary
