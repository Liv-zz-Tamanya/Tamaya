"""코칭 라우터 — PersonalAssistantAgent 경로 회귀."""

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from app.application.usecase.personal_assistant_agent import PersonalAssistantMode
from app.domain.service.medical_guardrail import GuardrailVerdict, build_disclaimer
from app.infrastructure.config.dependencies import (
    get_coaching_agent,
    get_coaching_personal_assistant_agent_factory,
    get_extract_signals_usecase,
)
from app.main import app
from app.presentation.auth_deps import get_current_device_id
from app.presentation.router.coaching_schemas import CoachingMessageRequest


class _FakePersonalAssistantAgent:
    def __init__(self, content: str = "오늘 하루도 고생 많았어요") -> None:
        self.content = content
        self.calls: list[dict] = []

    async def run(self, *, messages, mode: PersonalAssistantMode, diary_context=None, **kwargs):
        self.calls.append(
            {
                "messages": list(messages),
                "mode": mode,
                "diary_context": diary_context,
                "coaching_context": kwargs.get("coaching_context"),
            }
        )
        return AIMessage(content=self.content)


class _FakePersonalAssistantFactory:
    def __init__(self, agent: _FakePersonalAssistantAgent | None = None) -> None:
        self.agent = agent or _FakePersonalAssistantAgent()
        self.calls: list[dict] = []

    def create(self, *, device_id, session_id, mode):
        self.calls.append({"device_id": device_id, "session_id": session_id, "mode": mode})
        return self.agent


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


def _override_factory(
    factory: _FakePersonalAssistantFactory | None = None,
) -> _FakePersonalAssistantFactory:
    fake = factory or _FakePersonalAssistantFactory()
    app.dependency_overrides[get_coaching_personal_assistant_agent_factory] = lambda: fake
    return fake


def _override_extract_signals(spy: _SpyExtractSignals | None = None) -> _SpyExtractSignals:
    fake = spy or _SpyExtractSignals()
    app.dependency_overrides[get_extract_signals_usecase] = lambda: fake
    return fake


def test_coaching_message_requires_authentication():
    _override_factory()
    client = TestClient(app)

    resp = client.post(
        "/api/v1/coaching/messages",
        json={"message": "오늘 너무 지쳤어", "history": []},
    )

    assert resp.status_code == 401


def test_safe_coaching_message_returns_reply():
    _authenticate()
    _override_extract_signals()
    factory = _override_factory()
    app.dependency_overrides[get_coaching_agent] = lambda: (_ for _ in ()).throw(
        AssertionError("CoachingAgent should not be used")
    )
    client = TestClient(app)

    resp = client.post(
        "/api/v1/coaching/messages",
        json={"message": "오늘 너무 지쳤어", "history": []},
    )

    assert resp.status_code == 200
    assert resp.json()["reply"] == "오늘 하루도 고생 많았어요"
    assert factory.calls[0]["device_id"] == "device-A"
    assert factory.calls[0]["mode"] == PersonalAssistantMode.COACHING
    assert factory.agent.calls[0]["mode"] == PersonalAssistantMode.COACHING
    assert factory.agent.calls[0]["diary_context"] is None


def test_risky_coaching_message_returns_disclaimer_schema():
    _authenticate()
    _override_extract_signals()
    factory = _override_factory(
        _FakePersonalAssistantFactory(
            _FakePersonalAssistantAgent(build_disclaimer(GuardrailVerdict.ADVICE_BOUNDARY))
        )
    )
    client = TestClient(app)

    resp = client.post(
        "/api/v1/coaching/messages",
        json={"message": "이 약 먹어도 돼?", "history": []},
    )

    assert resp.status_code == 200
    assert "전문가" in resp.json()["reply"]
    assert "GuardrailVerdict" not in resp.json()["reply"]
    assert factory.agent.calls[0]["mode"] == PersonalAssistantMode.COACHING


def test_emergency_coaching_message_returns_emergency_disclaimer_schema():
    _authenticate()
    _override_extract_signals()
    _override_factory(
        _FakePersonalAssistantFactory(
            _FakePersonalAssistantAgent(build_disclaimer(GuardrailVerdict.EMERGENCY))
        )
    )
    client = TestClient(app)

    resp = client.post(
        "/api/v1/coaching/messages",
        json={"message": "가슴이 너무 아프고 숨이 막혀", "history": []},
    )

    assert resp.status_code == 200
    assert "119" in resp.json()["reply"]
    assert "응급실" in resp.json()["reply"]
    assert "blocked_response" not in resp.json()["reply"]


def test_history_accepted_and_reply_returned():
    _authenticate()
    factory = _override_factory()
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
    call = factory.agent.calls[0]
    assert [message.content for message in call["messages"]] == ["안녕", "안녕!", "그렇구나"]
    assert call["coaching_context"] == {"persona": "부모님"}


def test_body_device_id_does_not_override_authenticated_device_id():
    _authenticate("device-A")
    _override_factory()
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
    _override_factory()
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
