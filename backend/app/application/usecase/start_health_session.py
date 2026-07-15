from app.application.service.health_ai_service import HealthAiService
from app.domain.model.health_session import HealthSession
from app.domain.repository.health_session_repository import HealthSessionRepository


class StartHealthSessionUseCase:
    def __init__(
        self,
        repo: HealthSessionRepository,
        ai: HealthAiService,
    ) -> None:
        self._repo = repo
        self._ai = ai

    async def execute(self, device_id: str) -> HealthSession:
        session = HealthSession(device_id=device_id)
        greeting = await self._ai.chat(messages=[], health_context=None)
        session.add_message("assistant", greeting)
        await self._repo.save(session)
        return session
