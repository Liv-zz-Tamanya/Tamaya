from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.model.user import User


class UserRepository(ABC):
    @abstractmethod
    async def save(self, user: User) -> User: ...

    @abstractmethod
    async def find_by_id(self, user_id: UUID) -> User | None: ...

    @abstractmethod
    async def find_by_kakao_id(self, kakao_id: str) -> User | None: ...
