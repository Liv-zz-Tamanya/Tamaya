from collections.abc import Sequence
from enum import StrEnum
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.application.service.diary_chat_prompt import (
    DiaryConversationContext,
    build_diary_chat_system_prompt,
)
from app.application.service.health_chat_prompt import build_health_chat_system_prompt
from app.application.service.tool_calling_chat_model import ToolCallingChatModel

DEFAULT_MAX_TOOL_ROUNDS = 3
ITERATION_LIMIT_MESSAGE = (
    "요청을 처리하는 과정에서 도구 호출이 반복되어 현재 요청을 완료하지 못했어요. "
    "질문을 더 구체적으로 다시 요청해 주세요."
)


class PersonalAssistantMode(StrEnum):
    DIARY = "diary"
    HEALTH = "health"


class PersonalAssistantState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    mode: PersonalAssistantMode
    diary_context: DiaryConversationContext | None
    llm_calls: int
    tool_rounds: int


def build_personal_assistant_system_message(
    mode: PersonalAssistantMode,
    diary_context: DiaryConversationContext | None = None,
) -> SystemMessage:
    match mode:
        case PersonalAssistantMode.DIARY:
            if diary_context is None:
                raise ValueError("diary_context is required for diary mode")
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
            return SystemMessage(
                content=build_health_chat_system_prompt(
                    tool_calling_enabled=True,
                    health_context=None,
                )
            )


class PersonalAssistantAgent:
    def __init__(
        self,
        model: ToolCallingChatModel,
        tools: Sequence[BaseTool],
        *,
        max_tool_rounds: int = DEFAULT_MAX_TOOL_ROUNDS,
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
        self._tool_node = ToolNode(self._tools, handle_tool_errors=False)
        self._graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(PersonalAssistantState)

        builder.add_node("agent", self._agent_node)
        builder.add_node("tools", self._tools_node)
        builder.add_node("iteration_limit", self._iteration_limit_node)

        builder.add_edge(START, "agent")
        builder.add_conditional_edges(
            "agent",
            self._route_after_agent,
            {
                "tools": "tools",
                "iteration_limit": "iteration_limit",
                END: END,
            },
        )
        builder.add_edge("tools", "agent")
        builder.add_edge("iteration_limit", END)

        return builder.compile()

    async def _agent_node(self, state: PersonalAssistantState) -> dict:
        response = await self._model.ainvoke(
            messages=[
                build_personal_assistant_system_message(
                    state["mode"],
                    state.get("diary_context"),
                ),
                *state["messages"],
            ],
            tools=self._tools,
        )
        return {
            "messages": [response],
            "llm_calls": state.get("llm_calls", 0) + 1,
        }

    async def _tools_node(
        self,
        state: PersonalAssistantState,
        config: RunnableConfig,
    ) -> dict:
        result = await self._tool_node.ainvoke(state, config=config)
        return {
            "messages": result["messages"],
            "tool_rounds": state.get("tool_rounds", 0) + 1,
        }

    async def _iteration_limit_node(self, state: PersonalAssistantState) -> dict:
        return {"messages": [AIMessage(content=ITERATION_LIMIT_MESSAGE)]}

    def _route_after_agent(
        self,
        state: PersonalAssistantState,
    ) -> Literal["tools", "iteration_limit", "__end__"]:
        last_message = state["messages"][-1]
        if not isinstance(last_message, AIMessage):
            raise RuntimeError("agent node must append AIMessage")
        if not last_message.tool_calls:
            return END
        if state.get("tool_rounds", 0) >= self._max_tool_rounds:
            return "iteration_limit"
        return "tools"

    async def _ainvoke_state(
        self,
        *,
        messages: Sequence[BaseMessage],
        mode: PersonalAssistantMode,
        diary_context: DiaryConversationContext | None = None,
    ) -> PersonalAssistantState:
        _validate_context_for_mode(mode, diary_context)
        initial_state: PersonalAssistantState = {
            "messages": list(messages),
            "mode": mode,
            "diary_context": diary_context,
            "llm_calls": 0,
            "tool_rounds": 0,
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
    ) -> AIMessage:
        result = await self._ainvoke_state(
            messages=messages,
            mode=mode,
            diary_context=diary_context,
        )
        for message in reversed(result["messages"]):
            if isinstance(message, AIMessage):
                if message.tool_calls:
                    break
                return message
        raise RuntimeError("personal assistant graph did not produce final AIMessage")


def _validate_context_for_mode(
    mode: PersonalAssistantMode,
    diary_context: DiaryConversationContext | None,
) -> None:
    if mode == PersonalAssistantMode.DIARY and diary_context is None:
        raise ValueError("diary_context is required for diary mode")
    if mode == PersonalAssistantMode.HEALTH and diary_context is not None:
        raise ValueError("diary_context is only supported for diary mode")
