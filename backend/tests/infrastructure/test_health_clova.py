from __future__ import annotations

from datetime import datetime

from app.application.service.health_ai_service import HealthAiService
from app.domain.model.health_message import HealthMessage
from app.infrastructure.config.settings import settings
from app.infrastructure.external.clova_client import (
    HEALTH_CHAT_GREETING,
    HealthClovaClient,
)


def test_health_clova_client_is_health_ai_service():
    assert isinstance(HealthClovaClient(), HealthAiService)


def test_health_client_uses_per_request_key_without_touching_settings():
    original_key = settings.clova_api_key
    original_mock = settings.clova_mock_mode

    client = HealthClovaClient(api_key="user-key", mock=False)

    assert client._mock is False
    assert client._client.api_key == "user-key"
    assert settings.clova_api_key == original_key
    assert settings.clova_mock_mode == original_mock


def test_health_client_defaults_to_settings():
    client = HealthClovaClient()

    assert client._mock == settings.clova_mock_mode


async def test_health_mock_chat_does_not_call_external_api(monkeypatch):
    client = HealthClovaClient(mock=True)

    async def fail_if_called(*args, **kwargs):  # pragma: no cover
        raise AssertionError("external CLOVA API should not be called in mock mode")

    monkeypatch.setattr(client._client.chat.completions, "create", fail_if_called)
    reply = await client.chat(
        messages=[
            HealthMessage(
                role="user",
                content="어제 몇 걸음 걸었어?",
                created_at=datetime.now(),
            )
        ],
        health_context=[],
    )

    assert isinstance(reply, str)
    assert reply.strip() != ""


async def test_health_mock_chat_with_context_does_not_call_external_api(monkeypatch):
    client = HealthClovaClient(mock=True)

    async def fail_if_called(*args, **kwargs):  # pragma: no cover
        raise AssertionError("external CLOVA API should not be called in mock mode")

    monkeypatch.setattr(client._client.chat.completions, "create", fail_if_called)
    reply = await client.chat(
        messages=[
            HealthMessage(
                role="user",
                content="이 기록 어때?",
                created_at=datetime.now(),
            )
        ],
        health_context=["2026-07-10에 9,144걸음을 걸었어."],
    )

    assert isinstance(reply, str)
    assert reply.strip() != ""


async def test_health_greeting_is_returned_without_external_api(monkeypatch):
    # api_key를 명시하지 않으면 settings.clova_api_key에 의존해 환경(.env 유무)에 따라
    # 결과가 갈림 — CI처럼 키가 없는 환경에서는 클라이언트 생성 자체가 실패한다
    client = HealthClovaClient(api_key="test-key", mock=False)

    async def fail_if_called(*args, **kwargs):  # pragma: no cover
        raise AssertionError("external CLOVA API should not be called for greeting")

    monkeypatch.setattr(client._client.chat.completions, "create", fail_if_called)

    assert await client.chat(messages=[]) == HEALTH_CHAT_GREETING
