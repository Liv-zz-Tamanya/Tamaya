import asyncio
from collections.abc import Sequence
from datetime import date
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.tools import BaseTool, StructuredTool

from app.application.service.agent_execution_observability import (
    AgentExecutionRecord,
    AgentExecutionTrace,
    AgentTerminationReason,
    AgentTraceDetail,
    activate_agent_execution_trace,
    reset_agent_execution_trace,
)
from app.application.service.diary_chat_prompt import DiaryConversationContext
from app.application.service.model_provider_error import (
    ModelProviderError,
    ModelProviderErrorCategory,
)
from app.application.service.model_retry_policy import ModelRetryPolicy
from app.application.service.personal_assistant_timeout import (
    PersonalAssistantTimeoutError,
    PersonalAssistantTimeoutPolicy,
)
from app.application.service.retrying_tool_calling_chat_model import RetryingToolCallingChatModel
from app.application.service.tool_calling_chat_model import ToolCallingChatModel
from app.application.tool.read_tools import (
    AgentToolExecutionContext,
    create_search_diary_memories_tool,
    create_search_health_records_tool,
)
from app.application.usecase.personal_assistant_agent import (
    PersonalAssistantAgent,
    PersonalAssistantMode,
)
from app.domain.model.event_chunk import EventChunk
from app.domain.model.health_chunk import HealthChunk


class _Recorder:
    def __init__(self) -> None:
        self.records: list[AgentExecutionRecord] = []

    def record(self, record: AgentExecutionRecord) -> None:
        self.records.append(record)


class _FailingRecorder:
    def record(self, record: AgentExecutionRecord) -> None:
        raise RuntimeError("recorder failed")


class _ResponsesModel(ToolCallingChatModel):
    def __init__(self, responses: Sequence[AIMessage | BaseException]) -> None:
        self._responses = list(responses)
        self.calls = 0

    async def ainvoke(
        self,
        messages: Sequence[BaseMessage],
        tools: Sequence[BaseTool],
    ) -> AIMessage:
        self.calls += 1
        response = self._responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


def _diary_context() -> DiaryConversationContext:
    return DiaryConversationContext(max_turns=5, current_user_turn=1, suggest_finalize=False)


def _tool_call() -> dict:
    return {
        "name": "search_diary_memories",
        "args": {"query": "PRIVATE_DIARY_TEXT"},
        "id": "call-memory",
        "type": "tool_call",
    }


def _tool() -> BaseTool:
    async def search_diary_memories(query: str) -> str:
        return "PRIVATE_DIARY_TEXT"

    return StructuredTool.from_function(
        coroutine=search_diary_memories,
        name="search_diary_memories",
        description="Search diary memories.",
    )


async def test_completed_execution_records_terminal_summary_once_without_sensitive_content():
    recorder = _Recorder()
    response = AIMessage(
        content="PRIVATE_DIARY_TEXT",
        usage_metadata={"input_tokens": 3, "output_tokens": 5, "total_tokens": 8},
    )
    agent = PersonalAssistantAgent(
        _ResponsesModel([response]),
        [],
        execution_recorder=recorder,
    )

    result = await agent.run(
        messages=[HumanMessage(content="PRIVATE_DIARY_TEXT")],
        mode=PersonalAssistantMode.DIARY,
        diary_context=_diary_context(),
    )

    assert result is response
    assert len(recorder.records) == 1
    record = recorder.records[0]
    assert record.mode == "diary"
    assert record.termination_reason == AgentTerminationReason.COMPLETED
    assert record.trace_id
    assert record.llm_calls == 1
    assert record.tool_rounds == 0
    assert record.tool_names == ()
    assert record.guardrail_verdict is None
    assert record.model_duration_ms >= 0
    assert record.tool_duration_ms == 0
    assert record.execution_duration_ms >= 0
    assert (record.input_tokens, record.output_tokens, record.total_tokens) == (3, 5, 8)
    assert "PRIVATE_DIARY_TEXT" not in str(record)


