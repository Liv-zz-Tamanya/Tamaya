from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.application.service.health_ai_service import HealthAiService
from app.domain.model.health_message import HealthMessage
from app.domain.model.health_session import HealthSession
from app.domain.repository.health_session_repository import HealthSessionRepository
from app.infrastructure.config.dependencies import (
    get_health_ai_service,
    get_health_chat_agent,
    get_health_session_repo,
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


class _FakeHealthAgent:
    async def run(
        self,
        device_id: str,
        session_id: UUID,
        messages: list[HealthMessage],
        current_user_message: str,
    ) -> str:
        return f"{device_id} 건강 응답"


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_health_chat_session_requires_authentication():
    client = TestClient(app)

    response = client.post("/api/v1/health-chat/sessions")

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
    app.dependency_overrides[get_health_chat_agent] = _FakeHealthAgent

    client = TestClient(app)
    get_response = client.get(f"/api/v1/health-chat/sessions/{other_session.id}")
    send_response = client.post(
        f"/api/v1/health-chat/sessions/{other_session.id}/messages",
        json={"content": "내 메시지"},
    )

    assert get_response.status_code == 404
    assert send_response.status_code == 404
    assert [message.content for message in other_session.messages] == ["B 세션"]
