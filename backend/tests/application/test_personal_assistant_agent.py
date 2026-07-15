from collections.abc import Sequence

import pytest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool, StructuredTool

from app.application.service.diary_chat_prompt import DiaryConversationContext
from app.application.usecase.personal_assistant_agent import (
    ITERATION_LIMIT_MESSAGE,
    PersonalAssistantAgent,
    PersonalAssistantMode,
)


class _FakeToolCallingChatModel:
    def __init__(self, responses: Sequence[AIMessage | Exception]) -> None:
        self._responses = list(responses)
        self.calls: list[dict] = []

    async def ainvoke(
        self,
        messages: Sequence[BaseMessage],
        tools: Sequence[BaseTool],
    ) -> AIMessage:
        self.calls.append({"messages": list(messages), "tools": list(tools)})
        if not self._responses:
            raise AssertionError("unexpected model call")
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _tool_call(name: str, call_id: str, **args) -> dict:
    return {"name": name, "args": args, "id": call_id, "type": "tool_call"}


def _diary_context(
    *,
    max_turns: int = 5,
    current_user_turn: int = 1,
    suggest_finalize: bool = False,
) -> DiaryConversationContext:
    return DiaryConversationContext(
        max_turns=max_turns,
        current_user_turn=current_user_turn,
        suggest_finalize=suggest_finalize,
    )


def _recording_tool(
    name: str,
    calls: list[dict],
    *,
    result: str | None = None,
    error: Exception | None = None,
) -> BaseTool:
    async def record_tool(query: str, limit: int = 5) -> str:
        calls.append({"query": query, "limit": limit})
        if error:
            raise error
        return result if result is not None else f"{name}:{query}:{limit}"

    record_tool.__name__ = name
    record_tool.__doc__ = f"Test tool named {name}."
    return StructuredTool.from_function(
        coroutine=record_tool,
        name=name,
        description=f"Test tool named {name}.",
    )


async def test_run_returns_general_response_without_tool_execution():
    model = _FakeToolCallingChatModel([AIMessage(content="일반 응답")])
    tool_calls: list[dict] = []
    tool = _recording_tool("search_diary_memories", tool_calls)
    agent = PersonalAssistantAgent(model, [tool])
    messages = [HumanMessage(content="오늘 기분이 복잡해")]

    response = await agent.run(
        messages=messages,
        mode=PersonalAssistantMode.DIARY,
        diary_context=_diary_context(),
    )
    state = await PersonalAssistantAgent(
        _FakeToolCallingChatModel([AIMessage(content="상태 응답")]),
        [tool],
    )._ainvoke_state(
        messages=messages,
        mode=PersonalAssistantMode.DIARY,
        diary_context=_diary_context(),
    )

    assert response.content == "일반 응답"
    assert len(model.calls) == 1
    assert tool_calls == []
    assert state["llm_calls"] == 1
    assert state["tool_rounds"] == 0
    assert model.calls[0]["messages"][1:] == messages


