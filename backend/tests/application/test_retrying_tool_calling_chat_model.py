import asyncio
from collections.abc import Sequence

import pytest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.tools import BaseTool

from app.application.service.model_provider_error import (
    ModelProviderError,
    ModelProviderErrorCategory,
)
from app.application.service.model_retry_policy import ModelRetryPolicy
from app.application.service.retrying_tool_calling_chat_model import RetryingToolCallingChatModel
from app.application.service.tool_calling_chat_model import ToolCallingChatModel


class _SequenceModel(ToolCallingChatModel):
    def __init__(self, responses: Sequence[AIMessage | BaseException]) -> None:
        self._responses = list(responses)
        self.calls: list[dict] = []

    async def ainvoke(
        self,
        messages: Sequence[BaseMessage],
        tools: Sequence[BaseTool],
    ) -> AIMessage:
        self.calls.append({"messages": messages, "tools": tools})
        response = self._responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


def _error(
    category: ModelProviderErrorCategory = ModelProviderErrorCategory.UNAVAILABLE,
    *,
    retryable: bool = True,
) -> ModelProviderError:
    return ModelProviderError(category=category, retryable=retryable)


async def test_successful_first_attempt_does_not_sleep_or_rebuild_response():
    response = AIMessage(content="응답", response_metadata={"provider": "clova"})
    delegate = _SequenceModel([response])
    sleeps: list[float] = []
    model = RetryingToolCallingChatModel(
        delegate,
        ModelRetryPolicy(),
        sleep=lambda delay: _record_sleep(sleeps, delay),
    )
    messages = [HumanMessage(content="안녕")]
    tools: list[BaseTool] = []

    result = await model.ainvoke(messages, tools)

    assert result is response
    assert len(delegate.calls) == 1
    assert sleeps == []
    assert delegate.calls[0]["messages"] is messages
    assert delegate.calls[0]["tools"] is tools


async def test_rate_limit_retries_once_then_preserves_ai_message_tool_calls_and_metadata():
    response = AIMessage(
        content="기억을 찾았어",
        tool_calls=[{"name": "search_diary_memories", "args": {"query": "발표"}, "id": "c1"}],
        response_metadata={"provider": "clova"},
    )
    delegate = _SequenceModel([_error(ModelProviderErrorCategory.RATE_LIMIT), response])
    sleeps: list[float] = []
    model = RetryingToolCallingChatModel(
        delegate,
        ModelRetryPolicy(),
        sleep=lambda delay: _record_sleep(sleeps, delay),
    )
    messages = [HumanMessage(content="발표 기억 찾아줘")]
    tools: list[BaseTool] = []

    result = await model.ainvoke(messages, tools)

    assert result is response
    assert result.tool_calls == response.tool_calls
    assert result.response_metadata == {"provider": "clova"}
    assert len(delegate.calls) == 2
    assert sleeps == [0.5]
    assert all(call["messages"] is messages for call in delegate.calls)
    assert all(call["tools"] is tools for call in delegate.calls)


async def test_network_error_retries_and_unavailable_error_stops_at_max_attempts():
    response = AIMessage(content="복구됨")
    network_delegate = _SequenceModel([_error(ModelProviderErrorCategory.NETWORK), response])
    network_sleeps: list[float] = []
    network_model = RetryingToolCallingChatModel(
        network_delegate,
        ModelRetryPolicy(),
        sleep=lambda delay: _record_sleep(network_sleeps, delay),
    )

    assert (await network_model.ainvoke([HumanMessage(content="안녕")], [])).content == "복구됨"
    assert len(network_delegate.calls) == 2
    assert network_sleeps == [0.5]

    error = _error()
    unavailable_delegate = _SequenceModel([error, error, error])
    unavailable_sleeps: list[float] = []
    unavailable_model = RetryingToolCallingChatModel(
        unavailable_delegate,
        ModelRetryPolicy(max_attempts=3),
        sleep=lambda delay: _record_sleep(unavailable_sleeps, delay),
    )

    with pytest.raises(ModelProviderError) as raised:
        await unavailable_model.ainvoke([HumanMessage(content="안녕")], [])

    assert raised.value is error
    assert len(unavailable_delegate.calls) == 3
    assert unavailable_sleeps == [0.5, 1.0]


@pytest.mark.parametrize(
    "error",
    [
        _error(ModelProviderErrorCategory.INVALID_REQUEST, retryable=False),
        _error(ModelProviderErrorCategory.AUTHENTICATION, retryable=False),
        _error(ModelProviderErrorCategory.UNKNOWN, retryable=False),
        TypeError("invalid response"),
    ],
)
async def test_non_retryable_errors_are_propagated_without_sleep(error):
    delegate = _SequenceModel([error])
    sleeps: list[float] = []
    model = RetryingToolCallingChatModel(
        delegate,
        ModelRetryPolicy(),
        sleep=lambda delay: _record_sleep(sleeps, delay),
    )

    with pytest.raises(type(error)):
        await model.ainvoke([HumanMessage(content="안녕")], [])

    assert len(delegate.calls) == 1
    assert sleeps == []


async def test_cancelled_error_is_propagated_without_retry():
    delegate = _SequenceModel([asyncio.CancelledError()])
    model = RetryingToolCallingChatModel(delegate, ModelRetryPolicy())

    with pytest.raises(asyncio.CancelledError):
        await model.ainvoke([HumanMessage(content="안녕")], [])

    assert len(delegate.calls) == 1


def test_retry_policy_validates_bounds_and_caps_backoff():
    policy = ModelRetryPolicy(
        max_attempts=4,
        initial_backoff_seconds=0.5,
        backoff_multiplier=2,
        max_backoff_seconds=1,
    )

    assert [policy.backoff_seconds(index) for index in (1, 2, 3)] == [0.5, 1.0, 1]
    with pytest.raises(ValueError, match="max_attempts"):
        ModelRetryPolicy(max_attempts=0)
    with pytest.raises(ValueError, match="max_backoff_seconds"):
        ModelRetryPolicy(initial_backoff_seconds=1, max_backoff_seconds=0.5)


async def _record_sleep(sleeps: list[float], delay: float) -> None:
    sleeps.append(delay)
