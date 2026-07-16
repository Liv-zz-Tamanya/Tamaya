import pytest
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import ValidationError

from app.application.service.personal_assistant_timeout import PersonalAssistantTimeoutPolicy
from app.infrastructure.config import dependencies
from app.infrastructure.config.settings import Settings
from app.infrastructure.external.clova_tool_calling import ClovaToolCallingChatModel


async def test_tool_calling_chat_model_provider_uses_mock_model_in_mock_mode(monkeypatch):
    monkeypatch.setattr(dependencies.settings, "clova_mock_mode", True)

    model = dependencies.get_tool_calling_chat_model(x_clova_api_key=None)
    response = await model.ainvoke([HumanMessage(content="안녕")], [])

    assert isinstance(response, AIMessage)
    assert response.content


async def test_coaching_tool_calling_model_provider_uses_mock_model_in_mock_mode(monkeypatch):
    monkeypatch.setattr(dependencies.settings, "clova_mock_mode", True)

    model = dependencies.get_coaching_tool_calling_chat_model(x_clova_api_key=None)
    response = await model.ainvoke([HumanMessage(content="안녕")], [])

    assert isinstance(response, AIMessage)
    assert response.content


def test_timeout_policy_provider_uses_settings_values(monkeypatch):
    monkeypatch.setattr(
        dependencies.settings, "personal_assistant_model_call_timeout_seconds", 20.0
    )
    monkeypatch.setattr(
        dependencies.settings, "personal_assistant_tool_round_timeout_seconds", 12.0
    )
    monkeypatch.setattr(dependencies.settings, "personal_assistant_execution_timeout_seconds", 35.0)

    policy = dependencies.get_personal_assistant_timeout_policy()

    assert policy == PersonalAssistantTimeoutPolicy(20.0, 12.0, 35.0)


def test_settings_reject_non_positive_personal_assistant_timeout():
    with pytest.raises(ValidationError):
        Settings(personal_assistant_model_call_timeout_seconds=0)


def test_tool_calling_chat_model_provider_uses_clova_adapter_with_real_key(monkeypatch):
    monkeypatch.setattr(dependencies.settings, "clova_mock_mode", False)

    model = dependencies.get_tool_calling_chat_model(x_clova_api_key="nv-user-key")

    assert isinstance(model, ClovaToolCallingChatModel)


def test_coaching_tool_calling_chat_model_provider_uses_coaching_generation_settings(
    monkeypatch,
):
    monkeypatch.setattr(dependencies.settings, "clova_mock_mode", False)

    model = dependencies.get_coaching_tool_calling_chat_model(x_clova_api_key="nv-user-key")

    assert isinstance(model, ClovaToolCallingChatModel)
    assert model._api_key == "nv-user-key"
    assert model._temperature == 0.6
    assert model._max_tokens == 300
