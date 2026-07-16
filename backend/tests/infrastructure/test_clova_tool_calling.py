from __future__ import annotations

from collections.abc import Sequence

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.application.service.tool_calling_chat_model import ToolCallingChatModel
from app.infrastructure.config.settings import settings
from app.infrastructure.external.clova_tool_calling import ClovaToolCallingChatModel


class _ToolInput(BaseModel):
    query: str = Field(description="Search query")


async def _sample_tool(query: str) -> dict:
    raise AssertionError("Tool must not be executed by the model adapter")


def _tool(name: str = "search_diary_memories") -> StructuredTool:
    return StructuredTool.from_function(
        coroutine=_sample_tool,
        name=name,
        description=f"{name} description",
        args_schema=_ToolInput,
    )


class _FakeBoundModel:
    def __init__(self, parent: _FakeChatModel, response: AIMessage | Exception) -> None:
        self._parent = parent
        self._response = response

    async def ainvoke(self, messages):
        self._parent.bound_ainvoke_calls.append(messages)
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


class _FakeChatModel:
    instances: list[_FakeChatModel] = []

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.bind_calls: list[dict] = []
        self.ainvoke_calls: list[list] = []
        self.bound_ainvoke_calls: list[list] = []
        self.response: AIMessage | Exception = AIMessage(content="default")
        _FakeChatModel.instances.append(self)

    def bind_tools(self, tools: Sequence[StructuredTool], **kwargs) -> _FakeBoundModel:
        self.bind_calls.append({"tools": list(tools), "kwargs": kwargs})
        return _FakeBoundModel(self, self.response)

    async def ainvoke(self, messages):
        self.ainvoke_calls.append(messages)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


@pytest.fixture(autouse=True)
def _reset_fake_instances():
    _FakeChatModel.instances = []


def test_tool_calling_chat_model_contract_is_async():
    assert issubclass(ClovaToolCallingChatModel, ToolCallingChatModel)
    assert hasattr(ToolCallingChatModel, "ainvoke")


def test_clova_tool_calling_model_initializes_with_explicit_values():
    model = ClovaToolCallingChatModel(
        model="HCX-005",
        api_key="nv-explicit",
        base_url="https://example.com/v1",
        temperature=0.1,
        max_tokens=2048,
        timeout=7,
        chat_model_factory=_FakeChatModel,
    )

    assert repr(model) == (
        "ClovaToolCallingChatModel(model='HCX-005', base_url='https://example.com/v1', "
        "temperature=0.1, max_tokens=2048, timeout=7, api_key='***')"
    )
    assert "nv-explicit" not in repr(model)
    assert _FakeChatModel.instances[0].kwargs == {
        "model": "HCX-005",
        "api_key": "nv-explicit",
        "base_url": "https://example.com/v1",
        "temperature": 0.1,
        "max_tokens": 2048,
        "timeout": 7,
        "max_retries": 0,
    }


def test_clova_tool_calling_model_uses_settings_defaults(monkeypatch):
    monkeypatch.setattr(settings, "clova_model", "HCX-DEFAULT")
    monkeypatch.setattr(settings, "clova_api_key", "nv-default")
    monkeypatch.setattr(settings, "clova_base_url", "https://default.example/v1")
    monkeypatch.setattr(settings, "clova_agent_temperature", 0.3)
    monkeypatch.setattr(settings, "clova_agent_max_tokens", 1024)
    monkeypatch.setattr(settings, "clova_agent_timeout_seconds", 11.0)

    ClovaToolCallingChatModel(chat_model_factory=_FakeChatModel)

    assert _FakeChatModel.instances[0].kwargs == {
        "model": "HCX-DEFAULT",
        "api_key": "nv-default",
        "base_url": "https://default.example/v1",
        "temperature": 0.3,
        "max_tokens": 1024,
        "timeout": 11.0,
        "max_retries": 0,
    }


def test_clova_tool_calling_model_keeps_byok_instances_separate():
    ClovaToolCallingChatModel(api_key="nv-user-a", chat_model_factory=_FakeChatModel)
    ClovaToolCallingChatModel(api_key="nv-user-b", chat_model_factory=_FakeChatModel)

    assert _FakeChatModel.instances[0].kwargs["api_key"] == "nv-user-a"
    assert _FakeChatModel.instances[1].kwargs["api_key"] == "nv-user-b"
    assert _FakeChatModel.instances[0] is not _FakeChatModel.instances[1]


async def test_clova_tool_calling_model_binds_tools_without_executing_them():
    model = ClovaToolCallingChatModel(chat_model_factory=_FakeChatModel)
    fake_chat = _FakeChatModel.instances[0]
    fake_chat.response = AIMessage(content="", tool_calls=[])
    tools = [_tool("search_diary_memories"), _tool("search_health_records")]
    messages = [HumanMessage(content="예전 발표 기억 찾아줘")]

    response = await model.ainvoke(messages, tools)

    assert response is fake_chat.response
    assert len(fake_chat.bind_calls) == 1
    assert [tool.name for tool in fake_chat.bind_calls[0]["tools"]] == [
        "search_diary_memories",
        "search_health_records",
    ]
    assert fake_chat.bind_calls[0]["kwargs"] == {"tool_choice": "auto"}
    assert fake_chat.bind_calls[0]["tools"][0].args_schema is _ToolInput
    assert fake_chat.bound_ainvoke_calls == [messages]
    assert fake_chat.ainvoke_calls == []


