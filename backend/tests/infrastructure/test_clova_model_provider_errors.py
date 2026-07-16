import asyncio

import httpx
import openai
import pytest
from langchain_core.messages import HumanMessage

from app.application.service.model_provider_error import (
    ModelProviderError,
    ModelProviderErrorCategory,
)
from app.infrastructure.external.clova_tool_calling import ClovaToolCallingChatModel


class _RaisingBoundModel:
    def __init__(self, error: BaseException) -> None:
        self._error = error

    async def ainvoke(self, messages):
        raise self._error


class _RaisingChatModel:
    def __init__(self, *, error: BaseException, **kwargs) -> None:
        self._error = error

    def bind_tools(self, tools, **kwargs):
        return _RaisingBoundModel(self._error)

    async def ainvoke(self, messages):
        raise self._error


def _factory(error: BaseException):
    def create(**kwargs):
        return _RaisingChatModel(error=error, **kwargs)

    return create


def _request() -> httpx.Request:
    return httpx.Request("POST", "https://clova.example/v1/chat/completions")


def _status_error(status_code: int) -> openai.APIStatusError:
    return openai.APIStatusError(
        "provider detail containing nv-secret",
        response=httpx.Response(status_code, request=_request()),
        body=None,
    )


@pytest.mark.parametrize(
    ("status_code", "category", "retryable"),
    [
        (429, ModelProviderErrorCategory.RATE_LIMIT, True),
        (500, ModelProviderErrorCategory.UNAVAILABLE, True),
        (502, ModelProviderErrorCategory.UNAVAILABLE, True),
        (503, ModelProviderErrorCategory.UNAVAILABLE, True),
        (504, ModelProviderErrorCategory.UNAVAILABLE, True),
        (400, ModelProviderErrorCategory.INVALID_REQUEST, False),
        (401, ModelProviderErrorCategory.AUTHENTICATION, False),
        (403, ModelProviderErrorCategory.AUTHENTICATION, False),
        (404, ModelProviderErrorCategory.INVALID_REQUEST, False),
    ],
)
async def test_clova_adapter_converts_public_openai_status_errors(
    status_code,
    category,
    retryable,
):
    original = _status_error(status_code)
    model = ClovaToolCallingChatModel(chat_model_factory=_factory(original))

    with pytest.raises(ModelProviderError) as error:
        await model.ainvoke([HumanMessage(content="사용자 요청")], [])

    assert error.value.category == category
    assert error.value.retryable is retryable
    assert error.value.status_code == status_code
    assert error.value.__cause__ is original
    assert "nv-secret" not in str(error.value)
    assert "사용자 요청" not in str(error.value)


async def test_clova_adapter_converts_public_transport_errors_to_retryable_network_error():
    original = httpx.ConnectError("network nv-secret", request=_request())
    model = ClovaToolCallingChatModel(chat_model_factory=_factory(original))

    with pytest.raises(ModelProviderError) as error:
        await model.ainvoke([HumanMessage(content="사용자 요청")], [])

    assert error.value.category == ModelProviderErrorCategory.NETWORK
    assert error.value.retryable is True
    assert error.value.status_code is None
    assert error.value.__cause__ is original


async def test_clova_adapter_converts_unknown_public_openai_error_without_retry():
    original = openai.APIError("unknown provider error", request=_request(), body=None)
    model = ClovaToolCallingChatModel(chat_model_factory=_factory(original))

    with pytest.raises(ModelProviderError) as error:
        await model.ainvoke([HumanMessage(content="사용자 요청")], [])

    assert error.value.category == ModelProviderErrorCategory.UNKNOWN
    assert error.value.retryable is False
    assert error.value.status_code is None
    assert error.value.__cause__ is original


async def test_clova_adapter_propagates_cancelled_error_without_conversion():
    model = ClovaToolCallingChatModel(chat_model_factory=_factory(asyncio.CancelledError()))

    with pytest.raises(asyncio.CancelledError):
        await model.ainvoke([HumanMessage(content="사용자 요청")], [])


async def test_clova_adapter_leaves_unknown_non_provider_errors_unchanged():
    model = ClovaToolCallingChatModel(chat_model_factory=_factory(RuntimeError("unexpected")))

    with pytest.raises(RuntimeError, match="unexpected"):
        await model.ainvoke([HumanMessage(content="사용자 요청")], [])


async def test_clova_adapter_keeps_invalid_model_response_as_type_error():
    class _InvalidChatModel:
        def __init__(self, **kwargs) -> None:
            pass

        async def ainvoke(self, messages):
            return "not an AIMessage"

    model = ClovaToolCallingChatModel(chat_model_factory=_InvalidChatModel)

    with pytest.raises(TypeError, match="must return AIMessage"):
        await model.ainvoke([HumanMessage(content="사용자 요청")], [])
