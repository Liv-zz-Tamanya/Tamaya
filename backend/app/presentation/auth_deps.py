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
from app.infrastructure.persistence.models import UserSessionModel


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
