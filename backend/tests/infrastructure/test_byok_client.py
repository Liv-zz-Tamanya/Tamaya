"""BYOK 요청별 ClovaClient 구성 + 헤더 DI (G003-1, TDD).

요청별 api_key/mock override가 settings를 변경하지 않고 클라이언트에 반영되는지,
X-Clova-Api-Key 헤더가 있으면 real(user key), 없으면 기존 기본값(mock)을 쓰는지 검증한다.
"""

from app.application.service.ai_chat_service import AiChatService
from app.infrastructure.config.dependencies import get_ai_chat_service
from app.infrastructure.config.settings import settings
from app.infrastructure.external.clova_client import ClovaClient


def test_client_uses_per_request_key_without_touching_settings():
    original_key = settings.clova_api_key
    original_mock = settings.clova_mock_mode

    client = ClovaClient(api_key="user-key", mock=False)

    assert client._mock is False
    assert client._client.api_key == "user-key"
    # settings는 어떤 경우에도 변경되지 않아야 함(env 비파괴)
    assert settings.clova_api_key == original_key
    assert settings.clova_mock_mode == original_mock


def test_client_defaults_to_settings():
    client = ClovaClient()
    assert client._mock == settings.clova_mock_mode


def test_di_with_header_builds_real_client_with_user_key():
    service = get_ai_chat_service(x_clova_api_key="user-supplied-key")
    assert isinstance(service, AiChatService)
    assert isinstance(service, ClovaClient)
    assert service._mock is False
    assert service._client.api_key == "user-supplied-key"


def test_di_without_header_uses_defaults():
    service = get_ai_chat_service(x_clova_api_key=None)
    assert isinstance(service, ClovaClient)
    # 헤더 없으면 기존 동작(기본 mock 모드) 유지 — 회귀 방지
    assert service._mock == settings.clova_mock_mode
