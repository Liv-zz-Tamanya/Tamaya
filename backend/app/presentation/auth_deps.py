"""프레젠테이션 인증 의존성.

회고 세션·일기를 사용자(device)별로 스코핑하기 위해, 보호 라우트에서
Bearer JWT의 sub(=identity, 익명 device 인증 시 device_id)를 추출한다.
"""

from __future__ import annotations

from fastapi import Header, HTTPException, status

from app.infrastructure.auth.jwt_handler import decode_token


def get_current_device_id(authorization: str | None = Header(default=None)) -> str:
    """Authorization: Bearer <jwt> 에서 sub(device_id)를 반환. 없거나 유효하지 않으면 401."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "인증 토큰이 필요합니다.")
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_token(token)
    except Exception as exc:  # jose.JWTError / ValueError 등
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "유효하지 않은 토큰입니다.") from exc
    identity = payload.get("sub")
    if not identity:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "유효하지 않은 토큰입니다.")
    return identity