async def test_diary_memory_tool_round_returns_final_response():
    diary_calls: list[dict] = []
    health_calls: list[dict] = []
    diary_tool = _recording_tool("search_diary_memories", diary_calls, result="diary result")
    health_tool = _recording_tool("search_health_records", health_calls)
    model = _FakeToolCallingChatModel(
        [
            AIMessage(
                content="기억을 찾아볼게요.",
                tool_calls=[
                    _tool_call("search_diary_memories", "call-diary", query="발표", limit=2)
                ],
            ),
            AIMessage(content="발표 기억을 찾았어요."),
        ]
    )
    agent = PersonalAssistantAgent(model, [diary_tool, health_tool])

    state = await agent._ainvoke_state(
        messages=[HumanMessage(content="발표했던 기억 찾아줘")],
        mode=PersonalAssistantMode.DIARY,
        diary_context=_diary_context(),
    )
    response = await PersonalAssistantAgent(
        _FakeToolCallingChatModel(
            [
                AIMessage(
                    content="기억을 찾아볼게요.",
                    tool_calls=[
                        _tool_call("search_diary_memories", "call-diary-2", query="발표", limit=2)
                    ],
                ),
                AIMessage(content="발표 기억을 찾았어요."),
            ]
        ),
        [diary_tool, health_tool],
    ).run(
        messages=[HumanMessage(content="발표했던 기억 찾아줘")],
        mode=PersonalAssistantMode.DIARY,
        diary_context=_diary_context(),
    )

    assert response.content == "발표 기억을 찾았어요."
    assert diary_calls == [{"query": "발표", "limit": 2}, {"query": "발표", "limit": 2}]
    assert health_calls == []
    assert state["llm_calls"] == 2
    assert state["tool_rounds"] == 1
    tool_messages = [message for message in state["messages"] if isinstance(message, ToolMessage)]
    assert len(tool_messages) == 1
    assert tool_messages[0].tool_call_id == "call-diary"
    assert tool_messages[0].content == "diary result"
    assert any(isinstance(message, ToolMessage) for message in model.calls[1]["messages"])


async def test_health_record_tool_round_returns_final_response():
    diary_calls: list[dict] = []
    health_calls: list[dict] = []
    diary_tool = _recording_tool("search_diary_memories", diary_calls)
    health_tool = _recording_tool("search_health_records", health_calls, result="health result")
    model = _FakeToolCallingChatModel(
        [
            AIMessage(
                content="건강 기록을 찾아볼게요.",
                tool_calls=[
                    _tool_call(
                        "search_health_records", "call-health", query="어제 걸음 수", limit=3
                    )
                ],
            ),
            AIMessage(content="어제 걸음 수 기록을 찾았어요."),
        ]
    )
    agent = PersonalAssistantAgent(model, [diary_tool, health_tool])

    state = await agent._ainvoke_state(
        messages=[HumanMessage(content="어제 얼마나 걸었어?")],
        mode=PersonalAssistantMode.HEALTH,
    )

    assert health_calls == [{"query": "어제 걸음 수", "limit": 3}]
    assert diary_calls == []
    assert state["messages"][-1].content == "어제 걸음 수 기록을 찾았어요."
    assert state["llm_calls"] == 2
    assert state["tool_rounds"] == 1
    assert any(
        isinstance(message, ToolMessage) and message.content == "health result"
        for message in model.calls[1]["messages"]
    )


async def test_sequential_multiple_tool_rounds_preserve_message_order_and_counts():
    diary_calls: list[dict] = []
    health_calls: list[dict] = []
    model = _FakeToolCallingChatModel(
        [
            AIMessage(
                content="일기 먼저 볼게요.",
                tool_calls=[_tool_call("search_diary_memories", "call-1", query="산책")],
            ),
            AIMessage(
                content="건강 기록도 볼게요.",
                tool_calls=[_tool_call("search_health_records", "call-2", query="산책 걸음")],
            ),
            AIMessage(content="산책과 걸음 기록을 함께 정리했어요."),
        ]
    )
    agent = PersonalAssistantAgent(
        model,
        [
            _recording_tool("search_diary_memories", diary_calls, result="diary result"),
            _recording_tool("search_health_records", health_calls, result="health result"),
        ],
    )

    state = await agent._ainvoke_state(
        messages=[HumanMessage(content="산책과 건강 기록을 같이 봐줘")],
        mode=PersonalAssistantMode.DIARY,
        diary_context=_diary_context(),
    )

    assert diary_calls == [{"query": "산책", "limit": 5}]
    assert health_calls == [{"query": "산책 걸음", "limit": 5}]
    assert state["llm_calls"] == 3
    assert state["tool_rounds"] == 2
    assert [type(message).__name__ for message in state["messages"]] == [
        "HumanMessage",
        "AIMessage",
        "ToolMessage",
        "AIMessage",
        "ToolMessage",
        "AIMessage",
    ]
    assert [
        message.tool_call_id for message in state["messages"] if isinstance(message, ToolMessage)
    ] == [
        "call-1",
        "call-2",
    ]


