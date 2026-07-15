from typing import TypedDict
from uuid import UUID

from langgraph.graph import END, START, StateGraph

from app.application.service.ai_chat_service import AiChatService
from app.application.service.diary_memory_query_service import DiaryMemoryQueryService
from app.domain.model.chat_message import ChatMessage


class ChatAgentState(TypedDict):
    device_id: str
    session_id: UUID
    messages: list[ChatMessage]
    current_user_message: str
    suggest_finalize: bool
    max_turns: int
    retrieved_memories: list[str]
    response: str
    should_retrieve: bool


class ChatAgent:
    def __init__(
        self,
        ai: AiChatService,
        memory_query: DiaryMemoryQueryService,
    ) -> None:
        self._ai = ai
        self._memory_query = memory_query
        self._graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(ChatAgentState)

        builder.add_node("route_node", self._route_node)
        builder.add_node("retrieve_memory_node", self._retrieve_memory_node)
        builder.add_node("chat_node", self._chat_node)

        builder.add_edge(START, "route_node")
        builder.add_conditional_edges(
            "route_node",
            lambda state: "retrieve_memory_node" if state["should_retrieve"] else "chat_node",
        )
        builder.add_edge("retrieve_memory_node", "chat_node")
        builder.add_edge("chat_node", END)

        return builder.compile()

    async def _route_node(self, state: ChatAgentState) -> dict:
        should_retrieve = await self._ai.classify_memory_need(state["current_user_message"])
        return {"should_retrieve": should_retrieve}

    async def _retrieve_memory_node(self, state: ChatAgentState) -> dict:
        chunks = await self._memory_query.search_similar(
            device_id=state["device_id"],
            limit=5,
            query=state["current_user_message"],
            exclude_session_id=state["session_id"],
        )
        memories = []
        for chunk in chunks:
            parts = [f"- {chunk.diary_date.strftime('%Y-%m-%d')}: {chunk.text}"]
            details = []
            if chunk.who:
                details.append(f"인물:{chunk.who}")
            if chunk.where:
                details.append(f"장소:{chunk.where}")
            if chunk.when:
                details.append(f"시간:{chunk.when}")
            if details:
                parts.append(f"({', '.join(details)})")
            if chunk.tags:
                parts.append(" ".join(f"#{t}" for t in chunk.tags))
            memories.append(" ".join(parts))
        return {"retrieved_memories": memories}

    async def _chat_node(self, state: ChatAgentState) -> dict:
        memories = state.get("retrieved_memories") or []
        response = await self._ai.chat(
            messages=state["messages"],
            suggest_finalize=state["suggest_finalize"],
            memories=memories if memories else None,
            max_turns=state["max_turns"],
        )
        return {"response": response}

    async def run(
        self,
        device_id: str,
        session_id: UUID,
        messages: list[ChatMessage],
        current_user_message: str,
        suggest_finalize: bool = False,
        max_turns: int = 5,
    ) -> str:
        initial_state: ChatAgentState = {
            "device_id": device_id,
            "session_id": session_id,
            "messages": messages,
            "current_user_message": current_user_message,
            "suggest_finalize": suggest_finalize,
            "max_turns": max_turns,
            "retrieved_memories": [],
            "response": "",
            "should_retrieve": False,
        }
        result = await self._graph.ainvoke(initial_state)
        return result["response"]
