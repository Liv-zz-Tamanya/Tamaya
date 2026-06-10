"""LangGraph 코칭 에이전트 — guardrail-first.

기존 ChatAgent StateGraph를 본떠, 의료 면책 가드레일을 코칭 생성보다 먼저 둔다.
위험 입력은 coach 호출 없이 면책으로 단락되고, 안전 입력만 코칭으로 흐른다.
coach 응답은 post-generation tripwire로 한 번 더 검사한다(이중 안전망).
"""

from typing import TypedDict
from uuid import UUID

from langgraph.graph import END, START, StateGraph

from app.application.service.coaching_ai_service import CoachingAiService
from app.domain.model.chat_message import ChatMessage
from app.domain.service.medical_guardrail import (
    GuardrailVerdict,
    build_disclaimer,
    classify_medical_request,
    contains_prescriptive_content,
)


class CoachingAgentState(TypedDict):
    session_id: UUID
    messages: list[ChatMessage]
    current_user_message: str
    persona: str | None
    verdict: GuardrailVerdict
    response: str


class CoachingAgent:
    def __init__(self, ai: CoachingAiService) -> None:
        self._ai = ai
        self._graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(CoachingAgentState)
        builder.add_node("guardrail_node", self._guardrail_node)
        builder.add_node("disclaimer_node", self._disclaimer_node)
        builder.add_node("coach_node", self._coach_node)

        builder.add_edge(START, "guardrail_node")
        builder.add_conditional_edges(
            "guardrail_node",
            lambda state: (
                "coach_node" if state["verdict"] == GuardrailVerdict.SAFE else "disclaimer_node"
            ),
        )
        builder.add_edge("disclaimer_node", END)
        builder.add_edge("coach_node", END)
        return builder.compile()

    async def _guardrail_node(self, state: CoachingAgentState) -> dict:
        return {"verdict": classify_medical_request(state["current_user_message"])}

    async def _disclaimer_node(self, state: CoachingAgentState) -> dict:
        return {"response": build_disclaimer(state["verdict"])}

    async def _coach_node(self, state: CoachingAgentState) -> dict:
        reply = await self._ai.coach(state["messages"], state.get("persona"))
        # post-generation tripwire: 처방성 응답이면 결정론 면책으로 치환
        if contains_prescriptive_content(reply):
            reply = build_disclaimer(GuardrailVerdict.ADVICE_BOUNDARY)
        return {"response": reply}

    async def run(
        self,
        session_id: UUID,
        messages: list[ChatMessage],
        current_user_message: str,
        persona: str | None = None,
    ) -> str:
        initial_state: CoachingAgentState = {
            "session_id": session_id,
            "messages": messages,
            "current_user_message": current_user_message,
            "persona": persona,
            # fail-closed: guardrail_node가 항상 덮어쓰지만, 그래프 오설정 시
            # coach로 새지 않도록 기본값을 안전(면책)으로 둔다.
            "verdict": GuardrailVerdict.ADVICE_BOUNDARY,
            "response": "",
        }
        result = await self._graph.ainvoke(initial_state)
        return result["response"]
