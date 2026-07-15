"""코칭 라우터 — 수직 슬라이스 (G004-1, TDD).

TestClient + dependency_overrides(fake CoachingAiService)로 실 CLOVA 없이
HTTP→usecase→guardrail-first agent 경로를 검증한다.
"""

import pytest
from fastapi.testclient import TestClient

from app.application.service.coaching_ai_service import CoachingAiService
from app.domain.model.chat_message import ChatMessage
from app.infrastructure.config.dependencies import (
    get_coaching_ai_service,
    get_extract_signals_usecase,
)
from app.main import app
from app.presentation.auth_deps import get_current_device_id
from app.presentation.router.coaching_schemas import CoachingMessageRequest


class _FakeCoachAi(CoachingAiService):
    def __init__(self) -> None:
        self.calls: list[tuple[list[ChatMessage], str | None]] = []

    async def coach(self, messages: list[ChatMessage], persona: str | None = None) -> str:
        self.calls.append((messages, persona))
        return "오늘 하루도 고생 많았어요"


class _SpyExtractSignals:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[dict] = []

    async def execute(self, **kwargs) -> None:
        self.calls.append(kwargs)
        if self.fail:
            raise RuntimeError("signal failed")


@pytest.fixture(autouse=True)
def _override():
    yield
    app.dependency_overrides.clear()


def _authenticate(device_id: str = "device-A") -> None:
    app.dependency_overrides[get_current_device_id] = lambda: device_id


def _override_coaching_ai(ai: _FakeCoachAi | None = None) -> _FakeCoachAi:
    fake = ai or _FakeCoachAi()
    app.dependency_overrides[get_coaching_ai_service] = lambda: fake
    return fake


def _override_extract_signals(spy: _SpyExtractSignals | None = None) -> _SpyExtractSignals:
    fake = spy or _SpyExtractSignals()
    app.dependency_overrides[get_extract_signals_usecase] = lambda: fake
    return fake


def test_coaching_message_requires_authentication():
    _override_coaching_ai()
    client = TestClient(app)

    resp = client.post(
        "/api/v1/coaching/messages",
        json={"message": "오늘 너무 지쳤어", "history": []},
    )

    assert resp.status_code == 401


def test_safe_coaching_message_returns_reply():
    _authenticate()
    _override_coaching_ai()
    client = TestClient(app)
    resp = client.post(
        "/api/v1/coaching/messages",
        json={"message": "오늘 너무 지쳤어", "history": []},
    )
    assert resp.status_code == 200
    assert resp.json()["reply"] == "오늘 하루도 고생 많았어요"


def test_risky_coaching_message_returns_disclaimer():
    _authenticate()
    ai = _override_coaching_ai()
    client = TestClient(app)
    resp = client.post(
        "/api/v1/coaching/messages",
        json={"message": "이 약 먹어도 돼?", "history": []},
    )
    assert resp.status_code == 200
    assert "전문가" in resp.json()["reply"]
    assert ai.calls == []


def test_history_accepted_and_reply_returned():
    _authenticate()
    ai = _override_coaching_ai()
    client = TestClient(app)
    resp = client.post(
        "/api/v1/coaching/messages",
        json={
            "message": "그렇구나",
            "persona": "부모님",
            "history": [
                {"role": "user", "content": "안녕"},
                {"role": "assistant", "content": "안녕!"},
            ],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["reply"] != ""
    assert len(ai.calls) == 1
    messages, persona = ai.calls[0]
    assert [m.content for m in messages] == ["안녕", "안녕!", "그렇구나"]
    assert persona == "부모님"


def test_body_device_id_does_not_override_authenticated_device_id():
    _authenticate("device-A")
    _override_coaching_ai()
    spy = _override_extract_signals()
    client = TestClient(app)

    resp = client.post(
        "/api/v1/coaching/messages",
        json={"device_id": "device-B", "message": "오늘 너무 지쳤어", "history": []},
    )

    assert resp.status_code == 200
    assert len(spy.calls) == 1
    assert spy.calls[0]["device_id"] == "device-A"


def test_signal_extraction_failure_still_returns_reply():
    _authenticate("device-A")
    _override_coaching_ai()
    spy = _override_extract_signals(_SpyExtractSignals(fail=True))
    client = TestClient(app)

    resp = client.post(
        "/api/v1/coaching/messages",
        json={"message": "오늘 너무 지쳤어", "history": []},
    )

    assert resp.status_code == 200
    assert resp.json()["reply"] == "오늘 하루도 고생 많았어요"
    assert spy.calls[0]["device_id"] == "device-A"


def test_openapi_coaching_request_schema_excludes_device_id():
    schema = CoachingMessageRequest.model_json_schema()

    assert "device_id" not in schema["properties"]
    assert {"message", "persona", "history"}.issubset(schema["properties"])
