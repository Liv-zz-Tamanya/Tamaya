from uuid import UUID

from app.domain.model.health_session import HealthSession
from app.domain.repository.health_session_repository import HealthSessionRepository


class GetHealthSessionUseCase:
    def __init__(self, repo: HealthSessionRepository) -> None:
        self._repo = repo

    async def execute(self, session_id: UUID) -> HealthSession:
        session = await self._repo.find_by_id(session_id)
        if not session:
            raise ValueError("세션을 찾을 수 없습니다.")
        return session