async def test_multiple_tool_calls_in_one_ai_message_are_all_executed():
    diary_calls: list[dict] = []
    health_calls: list[dict] = []
    model = _FakeToolCallingChatModel(
        [
            AIMessage(
                content="두 기록을 같이 볼게요.",
                tool_calls=[
                    _tool_call("search_diary_memories", "call-diary", query="운동"),
                    _tool_call("search_health_records", "call-health", query="운동"),
                ],
            ),
            AIMessage(content="두 기록을 확인했어요."),
        ]
    )
    agent = PersonalAssistantAgent(
        model,
        [
            _recording_tool("search_diary_memories", diary_calls, result="diary result"),
            _recording_tool("search_health_records", health_calls, result="health result"),
        ],
    )

    state = await agent._ainvoke_state(
        messages=[HumanMessage(content="운동한 날 기록 찾아줘")],
        mode=PersonalAssistantMode.HEALTH,
    )

    assert diary_calls == [{"query": "운동", "limit": 5}]
    assert health_calls == [{"query": "운동", "limit": 5}]
    tool_messages = [message for message in state["messages"] if isinstance(message, ToolMessage)]
    assert {message.tool_call_id for message in tool_messages} == {"call-diary", "call-health"}
    second_model_messages = model.calls[1]["messages"]
    assert sum(isinstance(message, ToolMessage) for message in second_model_messages) == 2


async def test_iteration_limit_returns_deterministic_ai_message_without_extra_tool_execution():
    tool_calls: list[dict] = []
    state_model = _FakeToolCallingChatModel(
        [
            AIMessage(
                content="1",
                tool_calls=[_tool_call("search_diary_memories", "call-1", query="반복")],
            ),
            AIMessage(
                content="2",
                tool_calls=[_tool_call("search_diary_memories", "call-2", query="반복")],
            ),
            AIMessage(
                content="3",
                tool_calls=[_tool_call("search_diary_memories", "call-3", query="반복")],
            ),
        ]
    )
    agent = PersonalAssistantAgent(
        state_model,
        [_recording_tool("search_diary_memories", tool_calls)],
        max_tool_rounds=2,
    )

    state = await agent._ainvoke_state(
        messages=[HumanMessage(content="계속 찾아봐")],
        mode=PersonalAssistantMode.DIARY,
        diary_context=_diary_context(),
    )

    response_model = _FakeToolCallingChatModel(
        [
            AIMessage(
                content="1",
                tool_calls=[_tool_call("search_diary_memories", "run-call-1", query="반복")],
            ),
            AIMessage(
                content="2",
                tool_calls=[_tool_call("search_diary_memories", "run-call-2", query="반복")],
            ),
            AIMessage(
                content="3",
                tool_calls=[_tool_call("search_diary_memories", "run-call-3", query="반복")],
            ),
        ]
    )
    response = await PersonalAssistantAgent(
        response_model,
        [_recording_tool("search_diary_memories", [])],
        max_tool_rounds=2,
    ).run(
        messages=[HumanMessage(content="계속 찾아봐")],
        mode=PersonalAssistantMode.DIARY,
        diary_context=_diary_context(),
    )

    assert response.content == ITERATION_LIMIT_MESSAGE
    assert "iteration_limit" not in response.content
    assert "call-" not in response.content
    assert len(tool_calls) == 2
    assert len(state_model.calls) == 3
    assert state["messages"][-1].content == ITERATION_LIMIT_MESSAGE