async def test_tool_execution_records_round_names_and_no_tool_arguments_or_results():
    recorder = _Recorder()
    model = _ResponsesModel(
        [
            AIMessage(content="search", tool_calls=[_tool_call()]),
            AIMessage(content="done"),
        ]
    )
    agent = PersonalAssistantAgent(model, [_tool()], execution_recorder=recorder)

    await agent.run(
        messages=[HumanMessage(content="PRIVATE_DIARY_TEXT")],
        mode=PersonalAssistantMode.DIARY,
        diary_context=_diary_context(),
    )

    record = recorder.records[0]
    assert record.llm_calls == 2
    assert record.tool_rounds == 1
    assert record.tool_names == ("search_diary_memories",)
    assert record.tool_duration_ms >= 0
    assert "PRIVATE_DIARY_TEXT" not in str(record)


async def test_full_trace_records_direct_llm_response_details():
    recorder = _Recorder()
    response = AIMessage(
        content="final response",
        response_metadata={"finish_reason": "stop"},
        usage_metadata={"input_tokens": 7, "output_tokens": 11, "total_tokens": 18},
    )
    agent = PersonalAssistantAgent(
        _ResponsesModel([response]),
        [],
        execution_recorder=recorder,
        trace_detail=AgentTraceDetail.FULL,
    )

    await agent.run(
        messages=[HumanMessage(content="안녕")],
        mode=PersonalAssistantMode.DIARY,
        diary_context=_diary_context(),
    )

    record = recorder.records[0]
    assert len(record.llm_call_traces) == 1
    trace = record.llm_call_traces[0]
    assert trace.call_number == 1
    assert trace.finish_reason == "stop"
    assert trace.response_content == "final response"
    assert trace.tool_calls == ()
    assert (trace.input_tokens, trace.output_tokens, trace.total_tokens) == (7, 11, 18)
    assert trace.duration_ms is not None
    assert record.first_finish_reason == "stop"
    assert record.first_response_content == "final response"
    assert record.final_response_content == "final response"


async def test_full_trace_records_tool_call_arguments_and_final_response():
    recorder = _Recorder()
    model = _ResponsesModel(
        [
            AIMessage(
                content="",
                tool_calls=[_tool_call()],
                response_metadata={"finish_reason": "tool_calls"},
                usage_metadata={"input_tokens": 3, "output_tokens": 4, "total_tokens": 7},
            ),
            AIMessage(
                content="done",
                response_metadata={"finish_reason": "stop"},
                usage_metadata={"input_tokens": 5, "output_tokens": 6, "total_tokens": 11},
            ),
        ]
    )
    agent = PersonalAssistantAgent(
        model,
        [_tool()],
        execution_recorder=recorder,
        trace_detail=AgentTraceDetail.FULL,
    )

    await agent.run(
        messages=[HumanMessage(content="PRIVATE_DIARY_TEXT")],
        mode=PersonalAssistantMode.DIARY,
        diary_context=_diary_context(),
    )

    record = recorder.records[0]
    assert len(record.llm_call_traces) == 2
    assert record.first_finish_reason == "tool_calls"
    assert record.first_response_content is None
    assert record.final_response_content == "done"
    assert record.tool_calls[0].round == 1
    assert record.tool_calls[0].call_id == "call-memory"
    assert record.tool_calls[0].name == "search_diary_memories"
    assert record.tool_calls[0].arguments == {"query": "PRIVATE_DIARY_TEXT"}
    assert [trace.call_number for trace in record.llm_call_traces] == [1, 2]
    assert record.llm_call_traces[0].tool_calls == record.tool_calls
    assert record.llm_call_traces[1].response_content == "done"


