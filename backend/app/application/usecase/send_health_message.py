from uuid import UUID

from app.application.usecase.health_chat_agent import HealthChatAgent
from app.domain.model.health_message import HealthMessage
from app.domain.repository.health_session_repository import HealthSessionRepository


class SendHealthMessageUseCase:
    def __init__(
        self,
        repo: HealthSessionRepository,
        agent: HealthChatAgent,
    ) -> None:
        self._repo = repo
        self._agent = agent

    async def execute(
        self,
        session_id: UUID,
        content: str,
    ) -> tuple[HealthMessage, HealthMessage]:
        session = await self._repo.find_by_id(session_id)
        if not session:
            raise ValueError("세션을 찾을 수 없습니다.")

        user_msg = session.add_message("user", content)

        ai_response = await self._agent.run(
            session_id=session.id,
            messages=session.messages,
            current_user_message=content,
        )

        ai_msg = session.add_message("assistant", ai_response)
        await self._repo.save(session)
        return user_msg, ai_msg
