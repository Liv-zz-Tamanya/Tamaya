from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from app.application.service.health_ai_service import HealthAiService
from app.application.usecase.personal_assistant_agent import PersonalAssistantMode
from app.domain.model.health_message import HealthMessage
from app.domain.model.health_session import HealthSession
from app.domain.repository.health_session_repository import HealthSessionRepository
from app.domain.service.medical_guardrail import GuardrailVerdict, build_disclaimer
from app.infrastructure.config.dependencies import (
    get_health_ai_service,
    get_health_chat_agent,
    get_health_session_repo,
    get_personal_assistant_agent_factory,
)
from app.main import app
from app.presentation.auth_deps import get_current_device_id


class _MemoryHealthSessionRepo(HealthSessionRepository):
    def __init__(self) -> None:
        self.sessions: dict[UUID, HealthSession] = {}

    async def save(self, session: HealthSession) -> HealthSession:
        self.sessions[session.id] = session
        return session

    async def find_by_id(self, session_id: UUID, device_id: str) -> HealthSession | None:
        session = self.sessions.get(session_id)
        if session is None or session.device_id != device_id:
            return None
        return session


class _FakeHealthAi(HealthAiService):
    async def chat(
        self,
        messages: list[HealthMessage],
        health_context: list[str] | None = None,
    ) -> str:
        return "건강 인사"


class _FakePersonalAssistantAgent:
    def __init__(self, content: str = "dev-a 건강 응답") -> None:
        self.content = content
        self.calls: list[dict] = []

    async def run(self, *, messages, mode: PersonalAssistantMode, diary_context=None):
        self.calls.append(
            {
                "messages": list(messages),
                "mode": mode,
                "diary_context": diary_context,
            }
        )
        return AIMessage(content=self.content)


class _FakePersonalAssistantFactory:
    def __init__(self, agent: _FakePersonalAssistantAgent | None = None) -> None:
        self.agent = agent or _FakePersonalAssistantAgent()
        self.calls: list[dict] = []

    def create(self, *, device_id: str, session_id: UUID, mode: PersonalAssistantMode):
        self.calls.append({"device_id": device_id, "session_id": session_id, "mode": mode})
        return self.agent


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_health_chat_session_requires_authentication():
    client = TestClient(app)

    response = client.post("/api/v1/health-chat/sessions")

    assert response.status_code == 401


def test_health_chat_message_requires_authentication():
    client = TestClient(app)

    response = client.post(
        "/api/v1/health-chat/sessions/00000000-0000-0000-0000-000000000000/messages",
        json={"content": "안녕"},
    )

    assert response.status_code == 401


def test_health_chat_session_created_for_authenticated_device():
    repo = _MemoryHealthSessionRepo()
    app.dependency_overrides[get_current_device_id] = lambda: "dev-a"
    app.dependency_overrides[get_health_session_repo] = lambda: repo
    app.dependency_overrides[get_health_ai_service] = _FakeHealthAi

    client = TestClient(app)
    response = client.post("/api/v1/health-chat/sessions")

    assert response.status_code == 200
    body = response.json()
    session = repo.sessions[UUID(body["id"])]
    assert session.device_id == "dev-a"
    assert body["messages"][0]["content"] == "건강 인사"
    assert "device_id" not in body


def test_health_chat_hides_other_device_session_on_get_and_send():
    repo = _MemoryHealthSessionRepo()
    other_session = HealthSession(device_id="dev-b")
    other_session.add_message("assistant", "B 세션")
    repo.sessions[other_session.id] = other_session
    app.dependency_overrides[get_current_device_id] = lambda: "dev-a"
    app.dependency_overrides[get_health_session_repo] = lambda: repo
    app.dependency_overrides[get_personal_assistant_agent_factory] = lambda: (
        _FakePersonalAssistantFactory()
    )

    client = TestClient(app)
    get_response = client.get(f"/api/v1/health-chat/sessions/{other_session.id}")
    send_response = client.post(
        f"/api/v1/health-chat/sessions/{other_session.id}/messages",
        json={"content": "내 메시지"},
    )

    assert get_response.status_code == 404
    assert send_response.status_code == 404
    assert [message.content for message in other_session.messages] == ["B 세션"]


