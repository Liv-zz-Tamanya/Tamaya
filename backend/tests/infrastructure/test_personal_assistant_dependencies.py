import pytest
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import ValidationError

from app.application.service.model_retry_policy import ModelRetryPolicy
from app.application.service.personal_assistant_timeout import PersonalAssistantTimeoutPolicy
from app.application.service.retrying_tool_calling_chat_model import RetryingToolCallingChatModel
from app.infrastructure.config import dependencies
from app.infrastructure.config.settings import Settings
from app.infrastructure.external.clova_tool_calling import ClovaToolCallingChatModel


async def test_tool_calling_chat_model_provider_uses_mock_model_in_mock_mode(monkeypatch):
    monkeypatch.setattr(dependencies.settings, "clova_mock_mode", True)

    model = dependencies.get_tool_calling_chat_model(
        x_clova_api_key=None,
        retry_policy=dependencies.get_model_retry_policy(),
    )
    response = await model.ainvoke([HumanMessage(content="안녕")], [])

    assert isinstance(model, RetryingToolCallingChatModel)
    assert isinstance(response, AIMessage)
    assert response.content


async def test_coaching_tool_calling_model_provider_uses_mock_model_in_mock_mode(monkeypatch):
    monkeypatch.setattr(dependencies.settings, "clova_mock_mode", True)

    model = dependencies.get_coaching_tool_calling_chat_model(
        x_clova_api_key=None,
        retry_policy=dependencies.get_model_retry_policy(),
    )
    response = await model.ainvoke([HumanMessage(content="안녕")], [])

    assert isinstance(model, RetryingToolCallingChatModel)
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


def test_model_retry_policy_provider_uses_settings_values(monkeypatch):
    monkeypatch.setattr(dependencies.settings, "personal_assistant_model_retry_max_attempts", 3)
    monkeypatch.setattr(
        dependencies.settings, "personal_assistant_model_retry_initial_backoff_seconds", 0.25
    )
    monkeypatch.setattr(
        dependencies.settings, "personal_assistant_model_retry_backoff_multiplier", 3.0
    )
    monkeypatch.setattr(
        dependencies.settings, "personal_assistant_model_retry_max_backoff_seconds", 1.0
    )

    policy = dependencies.get_model_retry_policy()

    assert policy == ModelRetryPolicy(3, 0.25, 3.0, 1.0)


def test_settings_reject_non_positive_personal_assistant_timeout():
    with pytest.raises(ValidationError):
        Settings(personal_assistant_model_call_timeout_seconds=0)


def test_settings_rejects_invalid_model_retry_backoff_range():
    with pytest.raises(ValidationError):
        Settings(
            personal_assistant_model_retry_initial_backoff_seconds=1,
            personal_assistant_model_retry_max_backoff_seconds=0.5,
        )


def test_tool_calling_chat_model_provider_uses_clova_adapter_with_real_key(monkeypatch):
    monkeypatch.setattr(dependencies.settings, "clova_mock_mode", False)

    model = dependencies.get_tool_calling_chat_model(
        x_clova_api_key="nv-user-key",
        retry_policy=dependencies.get_model_retry_policy(),
    )

    assert isinstance(model, RetryingToolCallingChatModel)
    assert isinstance(model._delegate, ClovaToolCallingChatModel)


def test_coaching_tool_calling_chat_model_provider_uses_coaching_generation_settings(
    monkeypatch,
):
    monkeypatch.setattr(dependencies.settings, "clova_mock_mode", False)

    model = dependencies.get_coaching_tool_calling_chat_model(
        x_clova_api_key="nv-user-key",
        retry_policy=dependencies.get_model_retry_policy(),
    )

    assert isinstance(model, RetryingToolCallingChatModel)
    assert isinstance(model._delegate, ClovaToolCallingChatModel)
    assert model._delegate._api_key == "nv-user-key"
    assert model._delegate._temperature == 0.6
    assert model._delegate._max_tokens == 300