async def test_mode_specific_system_message_is_first_and_not_accumulated_in_state():
    diary_model = _FakeToolCallingChatModel([AIMessage(content="diary")])
    health_model = _FakeToolCallingChatModel([AIMessage(content="health")])
    input_messages = [HumanMessage(content="기록 봐줘")]

    diary_state = await PersonalAssistantAgent(diary_model, [])._ainvoke_state(
        messages=input_messages,
        mode=PersonalAssistantMode.DIARY,
        diary_context=_diary_context(max_turns=5, current_user_turn=2),
    )
    health_state = await PersonalAssistantAgent(health_model, [])._ainvoke_state(
        messages=input_messages,
        mode=PersonalAssistantMode.HEALTH,
    )

    diary_messages = diary_model.calls[0]["messages"]
    health_messages = health_model.calls[0]["messages"]
    assert isinstance(diary_messages[0], SystemMessage)
    assert "이음이야" in diary_messages[0].content
    assert "[현재 2턴째 / 5턴]" in diary_messages[0].content
    assert "search_diary_memories" in diary_messages[0].content
    assert isinstance(health_messages[0], SystemMessage)
    assert "헬시" in health_messages[0].content
    assert "search_health_records" in health_messages[0].content
    assert diary_messages[1:] == input_messages
    assert health_messages[1:] == input_messages
    assert not any(isinstance(message, SystemMessage) for message in diary_state["messages"])
    assert not any(isinstance(message, SystemMessage) for message in health_state["messages"])


async def test_diary_mode_requires_diary_context():
    agent = PersonalAssistantAgent(_FakeToolCallingChatModel([AIMessage(content="응답")]), [])

    with pytest.raises(ValueError, match="diary_context is required"):
        await agent.run(messages=[HumanMessage(content="안녕")], mode=PersonalAssistantMode.DIARY)


async def test_health_mode_rejects_diary_context():
    agent = PersonalAssistantAgent(_FakeToolCallingChatModel([AIMessage(content="응답")]), [])

    with pytest.raises(ValueError, match="only supported for diary mode"):
        await agent.run(
            messages=[HumanMessage(content="안녕")],
            mode=PersonalAssistantMode.HEALTH,
            diary_context=_diary_context(),
        )


async def test_health_prompt_is_applied_to_every_model_call_and_tool_scope_is_preserved():
    health_calls: list[dict] = []
    model = _FakeToolCallingChatModel(
        [
            AIMessage(
                content="건강 기록 확인",
                tool_calls=[_tool_call("search_health_records", "call-health", query="걸음 수")],
            ),
            AIMessage(content="걸음 수를 확인했어."),
        ]
    )
    agent = PersonalAssistantAgent(
        model,
        [_recording_tool("search_health_records", health_calls, result="health result")],
    )

    response = await agent.run(
        messages=[HumanMessage(content="어제 걸음 수 알려줘")],
        mode=PersonalAssistantMode.HEALTH,
    )

    assert response.content == "걸음 수를 확인했어."
    assert health_calls == [{"query": "걸음 수", "limit": 5}]
    assert len(model.calls) == 2
    for call in model.calls:
        assert [tool.name for tool in call["tools"]] == ["search_health_records"]
        system_message = call["messages"][0]
        assert isinstance(system_message, SystemMessage)
        assert "헬시" in system_message.content
        assert "search_health_records" in system_message.content
        assert "search_diary_memories" not in system_message.content
    assert any(isinstance(message, ToolMessage) for message in model.calls[1]["messages"])


async def test_diary_turn_policy_is_applied_to_every_model_call():
    tool_calls: list[dict] = []
    model = _FakeToolCallingChatModel(
        [
            AIMessage(
                content="기억 확인",
                tool_calls=[_tool_call("search_diary_memories", "call-1", query="발표")],
            ),
            AIMessage(content="최종 응답"),
        ]
    )
    agent = PersonalAssistantAgent(
        model,
        [_recording_tool("search_diary_memories", tool_calls)],
    )

    await agent.run(
        messages=[HumanMessage(content="지난 발표 기억나?")],
        mode=PersonalAssistantMode.DIARY,
        diary_context=_diary_context(max_turns=5, current_user_turn=4, suggest_finalize=True),
    )

    assert len(model.calls) == 2
    for call in model.calls:
        system_message = call["messages"][0]
        assert isinstance(system_message, SystemMessage)
        assert "[마무리 지시" in system_message.content
        assert "새 질문을 던지지 마" in system_message.content
        assert "search_diary_memories" in system_message.content


