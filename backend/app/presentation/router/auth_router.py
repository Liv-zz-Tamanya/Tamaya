from fastapi import APIRouter, Depends, HTTPException

from app.application.usecase.auth_anonymous import AuthAnonymousUseCase
from app.application.usecase.refresh_token import RefreshTokenUseCase
from app.domain.repository.user_repository import UserRepository
from app.infrastructure.auth.jwt_service import TokenError
from app.infrastructure.config.dependencies import get_user_repo
from app.presentation.router.v1_schemas import (
    AnonymousAuthRequest,
    AuthResponse,
    RefreshRequest,
    RefreshResponse,
    UserResponse,
)

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/anonymous", response_model=AuthResponse, summary="익명 로그인")
async def auth_anonymous(
    _: AnonymousAuthRequest | None = None,
    user_repo: UserRepository = Depends(get_user_repo),
):
    result = await AuthAnonymousUseCase(user_repo).execute()
    return AuthResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        user=UserResponse.from_domain(result["user"]),
        onboarding_step=result["onboarding_step"],
    )


@router.post("/refresh", response_model=RefreshResponse, summary="토큰 갱신")
async def refresh(
    body: RefreshRequest,
    user_repo: UserRepository = Depends(get_user_repo),
):
    try:
        result = await RefreshTokenUseCase(user_repo).execute(body.refresh_token)
    except TokenError as e:
        raise HTTPException(status_code=401, detail=str(e))
    return RefreshResponse(**result)


@router.post("/kakao", summary="카카오 로그인 (P0 미구현)")
async def auth_kakao():
    # TODO: Kakao OAuth — REST API key / redirect URI 발급 후 구현 (P0 범위 밖)
    raise HTTPException(status_code=501, detail="카카오 로그인은 아직 준비 중입니다.")
