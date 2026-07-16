import asyncio
from collections.abc import Sequence
from enum import StrEnum
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.application.service.coaching_prompt import build_coaching_system_prompt
from app.application.service.diary_chat_prompt import (
    DiaryConversationContext,
    build_diary_chat_system_prompt,
)
from app.application.service.health_chat_prompt import build_health_chat_system_prompt
from app.application.service.personal_assistant_timeout import (
    DEFAULT_PERSONAL_ASSISTANT_TIMEOUT_POLICY,
    PersonalAssistantTimeoutError,
    PersonalAssistantTimeoutPolicy,
)
from app.application.service.tool_calling_chat_model import ToolCallingChatModel
from app.domain.service.medical_guardrail import (
    GuardrailVerdict,
    build_disclaimer,
    classify_medical_request,
    contains_prescriptive_content,
)

DEFAULT_MAX_TOOL_ROUNDS = 3
ITERATION_LIMIT_MESSAGE = (
    "요청을 처리하는 과정에서 도구 호출이 반복되어 현재 요청을 완료하지 못했어요. "
    "질문을 더 구체적으로 다시 요청해 주세요."
)


class PersonalAssistantMode(StrEnum):
    DIARY = "diary"
    HEALTH = "health"
    COACHING = "coaching"


class CoachingConversationContext(TypedDict):
    persona: str | None


class PersonalAssistantState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    mode: PersonalAssistantMode
    diary_context: DiaryConversationContext | None
    coaching_context: CoachingConversationContext | None
    llm_calls: int
    tool_rounds: int
    guardrail_verdict: GuardrailVerdict


def build_personal_assistant_system_message(
    mode: PersonalAssistantMode,
    diary_context: DiaryConversationContext | None = None,
    coaching_context: CoachingConversationContext | None = None,
) -> SystemMessage:
    match mode:
        case PersonalAssistantMode.DIARY:
            if diary_context is None:
                raise ValueError("diary_context is required for diary mode")
            if coaching_context is not None:
                raise ValueError("coaching_context is only supported for coaching mode")
            return SystemMessage(
                content=build_diary_chat_system_prompt(
                    max_turns=diary_context.max_turns,
                    current_user_turn=diary_context.current_user_turn,
                    suggest_finalize=diary_context.suggest_finalize,
                    tool_calling_enabled=True,
                )
            )
        case PersonalAssistantMode.HEALTH:
            if diary_context is not None:
                raise ValueError("diary_context is only supported for diary mode")
            if coaching_context is not None:
                raise ValueError("coaching_context is only supported for coaching mode")
            return SystemMessage(
                content=build_health_chat_system_prompt(
                    tool_calling_enabled=True,
                    health_context=None,
                )
            )
        case PersonalAssistantMode.COACHING:
            if diary_context is not None:
                raise ValueError("diary_context is only supported for diary mode")
            return SystemMessage(
                content=build_coaching_system_prompt(
                    persona=coaching_context.get("persona") if coaching_context else None
                )
            )


