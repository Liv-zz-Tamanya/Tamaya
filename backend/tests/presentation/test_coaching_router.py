"""코칭 라우터 — 수직 슬라이스 (G004-1, TDD).

TestClient + dependency_overrides(fake CoachingAiService)로 실 CLOVA 없이
HTTP→usecase→guardrail-first agent 경로를 검증한다.
"""

import pytest
from fastapi.testclient import TestClient

from app.application.service.coaching_ai_service import CoachingAiService
from app.domain.model.chat_message import ChatMessage
from app.infrastructure.config.dependencies import get_coaching_ai_service
from app.main import app


class _FakeCoachAi(CoachingAiService):
    async def coach(self, messages: list[ChatMessage], persona: str | None = None) -> str:
        return "오늘 하루도 고생 많았어요"


@pytest.fixture(autouse=True)
def _override():
    app.dependency_overrides[get_coaching_ai_service] = _FakeCoachAi
    yield
    app.dependency_overrides.clear()


def test_safe_coaching_message_returns_reply():
    client = TestClient(app)
    resp = client.post(
        "/api/v1/coaching/messages",
        json={"device_id": "dev-1", "message": "오늘 너무 지쳤어", "history": []},
    )
    assert resp.status_code == 200
    assert resp.json()["reply"] == "오늘 하루도 고생 많았어요"


def test_risky_coaching_message_returns_disclaimer():
    client = TestClient(app)
    resp = client.post(
        "/api/v1/coaching/messages",
        json={"device_id": "dev-1", "message": "이 약 먹어도 돼?", "history": []},
    )
    assert resp.status_code == 200
    assert "전문가" in resp.json()["reply"]


def test_history_accepted_and_reply_returned():
    client = TestClient(app)
    resp = client.post(
        "/api/v1/coaching/messages",
        json={
            "device_id": "dev-1",
            "message": "그렇구나",
            "history": [
                {"role": "user", "content": "안녕"},
                {"role": "assistant", "content": "안녕!"},
            ],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["reply"] != ""