async def test_full_trace_records_invalid_tool_arguments_without_failing_recording():
    recorder = _Recorder()
    response = AIMessage(
        content="",
        invalid_tool_calls=[
            {
                "name": "search_diary_memories",
                "args": "{bad",
                "id": "bad-call",
                "error": "invalid json",
            }
        ],
        response_metadata={"finish_reason": "tool_calls"},
    )
    agent = PersonalAssistantAgent(
        _ResponsesModel([response]),
        [],
        execution_recorder=recorder,
        trace_detail=AgentTraceDetail.FULL,
    )

    await agent.run(
        messages=[HumanMessage(content="안녕")],
        mode=PersonalAssistantMode.DIARY,
        diary_context=_diary_context(),
    )

    record = recorder.records[0]
    assert record.tool_calls[0].name == "search_diary_memories"
    assert record.tool_calls[0].arguments is None
    assert record.tool_calls[0].arguments_parse_error == "invalid json"


async def test_basic_trace_keeps_tool_arguments_and_response_content_empty():
    recorder = _Recorder()
    model = _ResponsesModel(
        [
            AIMessage(content="", tool_calls=[_tool_call()]),
            AIMessage(content="PRIVATE_FINAL_RESPONSE"),
        ]
    )
    agent = PersonalAssistantAgent(model, [_tool()], execution_recorder=recorder)

    await agent.run(
        messages=[HumanMessage(content="PRIVATE_DIARY_TEXT")],
        mode=PersonalAssistantMode.DIARY,
        diary_context=_diary_context(),
    )

    record = recorder.records[0]
    assert record.tool_calls[0].name == "search_diary_memories"
    assert record.tool_calls[0].arguments is None
    assert record.first_response_content is None
    assert record.final_response_content is None
    assert all(trace.response_content is None for trace in record.llm_call_traces)
    assert "PRIVATE_DIARY_TEXT" not in str(record)
    assert "PRIVATE_FINAL_RESPONSE" not in str(record)


async def test_input_and_output_guardrails_have_distinct_terminal_records():
    input_recorder = _Recorder()
    blocked_agent = PersonalAssistantAgent(
        _ResponsesModel([]),
        [],
        execution_recorder=input_recorder,
    )

    await blocked_agent.run(
        messages=[HumanMessage(content="이 약 먹어도 돼? PRIVATE_HEALTH_TEXT")],
        mode=PersonalAssistantMode.HEALTH,
    )

    input_record = input_recorder.records[0]
    assert input_record.termination_reason == AgentTerminationReason.INPUT_GUARDRAIL_BLOCKED
    assert input_record.guardrail_verdict == "advice_boundary"
    assert input_record.llm_calls == 0
    assert input_record.tool_rounds == 0
    assert "PRIVATE_HEALTH_TEXT" not in str(input_record)

    output_recorder = _Recorder()
    output_agent = PersonalAssistantAgent(
        _ResponsesModel([AIMessage(content="하루 500mg씩 드세요 PRIVATE_HEALTH_TEXT")]),
        [],
        execution_recorder=output_recorder,
    )

    await output_agent.run(
        messages=[HumanMessage(content="오늘 걸음 수 알려줘")],
        mode=PersonalAssistantMode.HEALTH,
    )

    output_record = output_recorder.records[0]
    assert output_record.termination_reason == AgentTerminationReason.OUTPUT_GUARDRAIL_BLOCKED
    assert output_record.guardrail_verdict == "advice_boundary"
    assert "PRIVATE_HEALTH_TEXT" not in str(output_record)


async def test_retry_success_records_actual_attempts_and_retry_count():
    recorder = _Recorder()
    delegate = _ResponsesModel(
        [
            ModelProviderError(
                category=ModelProviderErrorCategory.RATE_LIMIT,
                retryable=True,
            ),
            AIMessage(content="recovered"),
        ]
    )
    model = RetryingToolCallingChatModel(
        delegate,
        ModelRetryPolicy(),
        sleep=lambda delay: _no_sleep(delay),
    )
    agent = PersonalAssistantAgent(model, [], execution_recorder=recorder)

    await agent.run(
        messages=[HumanMessage(content="안녕")],
        mode=PersonalAssistantMode.COACHING,
        coaching_context={"persona": "PRIVATE_PERSONA"},
    )

    record = recorder.records[0]
    assert record.llm_calls == 2
    assert record.retry_attempts == 1
    assert record.provider_error_category == "rate_limit"
    assert "PRIVATE_PERSONA" not in str(record)


