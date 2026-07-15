from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.model.health_session import HealthSession


class HealthSessionRepository(ABC):
    @abstractmethod
    async def save(self, session: HealthSession) -> HealthSession: ...

    @abstractmethod
    async def find_by_id(self, session_id: UUID, device_id: str) -> HealthSession | None: ...
