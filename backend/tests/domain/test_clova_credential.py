"""BYOK CLOVA 자격 해석 — 순수 함수 (G003-1, TDD).

우선순위 user key > env > mock. 키 마스킹은 last4만 노출(짧은 키는 전부 가림).
env(settings) 값은 이 함수 어디서도 변경되지 않는다(순수).
"""

from app.domain.service.clova_credential import (
    ClovaCredential,
    mask_api_key,
    resolve_clova_credential,
)


def test_mask_long_key_shows_only_last4():
    assert mask_api_key("sk-1234567890") == "••••7890"


def test_mask_short_key_fully_masked():
    # 4자 이하 키는 last4가 곧 전체이므로 노출하지 않고 전부 가린다
    assert mask_api_key("1234") == "••••"
    assert mask_api_key("ab") == "••••"


def test_mask_empty_key_is_empty():
    assert mask_api_key("") == ""


def test_user_key_wins_over_env_and_mock():
    cred = resolve_clova_credential(user_key="user-key", env_key="env-key", mock_mode=True)
    assert cred == ClovaCredential(api_key="user-key", use_mock=False)


def test_blank_user_key_is_ignored():
    cred = resolve_clova_credential(user_key="   ", env_key="env-key", mock_mode=False)
    assert cred == ClovaCredential(api_key="env-key", use_mock=False)


def test_env_key_used_real_when_mock_off():
    cred = resolve_clova_credential(user_key=None, env_key="env-key", mock_mode=False)
    assert cred == ClovaCredential(api_key="env-key", use_mock=False)


def test_mock_mode_falls_back_to_mock_even_with_env_key():
    cred = resolve_clova_credential(user_key=None, env_key="env-key", mock_mode=True)
    assert cred.use_mock is True
    # 최소권한: mock일 때는 실제 키를 자격에 싣지 않는다
    assert cred.api_key is None


def test_whitespace_env_key_does_not_trigger_real_mode():
    # 공백만 있는 env 키는 real 경로를 타면 안 됨(과금성 무효 호출 방지)
    cred = resolve_clova_credential(user_key=None, env_key="   ", mock_mode=False)
    assert cred == ClovaCredential(api_key=None, use_mock=True)


def test_nothing_provided_falls_back_to_mock():
    cred = resolve_clova_credential(user_key="", env_key="", mock_mode=False)
    assert cred == ClovaCredential(api_key=None, use_mock=True)
