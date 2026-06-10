"""CLOVA 설정 — device_id별 마스킹 키 프리뷰(원문 미보관)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ClovaSetting:
    device_id: str
    masked_key: str  # ••••last4 — 원문 키는 서버에 저장하지 않는다
    has_key: bool
