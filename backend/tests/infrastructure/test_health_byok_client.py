from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.application.service.health_ai_service import HealthAiService
from app.infrastructure.config.dependencies import get_health_ai_service
from app.infrastructure.config.settings import settings
from app.infrastructure.external.clova_client import HealthClovaClient


def test_health_di_with_header_builds_real_client_with_user_key():
    original_key = settings.clova_api_key
    original_mock = settings.clova_mock_mode

    service = get_health_ai_service(x_clova_api_key="user-supplied-key")

    assert isinstance(service, HealthAiService)
    assert isinstance(service, HealthClovaClient)
    assert service._mock is False
    assert service._client.api_key == "user-supplied-key"
    assert settings.clova_api_key == original_key
    assert settings.clova_mock_mode == original_mock


def test_health_di_without_header_uses_resolved_defaults(monkeypatch):
    monkeypatch.setattr(settings, "clova_api_key", "")
    monkeypatch.setattr(settings, "clova_mock_mode", True)

    service = get_health_ai_service(x_clova_api_key=None)

    assert isinstance(service, HealthClovaClient)
    assert service._mock is True
    assert service._client.api_key in (None, "")


def test_health_di_uses_env_key_when_mock_off(monkeypatch):
    monkeypatch.setattr(settings, "clova_api_key", "env-key")
    monkeypatch.setattr(settings, "clova_mock_mode", False)

    service = get_health_ai_service(x_clova_api_key=None)

    assert isinstance(service, HealthClovaClient)
    assert service._mock is False
    assert service._client.api_key == "env-key"


def test_health_di_ignores_blank_user_key(monkeypatch):
    monkeypatch.setattr(settings, "clova_api_key", "")
    monkeypatch.setattr(settings, "clova_mock_mode", False)

    service = get_health_ai_service(x_clova_api_key="   ")

    assert isinstance(service, HealthClovaClient)
    assert service._mock is True
    assert service._client.api_key in (None, "")


def test_health_di_keeps_request_keys_isolated():
    original_key = settings.clova_api_key
    original_mock = settings.clova_mock_mode

    service_a = get_health_ai_service(x_clova_api_key="user-key-a")
    service_b = get_health_ai_service(x_clova_api_key="user-key-b")

    assert isinstance(service_a, HealthClovaClient)
    assert isinstance(service_b, HealthClovaClient)
    assert service_a is not service_b
    assert service_a._client.api_key == "user-key-a"
    assert service_b._client.api_key == "user-key-b"
    assert settings.clova_api_key == original_key
    assert settings.clova_mock_mode == original_mock


def test_health_ai_dependency_receives_x_clova_api_key_header():
    app = FastAPI()

    @app.get("/probe")
    def probe(service: HealthAiService = Depends(get_health_ai_service)):
        assert isinstance(service, HealthClovaClient)
        return {"mock": service._mock, "api_key": service._client.api_key}

    client = TestClient(app)

    response = client.get("/probe", headers={"X-Clova-Api-Key": "header-key"})

    assert response.status_code == 200
    assert response.json() == {"mock": False, "api_key": "header-key"}
