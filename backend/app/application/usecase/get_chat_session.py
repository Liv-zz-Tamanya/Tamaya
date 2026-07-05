from uuid import UUID

from app.domain.model.chat_session import ChatSession
from app.domain.repository.chat_session_repository import ChatSessionRepository


class GetChatSessionUseCase:
    def __init__(self, repo: ChatSessionRepository) -> None:
        self._repo = repo

    async def execute(self, session_id: UUID, device_id: str) -> ChatSession:
        session = await self._repo.find_by_id(session_id)
        if not session or session.device_id != device_id:
            # 소유자가 아니면 존재 여부도 숨긴다.
            raise ValueError("세션을 찾을 수 없습니다.")
        return session
