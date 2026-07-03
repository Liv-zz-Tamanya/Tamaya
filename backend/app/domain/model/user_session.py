"""
DEC-023: 동시접속 strict 1세션 도메인 모델
인증 방식: device_id 익명 OR kakao OAuth2 (DEC-022.4)
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import UUID, uuid4

TOKEN_EXPIRE_MINUTES = 15  # access token
REFRESH_EXPIRE_DAYS = 30  # refresh token


@dataclass
class UserSession:
    """
    JWT jti 단위 세션. 동시접속 strict: 신규 세션 발급 시 기존 세션 revoke.
    device_id: 익명 사용자 식별자 (UUID v4)
    kakao_id: 카카오 OAuth 사용자 식별자
    둘 중 하나만 사용.
    """

    id: UUID = field(default_factory=uuid4)
    device_id: str | None = None
    kakao_id: str | None = None
    jti: str = field(default_factory=lambda: str(uuid4()))
    issued_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(
        default_factory=lambda: datetime.now() + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    )
    revoked_at: datetime | None = None

    @property
    def identity(self) -> str:
        """device_id 우선, 없으면 kakao_id"""
        return self.device_id or self.kakao_id or ""

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None

    def revoke(self) -> None:
        self.revoked_at = datetime.now()

    @classmethod
    def for_device(cls, device_id: str) -> "UserSession":
        return cls(device_id=device_id)

    @classmethod
    def for_kakao(cls, kakao_id: str) -> "UserSession":
        return cls(kakao_id=kakao_id)
