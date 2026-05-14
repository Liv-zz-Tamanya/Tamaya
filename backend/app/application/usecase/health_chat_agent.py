from typing import TypedDict
from uuid import UUID

from langgraph.graph import END, START, StateGraph

from app.application.service.embedding_service import EmbeddingService
from app.application.service.health_ai_service import HealthAiService
from app.domain.model.health_message import HealthMessage
from app.domain.repository.health_chunk_repository import HealthChunkRepository


class HealthChatAgentState(TypedDict):
    session_id: UUID
    messages: list[HealthMessage]
    current_user_message: str
    retrieved_health_data: list[str]
    response: str


class HealthChatAgent:
    def __init__(
        self,
        ai: HealthAiService,
        embedding_service: EmbeddingService,
        health_chunk_repo: HealthChunkRepository,
    ) -> None:
        self._ai = ai
        self._embedding_service = embedding_service
        self._health_chunk_repo = health_chunk_repo
        self._graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(HealthChatAgentState)

        builder.add_node("retrieve_node", self._retrieve_node)
        builder.add_node("chat_node", self._chat_node)

        builder.add_edge(START, "retrieve_node")
        builder.add_edge("retrieve_node", "chat_node")
        builder.add_edge("chat_node", END)

        return builder.compile()

    async def _retrieve_node(self, state: HealthChatAgentState) -> dict:
        query_embedding = self._embedding_service.embed([state["current_user_message"]])[0]
        chunks = await self._health_chunk_repo.search_similar(
            embedding=query_embedding,
            limit=5,
        )
        context = [
            f"- {chunk.record_date.strftime('%Y-%m-%d')}: {chunk.text}"
            for chunk in chunks
        ]
        return {"retrieved_health_data": context}

    async def _chat_node(self, state: HealthChatAgentState) -> dict:
        response = await self._ai.chat(
            messages=state["messages"],
            health_context=state["retrieved_health_data"] or None,
        )
        return {"response": response}

    async def run(
        self,
        session_id: UUID,
        messages: list[HealthMessage],
        current_user_message: str,
    ) -> str:
        initial_state: HealthChatAgentState = {
            "session_id": session_id,
            "messages": messages,
            "current_user_message": current_user_message,
            "retrieved_health_data": [],
            "response": "",
        }
        result = await self._graph.ainvoke(initial_state)
        return result["response"]
