from __future__ import annotations

import math
from datetime import date
from uuid import UUID, uuid4

import pytest

from app.application.service.embedding_service import EmbeddingService
from app.application.service.health_ai_service import HealthAiService
from app.application.usecase.health_chat_agent import HealthChatAgent
from app.application.usecase.send_health_message import SendHealthMessageUseCase
from app.domain.model.health_chunk import HealthChunk
from app.domain.model.health_message import HealthMessage
from app.domain.model.health_session import HealthSession
from app.domain.repository.health_chunk_repository import HealthChunkRepository
from app.domain.repository.health_session_repository import HealthSessionRepository


class _MemoryHealthSessionRepo(HealthSessionRepository):
    def __init__(self) -> None:
        self.sessions: dict[UUID, HealthSession] = {}

    async def save(self, session: HealthSession) -> HealthSession:
        existing = self.sessions.get(session.id)
        if existing and existing.device_id != session.device_id:
            raise ValueError("세션 소유자가 일치하지 않습니다.")
        self.sessions[session.id] = session
        return session

    async def find_by_id(self, session_id: UUID, device_id: str) -> HealthSession | None:
        session = self.sessions.get(session_id)
        if session is None or session.device_id != device_id:
            return None
        return session


class _FakeHealthAi(HealthAiService):
    def __init__(self) -> None:
        self.last_context: list[str] | None = None

    async def chat(
        self,
        messages: list[HealthMessage],
        health_context: list[str] | None = None,
    ) -> str:
        self.last_context = health_context
        return "건강 응답"


class _FakeEmbedding(EmbeddingService):
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0]]


class _MemoryHealthChunkRepo(HealthChunkRepository):
    def __init__(self, chunks: list[HealthChunk]) -> None:
        self.chunks = chunks
        self.calls: list[str] = []

    async def save_all(self, chunks: list[HealthChunk]) -> None:
        self.chunks.extend(chunks)

    async def search_similar(
        self,
        device_id: str,
        embedding: list[float],
        limit: int = 5,
    ) -> list[HealthChunk]:
        self.calls.append(device_id)
        scoped = [chunk for chunk in self.chunks if chunk.device_id == device_id]
        return sorted(scoped, key=lambda chunk: _cosine_distance(chunk.embedding, embedding))[
            :limit
        ]

    async def find_by_date(self, device_id: str, record_date: date) -> list[HealthChunk]:
        return [
            chunk
            for chunk in self.chunks
            if chunk.device_id == device_id and chunk.record_date == record_date
        ]

    async def exists_for_date(self, device_id: str, record_date: date) -> bool:
        return bool(await self.find_by_date(device_id, record_date))


def _cosine_distance(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    return 1 - dot / (left_norm * right_norm)


def _chunk(device_id: str, text: str, embedding: list[float]) -> HealthChunk:
    return HealthChunk(
        device_id=device_id,
        record_date=date(2026, 7, 10),
        text=text,
        embedding=embedding,
        data_types=["steps"],
    )


@pytest.mark.asyncio
async def test_send_health_message_hides_other_device_session_and_does_not_mutate_it():
    repo = _MemoryHealthSessionRepo()
    other_session = HealthSession(device_id="dev-b")
    other_session.add_message("assistant", "B의 시작")
    await repo.save(other_session)
    agent = HealthChatAgent(_FakeHealthAi(), _FakeEmbedding(), _MemoryHealthChunkRepo([]))
    usecase = SendHealthMessageUseCase(repo, agent)

    with pytest.raises(ValueError, match="세션을 찾을 수 없습니다."):
        await usecase.execute(other_session.id, "메시지", "dev-a")

    assert [message.content for message in other_session.messages] == ["B의 시작"]


@pytest.mark.asyncio
async def test_health_agent_excludes_other_device_chunk_even_when_more_similar():
    repo = _MemoryHealthChunkRepo(
        [
            _chunk("dev-a", "A 사용자의 걸음 기록", [0.8, 0.2]),
            _chunk("dev-b", "B 사용자의 더 가까운 기록", [1.0, 0.0]),
        ]
    )
    ai = _FakeHealthAi()
    agent = HealthChatAgent(ai, _FakeEmbedding(), repo)

    await agent.run(
        device_id="dev-a",
        session_id=uuid4(),
        messages=[],
        current_user_message="걸음 수 알려줘",
    )

    assert ai.last_context == ["- 2026-07-10: A 사용자의 걸음 기록"]
    assert repo.calls == ["dev-a"]


@pytest.mark.asyncio
async def test_health_agent_uses_empty_context_when_current_device_has_no_chunks():
    repo = _MemoryHealthChunkRepo([_chunk("dev-b", "B 사용자의 기록", [1.0, 0.0])])
    ai = _FakeHealthAi()
    agent = HealthChatAgent(ai, _FakeEmbedding(), repo)

    await agent.run(
        device_id="dev-a",
        session_id=uuid4(),
        messages=[],
        current_user_message="내 건강 데이터 알려줘",
    )

    assert ai.last_context is None