async def test_provider_error_and_timeout_stages_are_recorded_once():
    provider_recorder = _Recorder()
    provider_agent = PersonalAssistantAgent(
        _ResponsesModel(
            [
                ModelProviderError(
                    category=ModelProviderErrorCategory.AUTHENTICATION,
                    retryable=False,
                )
            ]
        ),
        [],
        execution_recorder=provider_recorder,
    )

    with pytest.raises(ModelProviderError):
        await provider_agent.run(
            messages=[HumanMessage(content="안녕")],
            mode=PersonalAssistantMode.COACHING,
            coaching_context={"persona": None},
        )

    provider_record = provider_recorder.records[0]
    assert provider_record.termination_reason == AgentTerminationReason.PROVIDER_ERROR
    assert provider_record.provider_error_category == "authentication"

    timeout_recorder = _Recorder()
    timeout_agent = PersonalAssistantAgent(
        _HangingModel(),
        [],
        timeout_policy=PersonalAssistantTimeoutPolicy(0.01, 1, 1),
        execution_recorder=timeout_recorder,
    )

    with pytest.raises(PersonalAssistantTimeoutError):
        await timeout_agent.run(
            messages=[HumanMessage(content="안녕")],
            mode=PersonalAssistantMode.COACHING,
            coaching_context={"persona": None},
        )

    timeout_record = timeout_recorder.records[0]
    assert timeout_record.termination_reason == AgentTerminationReason.TIMEOUT
    assert timeout_record.timeout_stage == "model"
    assert len(timeout_recorder.records) == 1

    tool_timeout_recorder = _Recorder()
    tool_timeout_agent = PersonalAssistantAgent(
        _ResponsesModel([AIMessage(content="", tool_calls=[_tool_call()])]),
        [_hanging_tool()],
        timeout_policy=PersonalAssistantTimeoutPolicy(1, 0.01, 1),
        execution_recorder=tool_timeout_recorder,
    )

    with pytest.raises(PersonalAssistantTimeoutError):
        await tool_timeout_agent.run(
            messages=[HumanMessage(content="안녕")],
            mode=PersonalAssistantMode.DIARY,
            diary_context=_diary_context(),
        )

    tool_timeout_record = tool_timeout_recorder.records[0]
    assert tool_timeout_record.termination_reason == AgentTerminationReason.TIMEOUT
    assert tool_timeout_record.timeout_stage == "tool"
    assert tool_timeout_record.llm_calls == 1
    assert tool_timeout_record.tool_rounds == 1

    execution_timeout_recorder = _Recorder()
    execution_timeout_agent = PersonalAssistantAgent(
        _HangingModel(),
        [],
        timeout_policy=PersonalAssistantTimeoutPolicy(1, 1, 0.01),
        execution_recorder=execution_timeout_recorder,
    )

    with pytest.raises(PersonalAssistantTimeoutError):
        await execution_timeout_agent.run(
            messages=[HumanMessage(content="안녕")],
            mode=PersonalAssistantMode.COACHING,
            coaching_context={"persona": None},
        )

    execution_timeout_record = execution_timeout_recorder.records[0]
    assert execution_timeout_record.termination_reason == AgentTerminationReason.TIMEOUT
    assert execution_timeout_record.timeout_stage == "execution"


