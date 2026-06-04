import uuid
from datetime import datetime, timedelta, timezone

import jwt

from app.infrastructure.config.settings import settings


class TokenError(Exception):
    """JWT 검증 실패 (만료/위조/타입 불일치)."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(user_id: uuid.UUID) -> str:
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": _now(),
        "exp": _now() + timedelta(minutes=settings.access_token_ttl_min),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: uuid.UUID, jti: str | None = None) -> tuple[str, str]:
    """refresh 토큰과 jti를 함께 반환 (추후 strict 1세션 revoke 대비)."""
    jti = jti or str(uuid.uuid4())
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": jti,
        "iat": _now(),
        "exp": _now() + timedelta(days=settings.refresh_token_ttl_days),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, jti


def decode_token(token: str, expected_type: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as e:
        raise TokenError("토큰이 만료되었습니다.") from e
    except jwt.PyJWTError as e:
        raise TokenError("유효하지 않은 토큰입니다.") from e

    if payload.get("type") != expected_type:
        raise TokenError("토큰 종류가 올바르지 않습니다.")
    return payload