def test_health_chat_message_uses_personal_assistant_factory_and_response_schema():
    repo = _MemoryHealthSessionRepo()
    session = HealthSession(device_id="dev-a")
    session.add_message("assistant", "건강 인사")
    repo.sessions[session.id] = session
    factory = _FakePersonalAssistantFactory(_FakePersonalAssistantAgent("건강 응답"))
    app.dependency_overrides[get_current_device_id] = lambda: "dev-a"
    app.dependency_overrides[get_health_session_repo] = lambda: repo
    app.dependency_overrides[get_personal_assistant_agent_factory] = lambda: factory
    app.dependency_overrides[get_health_chat_agent] = lambda: (_ for _ in ()).throw(
        AssertionError("HealthChatAgent should not be used")
    )

    client = TestClient(app)
    response = client.post(
        f"/api/v1/health-chat/sessions/{session.id}/messages",
        json={"content": "어제 걸음 수 알려줘"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user_message"]["content"] == "어제 걸음 수 알려줘"
    assert body["ai_message"]["content"] == "건강 응답"
    assert "device_id" not in body["user_message"]
    assert "device_id" not in body["ai_message"]
    assert factory.calls == [
        {"device_id": "dev-a", "session_id": session.id, "mode": PersonalAssistantMode.HEALTH}
    ]
    assert factory.agent.calls[0]["mode"] == PersonalAssistantMode.HEALTH
    assert factory.agent.calls[0]["diary_context"] is None


def test_health_chat_message_returns_advice_disclaimer_with_existing_schema():
    repo = _MemoryHealthSessionRepo()
    session = HealthSession(device_id="dev-a")
    session.add_message("assistant", "건강 인사")
    repo.sessions[session.id] = session
    factory = _FakePersonalAssistantFactory(
        _FakePersonalAssistantAgent(build_disclaimer(GuardrailVerdict.ADVICE_BOUNDARY))
    )
    app.dependency_overrides[get_current_device_id] = lambda: "dev-a"
    app.dependency_overrides[get_health_session_repo] = lambda: repo
    app.dependency_overrides[get_personal_assistant_agent_factory] = lambda: factory

    client = TestClient(app)
    response = client.post(
        f"/api/v1/health-chat/sessions/{session.id}/messages",
        json={"content": "혈압약 끊어도 돼?"},
    )

    assert response.status_code == 200
    body = response.json()
    ai_content = body["ai_message"]["content"]
    assert ai_content == build_disclaimer(GuardrailVerdict.ADVICE_BOUNDARY)
    assert "전문가" in ai_content
    assert "GuardrailVerdict" not in ai_content
    assert "blocked_response" not in ai_content
    assert "search_health_records" not in ai_content
    assert body["user_message"]["content"] == "혈압약 끊어도 돼?"
    assert "device_id" not in body["ai_message"]


def test_health_chat_message_returns_emergency_disclaimer_with_existing_schema():
    repo = _MemoryHealthSessionRepo()
    session = HealthSession(device_id="dev-a")
    session.add_message("assistant", "건강 인사")
    repo.sessions[session.id] = session
    factory = _FakePersonalAssistantFactory(
        _FakePersonalAssistantAgent(build_disclaimer(GuardrailVerdict.EMERGENCY))
    )
    app.dependency_overrides[get_current_device_id] = lambda: "dev-a"
    app.dependency_overrides[get_health_session_repo] = lambda: repo
    app.dependency_overrides[get_personal_assistant_agent_factory] = lambda: factory

    client = TestClient(app)
    response = client.post(
        f"/api/v1/health-chat/sessions/{session.id}/messages",
        json={"content": "가슴이 너무 아프고 숨이 막혀"},
    )

    assert response.status_code == 200
    body = response.json()
    ai_content = body["ai_message"]["content"]
    assert ai_content == build_disclaimer(GuardrailVerdict.EMERGENCY)
    assert "119" in ai_content
    assert "응급실" in ai_content
    assert "GuardrailVerdict" not in ai_content
    assert "blocked_response" not in ai_content
    assert "search_health_records" not in ai_content
    assert body["user_message"]["content"] == "가슴이 너무 아프고 숨이 막혀"