async def test_cancellation_and_recorder_failure_do_not_change_agent_outcome():
    cancellation_recorder = _Recorder()
    hanging_model = _HangingModel()
    cancellable_agent = PersonalAssistantAgent(
        hanging_model,
        [],
        execution_recorder=cancellation_recorder,
    )
    task = asyncio.create_task(
        cancellable_agent.run(
            messages=[HumanMessage(content="안녕")],
            mode=PersonalAssistantMode.COACHING,
            coaching_context={"persona": None},
        )
    )
    await hanging_model.started.wait()
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert cancellation_recorder.records[0].termination_reason == AgentTerminationReason.CANCELLED

    response = AIMessage(content="정상 응답")
    successful_agent = PersonalAssistantAgent(
        _ResponsesModel([response]),
        [],
        execution_recorder=_FailingRecorder(),
    )

    assert (
        await successful_agent.run(
            messages=[HumanMessage(content="안녕")],
            mode=PersonalAssistantMode.COACHING,
            coaching_context={"persona": None},
        )
    ) is response

    failing_agent = PersonalAssistantAgent(
        _ResponsesModel([RuntimeError("agent error")]),
        [],
        execution_recorder=_FailingRecorder(),
    )

    with pytest.raises(RuntimeError, match="agent error"):
        await failing_agent.run(
            messages=[HumanMessage(content="안녕")],
            mode=PersonalAssistantMode.COACHING,
            coaching_context={"persona": None},
        )


async def test_read_tool_records_only_retrieval_count_in_active_trace():
    class _DiaryQuery:
        async def search_similar(self, **kwargs) -> list[EventChunk]:
            return [
                EventChunk(
                    id=uuid4(),
                    chat_session_id=uuid4(),
                    diary_date=date(2026, 7, 1),
                    text="PRIVATE_DIARY_TEXT",
                    embedding=[0.1],
                    tags=[],
                    event_type="daily",
                )
            ]

    trace = AgentExecutionTrace(mode="diary")
    token = activate_agent_execution_trace(trace)
    try:
        tool = create_search_diary_memories_tool(
            _DiaryQuery(),
            AgentToolExecutionContext(device_id="device-private", session_id=uuid4()),
        )
        await tool.ainvoke({"query": "PRIVATE_DIARY_TEXT"})
    finally:
        reset_agent_execution_trace(token)

    record = trace.to_record()
    assert record.retrieval_result_count == 1
    assert record.diary_retrieval_result_count == 1
    assert record.health_retrieval_result_count is None
    assert "PRIVATE_DIARY_TEXT" not in str(record)
    assert "device-private" not in str(record)


async def test_health_read_tool_records_only_health_retrieval_count():
    class _HealthQuery:
        async def search_similar(self, **kwargs) -> list[HealthChunk]:
            return [
                HealthChunk(
                    device_id="device-private",
                    record_date=date(2026, 7, 1),
                    text="PRIVATE_HEALTH_TEXT",
                    embedding=[0.1],
                    data_types=["steps"],
                )
            ]

    trace = AgentExecutionTrace(mode="health")
    token = activate_agent_execution_trace(trace)
    try:
        tool = create_search_health_records_tool(
            _HealthQuery(),
            AgentToolExecutionContext(device_id="device-private", session_id=uuid4()),
        )
        await tool.ainvoke({"query": "PRIVATE_HEALTH_TEXT"})
    finally:
        reset_agent_execution_trace(token)

    record = trace.to_record()
    assert record.retrieval_result_count == 1
    assert record.diary_retrieval_result_count is None
    assert record.health_retrieval_result_count == 1
    assert "PRIVATE_HEALTH_TEXT" not in str(record)
    assert "device-private" not in str(record)


class _HangingModel(ToolCallingChatModel):
    def __init__(self) -> None:
        self.started = asyncio.Event()

    async def ainvoke(
        self,
        messages: Sequence[BaseMessage],
        tools: Sequence[BaseTool],
    ) -> AIMessage:
        self.started.set()
        await asyncio.Event().wait()
        raise AssertionError("unreachable")


def _hanging_tool() -> BaseTool:
    async def search_diary_memories(query: str) -> str:
        await asyncio.Event().wait()
        raise AssertionError("unreachable")

    return StructuredTool.from_function(
        coroutine=search_diary_memories,
        name="search_diary_memories",
        description="Search diary memories.",
    )


async def _no_sleep(delay: float) -> None:
    return None