async def test_clova_tool_calling_model_allows_empty_tool_list_as_plain_chat():
    model = ClovaToolCallingChatModel(chat_model_factory=_FakeChatModel)
    fake_chat = _FakeChatModel.instances[0]
    fake_chat.response = AIMessage(content="일반 응답")
    messages = [HumanMessage(content="오늘 기분이 복잡해")]

    response = await model.ainvoke(messages, [])

    assert response.content == "일반 응답"
    assert response.tool_calls == []
    assert fake_chat.bind_calls == []
    assert fake_chat.ainvoke_calls == [messages]


async def test_clova_tool_calling_model_preserves_tool_calls_content_and_order():
    tool_calls = [
        {
            "name": "search_diary_memories",
            "args": {"query": "발표 기억", "limit": 2},
            "id": "call-1",
            "type": "tool_call",
        },
        {
            "name": "search_health_records",
            "args": {"query": "수면 기록", "limit": 1},
            "id": "call-2",
            "type": "tool_call",
        },
    ]
    model = ClovaToolCallingChatModel(chat_model_factory=_FakeChatModel)
    fake_chat = _FakeChatModel.instances[0]
    fake_chat.response = AIMessage(content="도구를 확인할게.", tool_calls=tool_calls)

    response = await model.ainvoke([HumanMessage(content="기억 찾아줘")], [_tool()])

    assert response is fake_chat.response
    assert response.content == "도구를 확인할게."
    assert response.tool_calls == tool_calls
    assert [call["id"] for call in response.tool_calls] == ["call-1", "call-2"]
    assert [call["name"] for call in response.tool_calls] == [
        "search_diary_memories",
        "search_health_records",
    ]
    assert response.tool_calls[0]["args"] == {"query": "발표 기억", "limit": 2}


async def test_clova_tool_calling_model_preserves_general_response_content():
    model = ClovaToolCallingChatModel(chat_model_factory=_FakeChatModel)
    fake_chat = _FakeChatModel.instances[0]
    fake_chat.response = AIMessage(content="")

    response = await model.ainvoke([HumanMessage(content="빈 응답도 유지")], [_tool()])

    assert response.content == ""
    assert response.tool_calls == []


async def test_clova_tool_calling_model_normalizes_provider_token_usage():
    model = ClovaToolCallingChatModel(chat_model_factory=_FakeChatModel)
    fake_chat = _FakeChatModel.instances[0]
    fake_chat.response = AIMessage(
        content="응답",
        response_metadata={
            "token_usage": {
                "prompt_tokens": 3,
                "completion_tokens": 4,
            }
        },
    )

    response = await model.ainvoke([HumanMessage(content="질문")], [])

    assert response.usage_metadata == {
        "input_tokens": 3,
        "output_tokens": 4,
        "total_tokens": 7,
    }


async def test_clova_tool_calling_model_preserves_message_sequence_and_tool_message_link():
    previous_tool_call = {
        "name": "search_diary_memories",
        "args": {"query": "발표"},
        "id": "call-previous",
        "type": "tool_call",
    }
    messages = [
        SystemMessage(content="system"),
        HumanMessage(content="human"),
        AIMessage(content="", tool_calls=[previous_tool_call]),
        ToolMessage(content='{"count": 0, "items": []}', tool_call_id="call-previous"),
        HumanMessage(content="다시 정리해줘"),
    ]
    model = ClovaToolCallingChatModel(chat_model_factory=_FakeChatModel)
    fake_chat = _FakeChatModel.instances[0]
    fake_chat.response = AIMessage(content="정리했어")

    await model.ainvoke(messages, [_tool()])

    assert fake_chat.bound_ainvoke_calls == [messages]
    assert isinstance(fake_chat.bound_ainvoke_calls[0][0], SystemMessage)
    assert isinstance(fake_chat.bound_ainvoke_calls[0][1], HumanMessage)
    assert isinstance(fake_chat.bound_ainvoke_calls[0][2], AIMessage)
    assert isinstance(fake_chat.bound_ainvoke_calls[0][3], ToolMessage)
    assert fake_chat.bound_ainvoke_calls[0][3].tool_call_id == "call-previous"


async def test_clova_tool_calling_model_propagates_provider_errors():
    model = ClovaToolCallingChatModel(chat_model_factory=_FakeChatModel)
    fake_chat = _FakeChatModel.instances[0]
    fake_chat.response = RuntimeError("provider failed")

    with pytest.raises(RuntimeError, match="provider failed"):
        await model.ainvoke([HumanMessage(content="질문")], [_tool()])


async def test_clova_tool_calling_model_rejects_non_ai_message_response():
    model = ClovaToolCallingChatModel(chat_model_factory=_FakeChatModel)
    fake_chat = _FakeChatModel.instances[0]
    fake_chat.response = "not ai message"

    with pytest.raises(TypeError, match="must return AIMessage"):
        await model.ainvoke([HumanMessage(content="질문")], [_tool()])
