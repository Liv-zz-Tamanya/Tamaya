from datetime import date

from app.application.service.ai_chat_service import AiChatService
from app.domain.model.chat_session import ChatSession
from app.domain.repository.chat_session_repository import ChatSessionRepository


class StartChatSessionUseCase:
    def __init__(self, repo: ChatSessionRepository, ai: AiChatService) -> None:
        self._repo = repo
        self._ai = ai

    async def execute(self) -> ChatSession:
        today = date.today()
        existing = await self._repo.find_by_date(today)
        if existing:
            return existing

        session = ChatSession(session_date=today)

        # AI 첫 인사 메시지 생성
        greeting = await self._ai.chat([], suggest_finalize=False)
        session.add_message("assistant", greeting)

        await self._repo.save(session)
        return session
