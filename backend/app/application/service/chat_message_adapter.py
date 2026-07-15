from collections.abc import Sequence
from typing import Protocol

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage


class ConversationMessage(Protocol):
    role: str
    content: str


def to_langchain_messages(messages: Sequence[ConversationMessage]) -> list[BaseMessage]:
    converted: list[BaseMessage] = []
    for message in messages:
        if message.role == "user":
            converted.append(HumanMessage(content=message.content))
        elif message.role == "assistant":
            converted.append(AIMessage(content=message.content))
        elif message.role == "system":
            converted.append(SystemMessage(content=message.content))
        else:
            raise ValueError(f"unsupported chat message role: {message.role}")
    return converted


def extract_ai_message_text(message: AIMessage) -> str:
    if message.tool_calls:
        raise ValueError("final AIMessage must not contain tool calls")

    content = message.content
    if isinstance(content, str):
        text = content.strip()
    elif isinstance(content, list):
        text = "".join(_content_block_text(block) for block in content).strip()
    else:
        raise ValueError("unsupported AIMessage content type")

    if not text:
        raise ValueError("final AIMessage content must not be empty")
    return text


def _content_block_text(block: str | dict) -> str:
    if isinstance(block, str):
        return block
    if isinstance(block, dict) and block.get("type") == "text":
        text = block.get("text")
        if isinstance(text, str):
            return text
    raise ValueError("unsupported AIMessage content block")
