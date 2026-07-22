import asyncio
import logging
import time
from collections.abc import Sequence
from enum import StrEnum
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.application.service.agent_execution_observability import (
    AgentExecutionRecorder,
    AgentExecutionTrace,
    AgentTerminationReason,
    AgentTraceDetail,
    NullAgentExecutionRecorder,
    ToolCallTraceRecord,
    activate_agent_execution_trace,
    get_active_agent_execution_trace,
    reset_agent_execution_trace,
)
from app.application.service.coaching_prompt import build_coaching_system_prompt
from app.application.service.diary_chat_prompt import (
    DiaryConversationContext,
    build_diary_chat_system_prompt,
)
from app.application.service.health_chat_prompt import build_health_chat_system_prompt
from app.application.service.model_provider_error import ModelProviderError
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
logger = logging.getLogger(__name__)
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
        execution_recorder: AgentExecutionRecorder = NullAgentExecutionRecorder(),
        trace_detail: AgentTraceDetail = AgentTraceDetail.BASIC,
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
        self._execution_recorder = execution_recorder
        self._trace_detail = trace_detail
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
        verdict = classify_medical_request(latest_user_text)
        trace = get_active_agent_execution_trace()
        if trace is not None:
            trace.record_guardrail_verdict(verdict.value)
        return {
            "guardrail_verdict": verdict,
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
        trace = get_active_agent_execution_trace()
        if trace is not None:
            trace.termination_reason = AgentTerminationReason.INPUT_GUARDRAIL_BLOCKED
        return {"messages": [AIMessage(content=content, id="guardrail-blocked-response")]}

    async def _agent_node(self, state: PersonalAssistantState) -> dict:
        llm_calls = state.get("llm_calls", 0) + 1
        trace = get_active_agent_execution_trace()
        model_attempts_before = trace.llm_calls if trace is not None else 0
        started_at = time.monotonic()
        duration_seconds = 0.0
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
        finally:
            duration_seconds = time.monotonic() - started_at
            if trace is not None:
                trace.add_model_duration(duration_seconds)
                if trace.llm_calls == model_attempts_before:
                    trace.record_model_attempt()
        _ensure_ai_message_id(response, f"agent-response-{llm_calls}")
        if trace is not None:
            usage = _normalized_token_usage(response)
            trace.record_token_usage(usage)
            trace.record_llm_call(
                finish_reason=_finish_reason(response),
                response_content=_optional_ai_message_text(response),
                tool_calls=_tool_call_traces(response, state.get("tool_rounds", 0) + 1),
                usage=usage,
                duration_seconds=duration_seconds,
            )
        return {
            "messages": [response],
            "llm_calls": llm_calls,
        }

    async def _tools_node(
        self,
        state: PersonalAssistantState,
        config: RunnableConfig,
    ) -> dict:
        trace = get_active_agent_execution_trace()
        if trace is not None:
            trace.start_tool_round(_tool_names_from_state(state))
        started_at = time.monotonic()
        try:
            async with asyncio.timeout(self._timeout_policy.tool_round_seconds):
                result = await self._tool_node.ainvoke(state, config=config)
        except TimeoutError as exc:
            if trace is not None:
                trace.add_failed_tool_duration(time.monotonic() - started_at)
            raise PersonalAssistantTimeoutError("tool") from exc
        except Exception:
            if trace is not None:
                trace.add_failed_tool_duration(time.monotonic() - started_at)
            raise
        else:
            if trace is not None:
                trace.complete_tool_round(time.monotonic() - started_at)
        return {
            "messages": result["messages"],
            "tool_rounds": state.get("tool_rounds", 0) + 1,
        }

    async def _iteration_limit_node(self, state: PersonalAssistantState) -> dict:
        trace = get_active_agent_execution_trace()
        if trace is not None:
            trace.termination_reason = AgentTerminationReason.ITERATION_LIMIT
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

        trace = get_active_agent_execution_trace()
        if trace is not None:
            trace.record_guardrail_verdict(GuardrailVerdict.ADVICE_BOUNDARY.value)
            trace.termination_reason = AgentTerminationReason.OUTPUT_GUARDRAIL_BLOCKED

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
        trace = AgentExecutionTrace(mode=mode.value, trace_detail=self._trace_detail)
        context_token = activate_agent_execution_trace(trace)
        try:
            async with asyncio.timeout(self._timeout_policy.execution_seconds):
                result = await self._ainvoke_state(
                    messages=messages,
                    mode=mode,
                    diary_context=diary_context,
                    coaching_context=coaching_context,
                )
        except TimeoutError as exc:
            trace.termination_reason = AgentTerminationReason.TIMEOUT
            trace.record_timeout("execution")
            raise PersonalAssistantTimeoutError("execution") from exc
        except PersonalAssistantTimeoutError as exc:
            trace.termination_reason = AgentTerminationReason.TIMEOUT
            trace.record_timeout(exc.stage)
            raise
        except ModelProviderError as exc:
            trace.termination_reason = AgentTerminationReason.PROVIDER_ERROR
            trace.record_provider_error(exc.category.value)
            raise
        except asyncio.CancelledError:
            trace.termination_reason = AgentTerminationReason.CANCELLED
            raise
        except Exception:
            trace.termination_reason = (
                AgentTerminationReason.TOOL_ERROR
                if trace.tool_round_in_progress
                else AgentTerminationReason.UNEXPECTED_ERROR
            )
            raise
        else:
            for message in reversed(result["messages"]):
                if isinstance(message, AIMessage):
                    if message.tool_calls:
                        break
                    trace.record_final_response(_optional_ai_message_text(message))
                    return message
            trace.termination_reason = AgentTerminationReason.UNEXPECTED_ERROR
            raise RuntimeError("personal assistant graph did not produce final AIMessage")
        finally:
            self._record_execution(trace)
            reset_agent_execution_trace(context_token)

    def _record_execution(self, trace: AgentExecutionTrace) -> None:
        try:
            self._execution_recorder.record(trace.to_record())
        except Exception:
            logger.warning("personal assistant execution recording failed")


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


def _tool_names_from_state(state: PersonalAssistantState) -> list[str]:
    last_message = state["messages"][-1]
    if not isinstance(last_message, AIMessage):
        raise RuntimeError("tools node requires AIMessage")
    return [tool_call["name"] for tool_call in last_message.tool_calls]


def _tool_call_traces(message: AIMessage, round_number: int) -> list[ToolCallTraceRecord]:
    traces: list[ToolCallTraceRecord] = []
    for tool_call in message.tool_calls:
        traces.append(
            ToolCallTraceRecord(
                round=round_number,
                call_id=tool_call.get("id"),
                name=tool_call["name"],
                arguments=_tool_call_arguments(tool_call.get("args")),
            )
        )
    for invalid_call in getattr(message, "invalid_tool_calls", []) or []:
        raw_args = invalid_call.get("args") if isinstance(invalid_call, dict) else None
        traces.append(
            ToolCallTraceRecord(
                round=round_number,
                call_id=invalid_call.get("id") if isinstance(invalid_call, dict) else None,
                name=invalid_call.get("name") if isinstance(invalid_call, dict) else "unknown",
                arguments=None,
                arguments_parse_error=(
                    invalid_call.get("error")
                    if isinstance(invalid_call, dict) and isinstance(invalid_call.get("error"), str)
                    else f"could not parse tool arguments: {_short_text(raw_args)}"
                ),
            )
        )
    return traces


def _tool_call_arguments(value: object) -> dict | None:
    return value if isinstance(value, dict) else None


def _finish_reason(message: AIMessage) -> str | None:
    metadata = message.response_metadata
    for key in ("finish_reason", "stop_reason", "done_reason"):
        value = metadata.get(key)
        if isinstance(value, str):
            return value
    return None


def _optional_ai_message_text(message: AIMessage) -> str | None:
    try:
        content = _ai_message_text(message)
    except ValueError:
        return None
    return content or None


def _short_text(value: object, limit: int = 160) -> str:
    text = str(value)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _normalized_token_usage(message: AIMessage) -> dict[str, int] | None:
    usage = message.usage_metadata
    if not isinstance(usage, dict):
        return None

    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    total_tokens = usage.get("total_tokens")
    if not all(
        value is None or isinstance(value, int)
        for value in (input_tokens, output_tokens, total_tokens)
    ):
        return None
    if input_tokens is None and output_tokens is None and total_tokens is None:
        return None
    if total_tokens is None and isinstance(input_tokens, int) and isinstance(output_tokens, int):
        total_tokens = input_tokens + output_tokens
    return {
        "input_tokens": input_tokens if isinstance(input_tokens, int) else 0,
        "output_tokens": output_tokens if isinstance(output_tokens, int) else 0,
        "total_tokens": total_tokens if isinstance(total_tokens, int) else 0,
    }
