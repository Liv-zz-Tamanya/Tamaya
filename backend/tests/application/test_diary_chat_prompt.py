from datetime import datetime

import pytest

from app.application.service.diary_chat_prompt import (
    DiaryConversationContext,
    build_diary_chat_system_prompt,
)
from app.infrastructure.external import clova_client


def test_diary_chat_prompt_includes_turn_policy_without_finalize_hint():
    prompt = build_diary_chat_system_prompt(
        max_turns=5,
        current_user_turn=2,
        suggest_finalize=False,
        tool_calling_enabled=True,
    )

    assert "이 회고 대화는 5턴" in prompt
    assert "[현재 2턴째 / 5턴]" in prompt
    assert "아직 마무리 턴이 아니야" in prompt
    assert "절대 대화를 끝내거나 작별" in prompt
    assert "search_diary_memories" in prompt
    assert "Tool 결과에 없는 날짜, 인물, 장소, 사건을 만들지 마" in prompt


def test_diary_chat_prompt_includes_finalize_policy():
    prompt = build_diary_chat_system_prompt(
        max_turns=3,
        current_user_turn=2,
        suggest_finalize=True,
        tool_calling_enabled=True,
    )

    assert "이 회고 대화는 3턴" in prompt
    assert "[마무리 지시" in prompt
    assert "새 질문을 던지지 마" in prompt
    assert "일기로 정리해볼까" in prompt


def test_diary_chat_prompt_omits_tool_rules_for_legacy_clova_chat():
    prompt = build_diary_chat_system_prompt(
        max_turns=5,
        current_user_turn=1,
        suggest_finalize=False,
        tool_calling_enabled=False,
    )

    assert "search_diary_memories" not in prompt


def test_diary_conversation_context_validates_turn_values():
    with pytest.raises(ValueError, match="max_turns"):
        DiaryConversationContext(max_turns=0, current_user_turn=1, suggest_finalize=False)
    with pytest.raises(ValueError, match="current_user_turn"):
        DiaryConversationContext(max_turns=5, current_user_turn=0, suggest_finalize=False)
    with pytest.raises(ValueError, match="must not exceed"):
        DiaryConversationContext(max_turns=5, current_user_turn=6, suggest_finalize=False)


def test_clova_client_uses_shared_diary_prompt_builder(monkeypatch):
    captured: dict = {}

    def fake_builder(**kwargs) -> str:
        captured.update(kwargs)
        return "shared prompt"

    monkeypatch.setattr(clova_client, "build_diary_chat_system_prompt", fake_builder)
    client = clova_client.ClovaClient(api_key="key", mock=False)
    messages = [
        clova_client.ChatMessage("assistant", "시작", datetime(2026, 7, 15, 12, 0)),
        clova_client.ChatMessage("user", "오늘 이야기", datetime(2026, 7, 15, 12, 1)),
    ]

    async def fake_create(**kwargs):
        class _Message:
            content = " 응답 "

        class _Choice:
            message = _Message()

        class _Response:
            choices = [_Choice()]

        assert kwargs["messages"][0]["content"] == "shared prompt"
        return _Response()

    monkeypatch.setattr(client._client.chat.completions, "create", fake_create)

    import anyio

    result = anyio.run(client.chat, messages, False, 5)

    assert result == "응답"
    assert captured == {
        "max_turns": 5,
        "current_user_turn": 1,
        "suggest_finalize": False,
        "tool_calling_enabled": False,
    }


def test_clova_client_initial_greeting_uses_valid_turn_context(monkeypatch):
    captured: dict = {}

    def fake_builder(**kwargs) -> str:
        captured.update(kwargs)
        return "shared prompt"

    monkeypatch.setattr(clova_client, "build_diary_chat_system_prompt", fake_builder)
    client = clova_client.ClovaClient(api_key="key", mock=False)

    async def fake_create(**kwargs):
        class _Message:
            content = " 안녕 "

        class _Choice:
            message = _Message()

        class _Response:
            choices = [_Choice()]

        return _Response()

    monkeypatch.setattr(client._client.chat.completions, "create", fake_create)

    import anyio

    assert anyio.run(client.chat, [], False, 5) == "안녕"
    assert captured["current_user_turn"] == 1


def test_health_prompt_is_not_changed_by_diary_prompt_builder():
    from app.application.service.health_chat_prompt import build_health_chat_system_prompt

    health_prompt = build_health_chat_system_prompt(tool_calling_enabled=True)
    assert "헬시" in health_prompt
    assert "search_diary_memories" not in health_prompt
