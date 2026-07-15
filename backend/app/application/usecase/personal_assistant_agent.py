from collections.abc import Sequence
from enum import StrEnum
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.application.service.tool_calling_chat_model import ToolCallingChatModel

DEFAULT_MAX_TOOL_ROUNDS = 3
ITERATION_LIMIT_MESSAGE = (
    "요청을 처리하는 과정에서 도구 호출이 반복되어 현재 요청을 완료하지 못했어요. "
    "질문을 더 구체적으로 다시 요청해 주세요."
)

COMMON_SYSTEM_PROMPT = """
개인의 과거 일기나 건강 기록에 관한 질문은 추측하지 말고 필요한 경우 적절한 도구를 사용한다.
도구 결과에 없는 사실, 날짜, 인물, 장소, 수치를 만들어내지 않는다.
검색 결과가 없으면 기록을 찾지 못했다고 명확히 답한다.
같은 인자로 동일한 도구를 반복 호출하지 않는다.
사용자의 질문에 필요한 최소한의 도구만 호출한다.
도구 결과를 최종 답변에 자연스럽게 반영한다.
도구 이름, 내부 ID, JSON 원문은 사용자에게 불필요하게 노출하지 않는다.
""".strip()

DIARY_SYSTEM_PROMPT = f"""
{COMMON_SYSTEM_PROMPT}

너는 사용자의 회고와 일기 대화를 돕는 개인 비서다.
과거 사건, 감정, 인물, 장소에 대한 질문에는 일기 기억 도구를 사용한다.
건강 기록 질문은 건강 도구가 필요한 경우에만 사용한다.
일반적인 감정 대화에는 도구 호출을 강제하지 않는다.
""".strip()

HEALTH_SYSTEM_PROMPT = f"""
{COMMON_SYSTEM_PROMPT}

너는 사용자의 저장된 건강 기록에 근거하여 답하는 개인 비서다.
건강 데이터가 필요한 질문에는 건강 기록 도구를 사용한다.
검색 결과에 없는 수치나 상태를 추측하지 않는다.
진단, 처방, 약물 변경을 단정적으로 제시하지 않는다.
현재 응급 의료 가드레일을 완전히 대체하지 않는다.
""".strip()


class PersonalAssistantMode(StrEnum):
    DIARY = "diary"
    HEALTH = "health"


class PersonalAssistantState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    mode: PersonalAssistantMode
    llm_calls: int
    tool_rounds: int


def build_personal_assistant_system_message(mode: PersonalAssistantMode) -> SystemMessage:
    match mode:
        case PersonalAssistantMode.DIARY:
            return SystemMessage(content=DIARY_SYSTEM_PROMPT)
        case PersonalAssistantMode.HEALTH:
            return SystemMessage(content=HEALTH_SYSTEM_PROMPT)


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
                build_personal_assistant_system_message(state["mode"]),
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
    ) -> PersonalAssistantState:
        initial_state: PersonalAssistantState = {
            "messages": list(messages),
            "mode": mode,
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
    ) -> AIMessage:
        result = await self._ainvoke_state(messages=messages, mode=mode)
        for message in reversed(result["messages"]):
            if isinstance(message, AIMessage):
                if message.tool_calls:
                    break
                return message
        raise RuntimeError("personal assistant graph did not produce final AIMessage")
