import asyncio
from collections.abc import Callable, Sequence
from typing import Any, Protocol

import httpx
import openai
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langchain_naver import ChatClovaX

from app.application.service.model_provider_error import (
    ModelProviderError,
    ModelProviderErrorCategory,
)
from app.application.service.tool_calling_chat_model import ToolCallingChatModel
from app.infrastructure.config.settings import settings


class _BindableChatModel(Protocol):
    def bind_tools(
        self,
        tools: Sequence[BaseTool],
        **kwargs,
    ) -> Runnable[Sequence[BaseMessage], AIMessage]: ...

    async def ainvoke(self, input, *args, **kwargs) -> AIMessage: ...


ChatModelFactory = Callable[..., _BindableChatModel]


class ClovaToolCallingChatModel(ToolCallingChatModel):
    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: float | None = None,
        chat_model_factory: ChatModelFactory = ChatClovaX,
    ) -> None:
        self._model = model if model is not None else settings.clova_model
        self._api_key = api_key if api_key is not None else settings.clova_api_key
        self._base_url = base_url if base_url is not None else settings.clova_base_url
        self._temperature = (
            temperature if temperature is not None else settings.clova_agent_temperature
        )
        self._max_tokens = max_tokens if max_tokens is not None else settings.clova_agent_max_tokens
        self._timeout = timeout if timeout is not None else settings.clova_agent_timeout_seconds
        self._chat_model = chat_model_factory(
            model=self._model,
            api_key=self._api_key,
            base_url=self._base_url,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            timeout=self._timeout,
            max_retries=0,
        )

    def __repr__(self) -> str:
        return (
            "ClovaToolCallingChatModel("
            f"model={self._model!r}, "
            f"base_url={self._base_url!r}, "
            f"temperature={self._temperature!r}, "
            f"max_tokens={self._max_tokens!r}, "
            f"timeout={self._timeout!r}, "
            "api_key='***'"
            ")"
        )

    async def ainvoke(
        self,
        messages: Sequence[BaseMessage],
        tools: Sequence[BaseTool],
    ) -> AIMessage:
        runnable = (
            self._chat_model.bind_tools(list(tools), tool_choice="auto")
            if tools
            else self._chat_model
        )
        try:
            response = await runnable.ainvoke(list(messages))
        except asyncio.CancelledError:
            raise
        except (openai.APIStatusError, httpx.HTTPStatusError) as exc:
            raise _model_provider_error_from_status(_status_code_from_error(exc)) from exc
        except (openai.APIConnectionError, httpx.TransportError) as exc:
            raise ModelProviderError(
                category=ModelProviderErrorCategory.NETWORK,
                retryable=True,
            ) from exc
        except (openai.APIError, httpx.HTTPError) as exc:
            raise ModelProviderError(
                category=ModelProviderErrorCategory.UNKNOWN,
                retryable=False,
            ) from exc
        if not isinstance(response, AIMessage):
            raise TypeError("CLOVA tool-calling model must return AIMessage")
        _normalize_usage_metadata(response)
        return response


def _status_code_from_error(exc: openai.APIStatusError | httpx.HTTPStatusError) -> int:
    if isinstance(exc, openai.APIStatusError):
        return exc.status_code
    return exc.response.status_code


def _model_provider_error_from_status(status_code: int) -> ModelProviderError:
    if status_code == 429:
        return ModelProviderError(
            category=ModelProviderErrorCategory.RATE_LIMIT,
            retryable=True,
            status_code=status_code,
        )
    if status_code in {500, 502, 503, 504}:
        return ModelProviderError(
            category=ModelProviderErrorCategory.UNAVAILABLE,
            retryable=True,
            status_code=status_code,
        )
    if status_code in {401, 403}:
        return ModelProviderError(
            category=ModelProviderErrorCategory.AUTHENTICATION,
            retryable=False,
            status_code=status_code,
        )
    if status_code in {400, 404}:
        return ModelProviderError(
            category=ModelProviderErrorCategory.INVALID_REQUEST,
            retryable=False,
            status_code=status_code,
        )
    return ModelProviderError(
        category=ModelProviderErrorCategory.UNKNOWN,
        retryable=False,
        status_code=status_code,
    )


def _normalize_usage_metadata(response: AIMessage) -> None:
    if response.usage_metadata is not None:
        return
    raw_usage = response.response_metadata.get("token_usage")
    if not isinstance(raw_usage, dict):
        return

    input_tokens = _token_count(raw_usage, "input_tokens", "prompt_tokens")
    output_tokens = _token_count(raw_usage, "output_tokens", "completion_tokens")
    total_tokens = _token_count(raw_usage, "total_tokens")
    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens
    if input_tokens is None and output_tokens is None and total_tokens is None:
        return
    response.usage_metadata = {
        "input_tokens": input_tokens or 0,
        "output_tokens": output_tokens or 0,
        "total_tokens": total_tokens or 0,
    }


def _token_count(raw_usage: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = raw_usage.get(key)
        if isinstance(value, int):
            return value
    return None
