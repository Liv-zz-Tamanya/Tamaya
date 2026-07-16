"""코칭 메시지 usecase — PersonalAssistantAgent 전환 + history 전달."""

from datetime import datetime
from uuid import UUID, uuid4

import pytest
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.tools import BaseTool

from app.application.service.personal_assistant_timeout import PersonalAssistantTimeoutError
from app.application.service.tool_calling_chat_model import ToolCallingChatModel
from app.application.usecase.personal_assistant_agent_factory import PersonalAssistantAgentFactory
from app.application.usecase.send_coaching_message import SendCoachingMessageUseCase
from app.domain.model.chat_message import ChatMessage
from app.domain.service.medical_guardrail import GuardrailVerdict, build_disclaimer


class _FakeToolCallingModel(ToolCallingChatModel):
    def __init__(self, responses: list[AIMessage | Exception]) -> None:
        self.responses = responses
        self.calls: list[dict] = []

    async def ainvoke(self, messages: list[BaseMessage], tools: list[BaseTool]) -> AIMessage:
        self.calls.append({"messages": list(messages), "tools": list(tools)})
        if not self.responses:
            raise AssertionError("unexpected model call")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class _FakeDiaryQuery:
    async def search_similar(self, *args, **kwargs) -> list:
        raise AssertionError("coaching mode must not use diary tools")


class _FakeHealthQuery:
    async def search_similar(self, *args, **kwargs) -> list:
        raise AssertionError("coaching mode must not use health tools")


class _FailingExtract:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def execute(self, **kwargs) -> None:
        self.calls.append(kwargs)
        raise RuntimeError("db down")


class _SpyExtract:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def execute(self, **kwargs) -> None:
        self.calls.append(kwargs)


def _factory(model: _FakeToolCallingModel) -> PersonalAssistantAgentFactory:
    return PersonalAssistantAgentFactory(model, _FakeDiaryQuery(), _FakeHealthQuery())


def _uc(
    model: _FakeToolCallingModel,
    extract_signals=None,
) -> SendCoachingMessageUseCase:
    return SendCoachingMessageUseCase(_factory(model), extract_signals)


async def test_safe_message_returns_personal_assistant_reply_without_tools():
    model = _FakeToolCallingModel([AIMessage(content="오늘은 푹 쉬어요")])

    reply = await _uc(model).execute(device_id="dev-1", message="오늘 너무 지쳤어", history=[])

    assert reply == "오늘은 푹 쉬어요"
    assert len(model.calls) == 1
    assert model.calls[0]["tools"] == []
    assert [message.content for message in model.calls[0]["messages"][1:]] == ["오늘 너무 지쳤어"]


async def test_risky_message_short_circuits_to_disclaimer_without_model_call():
    model = _FakeToolCallingModel([])

    reply = await _uc(model).execute(device_id="dev-1", message="이 약 먹어도 돼?", history=[])

    assert reply == build_disclaimer(GuardrailVerdict.ADVICE_BOUNDARY)
    assert "전문가" in reply
    assert model.calls == []


async def test_emergency_message_short_circuits_to_emergency_disclaimer():
    model = _FakeToolCallingModel([])

    reply = await _uc(model).execute(
        device_id="dev-1",
        message="가슴이 너무 아프고 숨이 막혀",
        history=[],
    )

    assert reply == build_disclaimer(GuardrailVerdict.EMERGENCY)
    assert "119" in reply
    assert "응급실" in reply
    assert model.calls == []


async def test_prescriptive_model_output_is_replaced_by_disclaimer():
    model = _FakeToolCallingModel([AIMessage(content="하루 500mg씩 드세요")])

    reply = await _uc(model).execute(device_id="dev-1", message="오늘 너무 지쳤어", history=[])

    assert reply == build_disclaimer(GuardrailVerdict.ADVICE_BOUNDARY)
    assert "mg" not in reply
    assert len(model.calls) == 1


async def test_current_message_appended_once_to_history_for_model():
    model = _FakeToolCallingModel([AIMessage(content="응 알겠어요")])
    history = [
        ChatMessage(role="user", content="안녕", created_at=datetime.now()),
        ChatMessage(role="assistant", content="안녕!", created_at=datetime.now()),
    ]

    await _uc(model).execute(device_id="dev-1", message="오늘 힘들었어", history=history)

    assert [message.content for message in model.calls[0]["messages"][1:]] == [
        "안녕",
        "안녕!",
        "오늘 힘들었어",
    ]


async def test_persona_is_threaded_to_coaching_prompt():
    model = _FakeToolCallingModel([AIMessage(content="부모님 톤 응답")])

    await _uc(model).execute(
        device_id="dev-1",
        message="오늘 지쳤어",
        history=[],
        persona="부모님",
    )

    system_message = model.calls[0]["messages"][0]
    assert "건강냥" in system_message.content
    assert "부모님" in system_message.content


async def test_signal_extraction_failure_does_not_break_reply():
    model = _FakeToolCallingModel([AIMessage(content="괜찮아요")])
    extract = _FailingExtract()
    uc = _uc(model, extract)

    reply = await uc.execute(device_id="dev-1", message="오늘 힘들었어", history=[])

    assert reply == "괜찮아요"
    assert extract.calls[0]["device_id"] == "dev-1"


async def test_authenticated_device_id_and_session_id_are_passed_to_signal_extraction():
    model = _FakeToolCallingModel([AIMessage(content="괜찮아요")])
    extract = _SpyExtract()
    uc = _uc(model, extract)
    session_id = uuid4()

    reply = await uc.execute(
        device_id="device-A",
        message="오늘 힘들었어",
        history=[],
        session_id=session_id,
    )

    assert reply == "괜찮아요"
    assert len(extract.calls) == 1
    call = extract.calls[0]
    assert call["device_id"] == "device-A"
    assert call["session_id"] == session_id
    assert isinstance(call["session_id"], UUID)
    assert [message.role for message in call["messages"]] == ["user", "assistant"]
    assert call["messages"][0].content == "오늘 힘들었어"
    assert call["messages"][1].content == "괜찮아요"


async def test_missing_session_id_generates_session_id_for_signal_extraction():
    model = _FakeToolCallingModel([AIMessage(content="괜찮아요")])
    extract = _SpyExtract()

    await _uc(model, extract).execute(device_id="device-A", message="오늘 힘들었어", history=[])

    assert isinstance(extract.calls[0]["session_id"], UUID)


async def test_blank_device_id_is_rejected():
    model = _FakeToolCallingModel([AIMessage(content="괜찮아요")])

    with pytest.raises(ValueError, match="device_id is required"):
        await _uc(model).execute(device_id="   ", message="오늘 힘들었어", history=[])


async def test_model_error_is_propagated_without_signal_extraction():
    model = _FakeToolCallingModel([RuntimeError("model failed")])
    extract = _SpyExtract()

    with pytest.raises(RuntimeError, match="model failed"):
        await _uc(model, extract).execute(
            device_id="dev-1",
            message="오늘 너무 지쳤어",
            history=[],
        )

    assert len(model.calls) == 1
    assert extract.calls == []


async def test_agent_timeout_is_propagated_without_signal_extraction():
    model = _FakeToolCallingModel([PersonalAssistantTimeoutError("execution")])
    extract = _SpyExtract()

    with pytest.raises(PersonalAssistantTimeoutError) as error:
        await _uc(model, extract).execute(
            device_id="dev-1",
            message="오늘 너무 지쳤어",
            history=[],
        )

    assert error.value.stage == "execution"
    assert len(model.calls) == 1
    assert extract.calls == []