class PersonalAssistantAgent:
    def __init__(
        self,
        model: ToolCallingChatModel,
        tools: Sequence[BaseTool],
        *,
        max_tool_rounds: int = DEFAULT_MAX_TOOL_ROUNDS,
        timeout_policy: PersonalAssistantTimeoutPolicy = DEFAULT_PERSONAL_ASSISTANT_TIMEOUT_POLICY,
    ) -> None:
        if max_tool_rounds < 1:
            raise ValueError("max_tool_rounds must be at least 1")

        tool_names = [tool.name for tool in tools]
        duplicate_names = sorted({name for name in tool_names if tool_names.count(name) > 1})
        if duplicate_names:
            raise ValueError(f"duplicate tool names are not allowed: {', '.join(duplicate_names)}")

        self._model = model
        self._tools = tuple(tools)
        self._max_tool_rounds = max_tool_rounds
        self._timeout_policy = timeout_policy
        self._tool_node = ToolNode(self._tools, handle_tool_errors=False)
        self._graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(PersonalAssistantState)

        builder.add_node("input_guardrail", self._input_guardrail_node)
        builder.add_node("blocked_response", self._blocked_response_node)
        builder.add_node("agent", self._agent_node)
        builder.add_node("tools", self._tools_node)
        builder.add_node("output_guardrail", self._output_guardrail_node)
        builder.add_node("iteration_limit", self._iteration_limit_node)

        builder.add_edge(START, "input_guardrail")
        builder.add_conditional_edges(
            "input_guardrail",
            self._route_after_input_guardrail,
            {
                "agent": "agent",
                "blocked_response": "blocked_response",
            },
        )
        builder.add_edge("blocked_response", END)
        builder.add_conditional_edges(
            "agent",
            self._route_after_agent,
            {
                "tools": "tools",
                "iteration_limit": "iteration_limit",
                "output_guardrail": "output_guardrail",
            },
        )
        builder.add_edge("tools", "agent")
        builder.add_edge("output_guardrail", END)
        builder.add_edge("iteration_limit", END)

        return builder.compile()

    def _input_guardrail_node(self, state: PersonalAssistantState) -> dict:
        if state["mode"] == PersonalAssistantMode.DIARY:
            return {"guardrail_verdict": GuardrailVerdict.SAFE}

        latest_user_text = find_latest_human_message_text(state["messages"])
        return {
            "guardrail_verdict": classify_medical_request(latest_user_text),
        }

    def _route_after_input_guardrail(
        self,
        state: PersonalAssistantState,
    ) -> Literal["agent", "blocked_response"]:
        if state["guardrail_verdict"] == GuardrailVerdict.SAFE:
            return "agent"
        return "blocked_response"

    def _blocked_response_node(self, state: PersonalAssistantState) -> dict:
        verdict = state["guardrail_verdict"]
        if verdict == GuardrailVerdict.SAFE:
            raise RuntimeError("blocked_response requires unsafe guardrail verdict")

        content = build_disclaimer(verdict)
        if not content:
            raise RuntimeError("blocked_response produced empty disclaimer")
        return {"messages": [AIMessage(content=content, id="guardrail-blocked-response")]}

    async def _agent_node(self, state: PersonalAssistantState) -> dict:
        llm_calls = state.get("llm_calls", 0) + 1
        try:
            async with asyncio.timeout(self._timeout_policy.model_call_seconds):
                response = await self._model.ainvoke(
                    messages=[
                        build_personal_assistant_system_message(
                            state["mode"],
                            state.get("diary_context"),
                            state.get("coaching_context"),
                        ),
                        *state["messages"],
                    ],
                    tools=self._tools,
                )
        except TimeoutError as exc:
            raise PersonalAssistantTimeoutError("model") from exc
        _ensure_ai_message_id(response, f"agent-response-{llm_calls}")
        return {
            "messages": [response],
            "llm_calls": llm_calls,
        }

    async def _tools_node(
        self,
        state: PersonalAssistantState,
        config: RunnableConfig,
    ) -> dict:
        try:
            async with asyncio.timeout(self._timeout_policy.tool_round_seconds):
                result = await self._tool_node.ainvoke(state, config=config)
        except TimeoutError as exc:
            raise PersonalAssistantTimeoutError("tool") from exc
        return {
            "messages": result["messages"],
            "tool_rounds": state.get("tool_rounds", 0) + 1,
        }

    async def _iteration_limit_node(self, state: PersonalAssistantState) -> dict:
        return {"messages": [AIMessage(content=ITERATION_LIMIT_MESSAGE)]}

    def _output_guardrail_node(self, state: PersonalAssistantState) -> dict:
        if state["mode"] == PersonalAssistantMode.DIARY:
            return {}

        last_message = state["messages"][-1]
        if not isinstance(last_message, AIMessage) or last_message.tool_calls:
            raise RuntimeError("output_guardrail requires final AIMessage")

        if not contains_prescriptive_content(_ai_message_text(last_message)):
            return {}

        content = build_disclaimer(GuardrailVerdict.ADVICE_BOUNDARY)
        if not content:
            raise RuntimeError("output_guardrail produced empty disclaimer")

        return {
            "messages": [
                AIMessage(
                    content=content,
                    id=last_message.id,
                )
            ],
            "guardrail_verdict": GuardrailVerdict.ADVICE_BOUNDARY,
        }

    def _route_after_agent(
        self,
        state: PersonalAssistantState,
    ) -> Literal["tools", "iteration_limit", "output_guardrail"]:
        last_message = state["messages"][-1]
        if not isinstance(last_message, AIMessage):
            raise RuntimeError("agent node must append AIMessage")
        if not last_message.tool_calls:
            return "output_guardrail"
        if state.get("tool_rounds", 0) >= self._max_tool_rounds:
            return "iteration_limit"
        return "tools"

    async def _ainvoke_state(
        self,
        *,
        messages: Sequence[BaseMessage],
        mode: PersonalAssistantMode,
        diary_context: DiaryConversationContext | None = None,
        coaching_context: CoachingConversationContext | None = None,
    ) -> PersonalAssistantState:
        _validate_context_for_mode(mode, diary_context, coaching_context)
        initial_state: PersonalAssistantState = {
            "messages": list(messages),
            "mode": mode,
            "diary_context": diary_context,
            "coaching_context": coaching_context,
            "llm_calls": 0,
            "tool_rounds": 0,
            "guardrail_verdict": GuardrailVerdict.ADVICE_BOUNDARY,
        }
        recursion_limit = self._max_tool_rounds * 2 + 5
        return await self._graph.ainvoke(
            initial_state,
            config={"recursion_limit": recursion_limit},
        )

    async def run(
        self,
        *,
        messages: Sequence[BaseMessage],
        mode: PersonalAssistantMode,
        diary_context: DiaryConversationContext | None = None,
        coaching_context: CoachingConversationContext | None = None,
    ) -> AIMessage:
        try:
            async with asyncio.timeout(self._timeout_policy.execution_seconds):
                result = await self._ainvoke_state(
                    messages=messages,
                    mode=mode,
                    diary_context=diary_context,
                    coaching_context=coaching_context,
                )
        except TimeoutError as exc:
            raise PersonalAssistantTimeoutError("execution") from exc
        for message in reversed(result["messages"]):
            if isinstance(message, AIMessage):
                if message.tool_calls:
                    break
                return message
        raise RuntimeError("personal assistant graph did not produce final AIMessage")


