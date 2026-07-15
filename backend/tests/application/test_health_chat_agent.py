from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

from app.application.service.health_ai_service import HealthAiService
from app.application.usecase.health_chat_agent import HealthChatAgent
from app.domain.model.health_chunk import HealthChunk
from app.domain.model.health_message import HealthMessage


class _FakeHealthAi(HealthAiService):
    def __init__(self, reply: str = "health reply") -> None:
        self.reply = reply
        self.chat_calls: list[dict] = []

    async def chat(
        self,
        messages: list[HealthMessage],
        health_context: list[str] | None = None,
    ) -> str:
        self.chat_calls.append({"messages": messages, "health_context": health_context})
        return self.reply


class _FakeHealthQuery:
    def __init__(self, chunks: list[HealthChunk]) -> None:
        self.chunks = chunks
        self.calls: list[dict] = []

    async def search_similar(
        self,
        device_id: str,
        query: str,
        limit: int = 5,
    ) -> list[HealthChunk]:
        self.calls.append({"device_id": device_id, "query": query, "limit": limit})
        return self.chunks


def _message(content: str) -> HealthMessage:
    return HealthMessage(role="user", content=content, created_at=datetime.now())


def _health_chunk(text: str) -> HealthChunk:
    return HealthChunk(
        device_id="dev-a",
        record_date=date(2026, 7, 10),
        text=text,
        embedding=[0.1, 0.2],
        data_types=["steps"],
    )


async def test_health_chat_agent_retrieves_health_data_and_returns_ai_reply():
    ai = _FakeHealthAi(reply="health data reply")
    health_query = _FakeHealthQuery([_health_chunk("9,144걸음을 걸었어.")])
    agent = HealthChatAgent(ai, health_query)
    messages = [_message("어제 몇 걸음 걸었어?")]

    response = await agent.run(
        device_id="dev-a",
        session_id=uuid4(),
        messages=messages,
        current_user_message="어제 몇 걸음 걸었어?",
    )

    assert response == "health data reply"
    assert health_query.calls == [
        {"device_id": "dev-a", "query": "어제 몇 걸음 걸었어?", "limit": 5}
    ]
    assert ai.chat_calls == [
        {
            "messages": messages,
            "health_context": ["- 2026-07-10: 9,144걸음을 걸었어."],
        }
    ]


async def test_health_chat_agent_passes_no_context_when_search_returns_empty():
    ai = _FakeHealthAi(reply="no health data reply")
    health_query = _FakeHealthQuery([])
    agent = HealthChatAgent(ai, health_query)
    messages = [_message("오늘 운동 기록 있어?")]

    response = await agent.run(
        device_id="dev-a",
        session_id=uuid4(),
        messages=messages,
        current_user_message="오늘 운동 기록 있어?",
    )

    assert response == "no health data reply"
    assert health_query.calls == [
        {"device_id": "dev-a", "query": "오늘 운동 기록 있어?", "limit": 5}
    ]
    assert ai.chat_calls == [{"messages": messages, "health_context": None}]
