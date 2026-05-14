from abc import ABC, abstractmethod

from app.domain.model.health_message import HealthMessage


class HealthAiService(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[HealthMessage],
        health_context: list[str] | None = None,
    ) -> str: ...
