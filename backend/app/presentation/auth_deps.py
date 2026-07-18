"""프레젠테이션 인증 의존성.

회고 세션·일기를 사용자(device)별로 스코핑하기 위해, 보호 라우트에서
Bearer JWT의 sub(=identity, 익명 device 인증 시 device_id)를 추출한다.
로그아웃/동시접속 strict 정합을 위해 user_sessions의 revoked_at 상태도 함께 검증한다.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.auth.jwt_handler import decode_token
from app.infrastructure.config.database import get_db
from app.infrastructure.persistence.models import UserModel, UserSessionModel


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "인증 토큰이 필요합니다.")
    return authorization.split(" ", 1)[1].strip()


def _session_identity(session: UserSessionModel) -> str:
    return session.device_id or session.kakao_id or ""


async def get_current_session(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> UserSessionModel:
    """Authorization: Bearer <access jwt> 를 활성 세션으로 해석한다."""
    token = _extract_bearer_token(authorization)
    try:
        payload = decode_token(token)
    except Exception as exc:  # jose.JWTError / ValueError 등
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "유효하지 않은 토큰입니다.") from exc

    if payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "유효하지 않은 토큰입니다.")

    identity = payload.get("sub")
    jti = payload.get("jti")
    if not identity or not jti:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "유효하지 않은 토큰입니다.")

    session = await db.scalar(select(UserSessionModel).where(UserSessionModel.jti == jti))
    now = datetime.now(UTC).replace(tzinfo=None)
    if session is None or session.revoked_at is not None or session.expires_at <= now:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "만료되었거나 로그아웃된 토큰입니다.")

    if _session_identity(session) != identity:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "유효하지 않은 토큰입니다.")

    return session


async def get_current_device_id(
    session: UserSessionModel = Depends(get_current_session),
) -> str:
    return _session_identity(session)


async def get_current_nickname_user(
    session: UserSessionModel = Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
) -> UserModel:
    """현재 Bearer 세션에 연결된 닉네임 사용자를 조회한다.

    JWT subject와 기존 device_id 데이터 네임스페이스는 변경하지 않고,
    `nick-{nickname}` 세션만 users.id 기반 설정 API에 접근하게 한다.
    """
    device_id = session.device_id
    if not device_id or not device_id.startswith("nick-"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "닉네임 로그인이 필요합니다.")

    nickname = device_id.removeprefix("nick-")
    if not nickname:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "유효하지 않은 닉네임 세션입니다.")

    user = await db.scalar(select(UserModel).where(UserModel.nickname == nickname))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "존재하지 않는 닉네임 사용자입니다.")
    return user
