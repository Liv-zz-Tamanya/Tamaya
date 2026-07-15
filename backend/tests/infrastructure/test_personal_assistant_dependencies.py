from langchain_core.messages import AIMessage, HumanMessage

from app.infrastructure.config import dependencies
from app.infrastructure.external.clova_tool_calling import ClovaToolCallingChatModel


async def test_tool_calling_chat_model_provider_uses_mock_model_in_mock_mode(monkeypatch):
    monkeypatch.setattr(dependencies.settings, "clova_mock_mode", True)

    model = dependencies.get_tool_calling_chat_model(x_clova_api_key=None)
    response = await model.ainvoke([HumanMessage(content="안녕")], [])

    assert isinstance(response, AIMessage)
    assert response.content


def test_tool_calling_chat_model_provider_uses_clova_adapter_with_real_key(monkeypatch):
    monkeypatch.setattr(dependencies.settings, "clova_mock_mode", False)

    model = dependencies.get_tool_calling_chat_model(x_clova_api_key="nv-user-key")

    assert isinstance(model, ClovaToolCallingChatModel)
