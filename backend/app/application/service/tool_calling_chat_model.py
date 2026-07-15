from abc import ABC, abstractmethod
from collections.abc import Sequence

from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.tools import BaseTool


class ToolCallingChatModel(ABC):
    @abstractmethod
    async def ainvoke(
        self,
        messages: Sequence[BaseMessage],
        tools: Sequence[BaseTool],
    ) -> AIMessage: ...
