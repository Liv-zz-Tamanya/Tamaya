from datetime import datetime

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.application.service.chat_message_adapter import (
    extract_ai_message_text,
    to_langchain_messages,
)
from app.domain.model.chat_message import ChatMessage


def _message(role: str, content: str) -> ChatMessage:
    return ChatMessage(role=role, content=content, created_at=datetime(2026, 7, 15, 12, 0))


def test_to_langchain_messages_preserves_roles_content_and_order():
    messages = [
        _message("system", "시스템"),
        _message("user", "사용자"),
        _message("assistant", "응답"),
    ]

    converted = to_langchain_messages(messages)

    assert [type(message) for message in converted] == [SystemMessage, HumanMessage, AIMessage]
    assert [message.content for message in converted] == ["시스템", "사용자", "응답"]
    assert [message.content for message in messages] == ["시스템", "사용자", "응답"]


def test_to_langchain_messages_rejects_unknown_role():
    with pytest.raises(ValueError, match="unsupported chat message role"):
        to_langchain_messages([_message("tool", "도구")])


def test_to_langchain_messages_handles_empty_list():
    assert to_langchain_messages([]) == []


def test_to_langchain_messages_does_not_duplicate_last_user_message():
    messages = [_message("assistant", "시작"), _message("user", "방금 보낸 메시지")]

    converted = to_langchain_messages(messages)

    assert len(converted) == 2
    assert isinstance(converted[-1], HumanMessage)
    assert converted[-1].content == "방금 보낸 메시지"


def test_extract_ai_message_text_returns_stripped_text():
    assert extract_ai_message_text(AIMessage(content="  응답이야  ")) == "응답이야"


def test_extract_ai_message_text_extracts_text_blocks():
    message = AIMessage(
        content=[{"type": "text", "text": " 첫 문장"}, {"type": "text", "text": " 둘째"}]
    )

    assert extract_ai_message_text(message) == "첫 문장 둘째"


def test_extract_ai_message_text_rejects_tool_calls_empty_and_unsupported_blocks():
    with pytest.raises(ValueError, match="tool calls"):
        extract_ai_message_text(
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "search_diary_memories",
                        "args": {"query": "x"},
                        "id": "call-1",
                        "type": "tool_call",
                    }
                ],
            )
        )
    with pytest.raises(ValueError, match="must not be empty"):
        extract_ai_message_text(AIMessage(content="   "))
    with pytest.raises(ValueError, match="unsupported"):
        extract_ai_message_text(AIMessage(content=[{"type": "image", "url": "x"}]))
