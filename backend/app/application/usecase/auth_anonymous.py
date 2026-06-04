from app.domain.model.user import User
from app.domain.repository.user_repository import UserRepository
from app.infrastructure.auth import jwt_service


class AuthAnonymousUseCase:
    def __init__(self, user_repo: UserRepository) -> None:
        self._user_repo = user_repo

    async def execute(self) -> dict:
        user = User(kind="anonymous", needs_onboarding=True)
        await self._user_repo.save(user)

        access = jwt_service.create_access_token(user.id)
        refresh, _ = jwt_service.create_refresh_token(user.id)
        return {
            "access_token": access,
            "refresh_token": refresh,
            "user": user,
            "onboarding_step": 0,
        }
