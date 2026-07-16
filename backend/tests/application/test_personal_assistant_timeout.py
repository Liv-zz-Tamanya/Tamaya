import asyncio

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import BaseTool, StructuredTool

from app.application.service.diary_chat_prompt import DiaryConversationContext
from app.application.service.personal_assistant_timeout import (
    PersonalAssistantTimeoutError,
    PersonalAssistantTimeoutPolicy,
)
from app.application.usecase.personal_assistant_agent import (
    PersonalAssistantAgent,
    PersonalAssistantMode,
)


class _HangingModel:
    def __init__(self) -> None:
        self.calls = 0
        self.started = asyncio.Event()

    async def ainvoke(self, messages, tools) -> AIMessage:
        self.calls += 1
        self.started.set()
        await asyncio.Event().wait()
        raise AssertionError("unreachable")


class _ResponsesModel:
    def __init__(self, responses: list[AIMessage]) -> None:
        self._responses = responses
        self.calls = 0

    async def ainvoke(self, messages, tools) -> AIMessage:
        response = self._responses[self.calls]
        self.calls += 1
        return response


def _policy(
    *, model: float = 1, tool: float = 1, execution: float = 1
) -> PersonalAssistantTimeoutPolicy:
    return PersonalAssistantTimeoutPolicy(
        model_call_seconds=model,
        tool_round_seconds=tool,
        execution_seconds=execution,
    )


def _diary_context() -> DiaryConversationContext:
    return DiaryConversationContext(max_turns=5, current_user_turn=1, suggest_finalize=False)


def _tool_call() -> dict:
    return {
        "name": "search_diary_memories",
        "args": {"query": "지난 기억"},
        "id": "call-memory",
        "type": "tool_call",
    }


def _hanging_tool(started: asyncio.Event) -> BaseTool:
    async def search_diary_memories(query: str) -> str:
        started.set()
        await asyncio.Event().wait()
        raise AssertionError("unreachable")

    return StructuredTool.from_function(
        coroutine=search_diary_memories,
        name="search_diary_memories",
        description="Search diary memories.",
    )


async def test_model_call_timeout_has_model_stage_and_does_not_run_tools():
    model = _HangingModel()
    tool_started = asyncio.Event()
    agent = PersonalAssistantAgent(
        model,
        [_hanging_tool(tool_started)],
        timeout_policy=_policy(model=0.01, execution=1),
    )

    with pytest.raises(PersonalAssistantTimeoutError) as error:
        await agent.run(
            messages=[HumanMessage(content="지난 기록 알려줘")],
            mode=PersonalAssistantMode.DIARY,
            diary_context=_diary_context(),
        )

    assert error.value.stage == "model"
    assert model.calls == 1
    assert not tool_started.is_set()


async def test_tool_round_timeout_has_tool_stage_without_follow_up_model_call():
    model = _ResponsesModel([AIMessage(content="검색할게", tool_calls=[_tool_call()])])
    tool_started = asyncio.Event()
    agent = PersonalAssistantAgent(
        model,
        [_hanging_tool(tool_started)],
        timeout_policy=_policy(tool=0.01, execution=1),
    )

    with pytest.raises(PersonalAssistantTimeoutError) as error:
        await agent.run(
            messages=[HumanMessage(content="지난 기록 알려줘")],
            mode=PersonalAssistantMode.DIARY,
            diary_context=_diary_context(),
        )

    assert error.value.stage == "tool"
    assert tool_started.is_set()
    assert model.calls == 1


async def test_execution_timeout_does_not_replace_inner_stage_error():
    agent = PersonalAssistantAgent(
        _HangingModel(),
        [],
        timeout_policy=_policy(model=1, tool=1, execution=0.01),
    )

    with pytest.raises(PersonalAssistantTimeoutError) as error:
        await agent.run(
            messages=[HumanMessage(content="오늘 기분이 복잡해")],
            mode=PersonalAssistantMode.DIARY,
            diary_context=_diary_context(),
        )

    assert error.value.stage == "execution"


@pytest.mark.parametrize(
    ("mode", "kwargs"),
    [
        (PersonalAssistantMode.DIARY, {"diary_context": _diary_context()}),
        (PersonalAssistantMode.HEALTH, {}),
        (PersonalAssistantMode.COACHING, {"coaching_context": {"persona": None}}),
    ],
)
async def test_all_modes_apply_model_timeout_policy(mode, kwargs):
    agent = PersonalAssistantAgent(
        _HangingModel(),
        [],
        timeout_policy=_policy(model=0.01, execution=1),
    )

    with pytest.raises(PersonalAssistantTimeoutError) as error:
        await agent.run(messages=[HumanMessage(content="안녕")], mode=mode, **kwargs)

    assert error.value.stage == "model"


async def test_guardrail_short_circuit_does_not_enter_model_timeout_path():
    model = _HangingModel()
    agent = PersonalAssistantAgent(
        model,
        [],
        timeout_policy=_policy(model=0.01, execution=0.1),
    )

    response = await agent.run(
        messages=[HumanMessage(content="이 약 먹어도 돼?")],
        mode=PersonalAssistantMode.HEALTH,
    )

    assert "전문가" in response.content
    assert model.calls == 0


async def test_cancelled_error_is_not_converted_to_timeout_error():
    model = _HangingModel()
    agent = PersonalAssistantAgent(
        model,
        [],
        timeout_policy=_policy(model=10, tool=10, execution=10),
    )
    task = asyncio.create_task(
        agent.run(
            messages=[HumanMessage(content="오늘 기분이 복잡해")],
            mode=PersonalAssistantMode.DIARY,
            diary_context=_diary_context(),
        )
    )
    await model.started.wait()
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task


def test_timeout_policy_rejects_non_positive_values():
    with pytest.raises(ValueError, match="model_call_seconds"):
        PersonalAssistantTimeoutPolicy(0, 1, 1)
