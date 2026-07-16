import asyncio
from collections.abc import Awaitable, Callable, Sequence

from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.tools import BaseTool

from app.application.service.agent_execution_observability import (
    get_active_agent_execution_trace,
)
from app.application.service.model_provider_error import ModelProviderError
from app.application.service.model_retry_policy import ModelRetryPolicy
from app.application.service.tool_calling_chat_model import ToolCallingChatModel

Sleep = Callable[[float], Awaitable[None]]


class RetryingToolCallingChatModel(ToolCallingChatModel):
    def __init__(
        self,
        delegate: ToolCallingChatModel,
        policy: ModelRetryPolicy,
        *,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self._delegate = delegate
        self._policy = policy
        self._sleep = sleep

    async def ainvoke(
        self,
        messages: Sequence[BaseMessage],
        tools: Sequence[BaseTool],
    ) -> AIMessage:
        for attempt in range(1, self._policy.max_attempts + 1):
            trace = get_active_agent_execution_trace()
            if trace is not None:
                trace.record_model_attempt()
            try:
                return await self._delegate.ainvoke(messages, tools)
            except ModelProviderError as exc:
                if trace is not None:
                    trace.record_provider_error(exc.category.value)
                if not exc.retryable or attempt == self._policy.max_attempts:
                    raise
                if trace is not None:
                    trace.record_retry_attempt()
                await self._sleep(self._policy.backoff_seconds(attempt))

        raise RuntimeError("model retry attempts exhausted")
