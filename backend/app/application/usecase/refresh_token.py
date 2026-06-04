from uuid import UUID

from app.domain.repository.user_repository import UserRepository
from app.infrastructure.auth import jwt_service
from app.infrastructure.auth.jwt_service import TokenError


class RefreshTokenUseCase:
    def __init__(self, user_repo: UserRepository) -> None:
        self._user_repo = user_repo

    async def execute(self, refresh_token: str) -> dict:
        payload = jwt_service.decode_token(refresh_token, expected_type="refresh")
        user_id = UUID(payload["sub"])

        user = await self._user_repo.find_by_id(user_id)
        if user is None:
            raise TokenError("사용자를 찾을 수 없습니다.")

        access = jwt_service.create_access_token(user_id)
        new_refresh, _ = jwt_service.create_refresh_token(user_id)
        return {"access_token": access, "refresh_token": new_refresh}
