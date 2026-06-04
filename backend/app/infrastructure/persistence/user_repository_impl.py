from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.model.user import User
from app.domain.repository.user_repository import UserRepository
from app.infrastructure.persistence.models import UserModel


class UserRepositoryImpl(UserRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def save(self, user: User) -> User:
        model = await self._db.get(UserModel, user.id)
        if model is None:
            model = UserModel(id=user.id, created_at=user.created_at)
            self._db.add(model)
        model.kind = user.kind
        model.name = user.name
        model.needs_onboarding = user.needs_onboarding
        model.kakao_id = user.kakao_id
        await self._db.commit()
        return user

    async def find_by_id(self, user_id: UUID) -> User | None:
        model = await self._db.get(UserModel, user_id)
        return self._to_domain(model) if model else None

    async def find_by_kakao_id(self, kakao_id: str) -> User | None:
        stmt = select(UserModel).where(UserModel.kakao_id == kakao_id)
        result = await self._db.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    @staticmethod
    def _to_domain(model: UserModel) -> User:
        return User(
            id=model.id,
            kind=model.kind,
            name=model.name,
            needs_onboarding=model.needs_onboarding,
            kakao_id=model.kakao_id,
            created_at=model.created_at,
        )