async def test_empty_tool_list_supports_general_response():
    model = _FakeToolCallingChatModel([AIMessage(content="도구 없이 답변")])
    agent = PersonalAssistantAgent(model, [])

    response = await agent.run(
        messages=[HumanMessage(content="안녕")],
        mode=PersonalAssistantMode.DIARY,
        diary_context=_diary_context(),
    )

    assert response.content == "도구 없이 답변"
    assert model.calls[0]["tools"] == []


async def test_model_exception_is_propagated_without_retry_or_fallback():
    model = _FakeToolCallingChatModel([RuntimeError("model failed")])
    agent = PersonalAssistantAgent(model, [])

    with pytest.raises(RuntimeError, match="model failed"):
        await agent.run(
            messages=[HumanMessage(content="안녕")],
            mode=PersonalAssistantMode.DIARY,
            diary_context=_diary_context(),
        )

    assert len(model.calls) == 1


async def test_tool_exception_is_propagated_without_retry_or_fallback():
    tool_calls: list[dict] = []
    model = _FakeToolCallingChatModel(
        [
            AIMessage(
                content="도구 호출",
                tool_calls=[_tool_call("search_diary_memories", "call-error", query="실패")],
            )
        ]
    )
    agent = PersonalAssistantAgent(
        model,
        [
            _recording_tool(
                "search_diary_memories",
                tool_calls,
                error=RuntimeError("tool failed"),
            )
        ],
    )

    with pytest.raises(RuntimeError, match="tool failed"):
        await agent.run(
            messages=[HumanMessage(content="실패")],
            mode=PersonalAssistantMode.DIARY,
            diary_context=_diary_context(),
        )

    assert tool_calls == [{"query": "실패", "limit": 5}]
    assert len(model.calls) == 1


async def test_unknown_tool_call_is_converted_to_tool_message_by_tool_node():
    model = _FakeToolCallingChatModel(
        [
            AIMessage(
                content="없는 도구 호출",
                tool_calls=[_tool_call("missing_tool", "call-missing", query="x")],
            ),
            AIMessage(content="사용 가능한 도구로 다시 요청해 주세요."),
        ]
    )
    agent = PersonalAssistantAgent(model, [])

    state = await agent._ainvoke_state(
        messages=[HumanMessage(content="없는 도구")],
        mode=PersonalAssistantMode.DIARY,
        diary_context=_diary_context(),
    )

    tool_messages = [message for message in state["messages"] if isinstance(message, ToolMessage)]
    assert len(tool_messages) == 1
    assert tool_messages[0].tool_call_id == "call-missing"
    assert tool_messages[0].status == "error"
    assert "missing_tool" in tool_messages[0].content
    assert state["messages"][-1].content == "사용 가능한 도구로 다시 요청해 주세요."


def test_duplicate_tool_names_are_rejected():
    first_calls: list[dict] = []
    second_calls: list[dict] = []

    with pytest.raises(ValueError, match="duplicate tool names"):
        PersonalAssistantAgent(
            _FakeToolCallingChatModel([]),
            [
                _recording_tool("search_diary_memories", first_calls),
                _recording_tool("search_diary_memories", second_calls),
            ],
        )


def test_max_tool_rounds_must_be_positive():
    with pytest.raises(ValueError, match="max_tool_rounds"):
        PersonalAssistantAgent(_FakeToolCallingChatModel([]), [], max_tool_rounds=0)


async def test_run_does_not_mutate_input_message_list_or_message_objects():
    model = _FakeToolCallingChatModel([AIMessage(content="응답")])
    agent = PersonalAssistantAgent(model, [])
    human_message = HumanMessage(content="원본")
    messages = [human_message]
    original_id = id(human_message)

    await agent.run(
        messages=messages,
        mode=PersonalAssistantMode.DIARY,
        diary_context=_diary_context(),
    )

    assert messages == [human_message]
    assert id(messages[0]) == original_id
    assert messages[0].content == "원본"
