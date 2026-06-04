from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.model.character import Character


class CharacterRepository(ABC):
    @abstractmethod
    async def save(self, character: Character) -> Character: ...

    @abstractmethod
    async def find_by_user_id(self, user_id: UUID) -> Character | None: ...
