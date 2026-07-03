"""
JWT 발급 / 검증 유틸리티
DEC-022.4: device_id 익명 + 카카오 OAuth2 인증
DEC-023: jti 기반 strict 1세션 무효화

의존: python-jose (JOSE/JWT) — pyproject.toml에 추가 필요
fallback: python-jose 없는 환경에선 더미 토큰 반환 (MOCK MODE)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.infrastructure.config.settings import settings

_JWT_ALGORITHM = "HS256"
_ACCESS_EXPIRE_MIN = 15
_REFRESH_EXPIRE_DAYS = 30


def _secret() -> str:
    return settings.jwt_secret


def issue_access_token(identity: str, jti: str) -> str:
    """access token — 15분 만료"""
    try:
        from jose import jwt  # type: ignore[import]

        payload = {
            "sub": identity,
            "jti": jti,
            "type": "access",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=_ACCESS_EXPIRE_MIN),
        }
        return jwt.encode(payload, _secret(), algorithm=_JWT_ALGORITHM)
    except ImportError:
        # python-jose 미설치 환경: MOCK 토큰 반환
        return f"mock_access_{identity}_{jti}"


def issue_refresh_token(identity: str) -> tuple[str, str]:
    """refresh token — 30일 만료. 반환: (token, jti)"""
    jti = str(uuid.uuid4())
    try:
        from jose import jwt  # type: ignore[import]

        payload = {
            "sub": identity,
            "jti": jti,
            "type": "refresh",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(days=_REFRESH_EXPIRE_DAYS),
        }
        return jwt.encode(payload, _secret(), algorithm=_JWT_ALGORITHM), jti
    except ImportError:
        return f"mock_refresh_{identity}_{jti}", jti


def decode_token(token: str) -> dict:
    """
    토큰 디코드. 만료·서명 검증 포함.
    반환: payload dict (sub, jti, type, exp …)
    예외: jose.JWTError — 호출부에서 401 처리
    """
    try:
        from jose import jwt  # type: ignore[import]

        return jwt.decode(token, _secret(), algorithms=[_JWT_ALGORITHM])
    except ImportError:
        # MOCK 모드: token 파싱
        parts = token.split("_")
        if len(parts) >= 4:
            return {"sub": parts[2], "jti": parts[3], "type": parts[1]}
        raise ValueError("Invalid mock token")
