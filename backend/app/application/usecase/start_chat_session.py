from datetime import date

from app.application.service.ai_chat_service import AiChatService
from app.domain.model.chat_session import ChatSession
from app.domain.repository.chat_session_repository import ChatSessionRepository


class StartChatSessionUseCase:
    def __init__(self, repo: ChatSessionRepository, ai: AiChatService) -> None:
        self._repo = repo
        self._ai = ai

    async def execute(self, device_id: str) -> ChatSession:
        today = date.today()
        existing = await self._repo.find_by_device_and_date(device_id, today)
        if existing and not existing.is_finalized:
            return existing  # 진행 중인 세션은 이어서 진행

        # AI 첫 인사 메시지 생성
        greeting = await self._ai.chat([], suggest_finalize=False)

        if existing:
            # 오늘 세션이 이미 완료됨 → 리셋해서 재회고 허용
            # (UNIQUE(device_id, session_date) 때문에 새 행을 못 만들어 같은 행을 재사용)
            existing.messages = []
            existing.is_finalized = False
            existing.add_message("assistant", greeting)
            await self._repo.save(existing)
            return existing

        session = ChatSession(device_id=device_id, session_date=today)
        session.add_message("assistant", greeting)
        await self._repo.save(session)
        return session
