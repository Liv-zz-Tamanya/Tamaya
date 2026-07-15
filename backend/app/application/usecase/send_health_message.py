from uuid import UUID

from app.application.service.chat_message_adapter import (
    extract_ai_message_text,
    to_langchain_messages,
)
from app.application.usecase.personal_assistant_agent import PersonalAssistantMode
from app.application.usecase.personal_assistant_agent_factory import PersonalAssistantAgentFactory
from app.domain.model.health_message import HealthMessage
from app.domain.repository.health_session_repository import HealthSessionRepository


class SendHealthMessageUseCase:
    def __init__(
        self,
        repo: HealthSessionRepository,
        personal_assistant_factory: PersonalAssistantAgentFactory,
    ) -> None:
        self._repo = repo
        self._personal_assistant_factory = personal_assistant_factory

    async def execute(
        self,
        session_id: UUID,
        content: str,
        device_id: str,
    ) -> tuple[HealthMessage, HealthMessage]:
        session = await self._repo.find_by_id(session_id, device_id)
        if not session:
            raise ValueError("세션을 찾을 수 없습니다.")

        user_msg = session.add_message("user", content)

        agent = self._personal_assistant_factory.create(
            device_id=session.device_id,
            session_id=session.id,
            mode=PersonalAssistantMode.HEALTH,
        )
        response = await agent.run(
            messages=to_langchain_messages(session.messages),
            mode=PersonalAssistantMode.HEALTH,
        )
        ai_response = extract_ai_message_text(response)
        ai_msg = session.add_message("assistant", ai_response)
        await self._repo.save(session)
        return user_msg, ai_msg
