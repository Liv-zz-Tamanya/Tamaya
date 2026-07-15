from collections.abc import Callable, Sequence
from typing import Protocol

from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langchain_naver import ChatClovaX

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
        response = await runnable.ainvoke(list(messages))
        if not isinstance(response, AIMessage):
            raise TypeError("CLOVA tool-calling model must return AIMessage")
        return response