def _validate_context_for_mode(
    mode: PersonalAssistantMode,
    diary_context: DiaryConversationContext | None,
    coaching_context: CoachingConversationContext | None,
) -> None:
    if mode == PersonalAssistantMode.DIARY and diary_context is None:
        raise ValueError("diary_context is required for diary mode")
    if mode != PersonalAssistantMode.DIARY and diary_context is not None:
        raise ValueError("diary_context is only supported for diary mode")
    if mode != PersonalAssistantMode.COACHING and coaching_context is not None:
        raise ValueError("coaching_context is only supported for coaching mode")


def find_latest_human_message_text(messages: Sequence[BaseMessage]) -> str:
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return _message_content_text(message)
    raise ValueError("guarded modes require at least one HumanMessage")


def _message_content_text(message: BaseMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(_content_block_text(block) for block in content)
    raise ValueError("unsupported message content type")


def _ai_message_text(message: AIMessage) -> str:
    return _message_content_text(message)


def _content_block_text(block: str | dict) -> str:
    if isinstance(block, str):
        return block
    if isinstance(block, dict) and block.get("type") == "text":
        text = block.get("text")
        if isinstance(text, str):
            return text
    raise ValueError("unsupported message content block")


def _ensure_ai_message_id(message: AIMessage, default_id: str) -> None:
    if message.id is None:
        message.id = default_id
