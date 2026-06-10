"""BYOK CLOVA 자격 해석 — 순수 함수(외부 의존 0).

사용자 제공 키 > env 키 > mock 의 우선순위로 요청별 자격을 결정한다.
키 마스킹은 마지막 4자만 노출하며, 4자 이하 키는 전부 가린다(부분 노출 방지).
어떤 함수도 settings를 변경하지 않는다(env 비파괴는 호출부 책임).
"""

from dataclasses import dataclass

_MASK = "••••"


def mask_api_key(key: str) -> str:
    """키를 ••••last4 형태로 마스킹한다. 4자 이하/빈 키는 전부 가림."""
    if not key:
        return ""
    if len(key) <= 4:
        return _MASK
    return _MASK + key[-4:]


@dataclass(frozen=True)
class ClovaCredential:
    api_key: str | None
    use_mock: bool


def resolve_clova_credential(
    user_key: str | None,
    env_key: str,
    mock_mode: bool,
) -> ClovaCredential:
    """우선순위 user key > env > mock 으로 요청별 자격을 결정한다.

    - 사용자 키가 있으면 그 키로 **real** (env·mock 무시) — BYOK의 핵심.
    - 사용자 키가 없고 env 키가 있으며 mock_mode가 꺼져 있으면 env 키로 real.
    - 그 외에는 mock fallback.
    """
    user = (user_key or "").strip()
    env = (env_key or "").strip()  # 공백 패딩된 env 키가 real 경로를 타지 않도록 정규화
    if user:
        return ClovaCredential(api_key=user, use_mock=False)
    if env and not mock_mode:
        return ClovaCredential(api_key=env, use_mock=False)
    # mock fallback: 실제 키가 필요 없으므로 클라이언트에 자격을 싣지 않는다(최소권한).
    return ClovaCredential(api_key=None, use_mock=True)
