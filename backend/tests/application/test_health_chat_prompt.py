from datetime import datetime

import anyio

from app.application.service.health_chat_prompt import build_health_chat_system_prompt
from app.infrastructure.external import clova_client


def test_health_chat_prompt_includes_core_policy():
    prompt = build_health_chat_system_prompt(tool_calling_enabled=False)

    assert "헬시" in prompt
    assert "삼성 헬스 데이터" in prompt
    assert "한국어 반말" in prompt
    assert "1~3문장" in prompt
    assert "수치는 저장된 건강 데이터" in prompt
    assert "그 날 데이터가 없어서 모르겠어" in prompt
    assert "의학적 진단은 하지 마" in prompt
    assert "처방이나 약물 변경" in prompt
    assert "데이터에 없는 사실이나 수치" in prompt


def test_health_chat_prompt_includes_tool_rules_when_tool_calling_enabled():
    prompt = build_health_chat_system_prompt(tool_calling_enabled=True)

    assert "search_health_records" in prompt
    assert "동일한 query와 limit" in prompt
    assert "Tool 이름, 내부 ID, JSON 원문" in prompt
    assert "일기 기억 검색 Tool은 Health Chat에서 사용할 수 없다고 가정" in prompt
    assert "[건강 데이터 기록]" not in prompt


def test_health_chat_prompt_includes_context_only_for_legacy_chat():
    prompt = build_health_chat_system_prompt(
        tool_calling_enabled=False,
        health_context=["- 2026-07-10: 9,144걸음"],
    )
    no_context_prompt = build_health_chat_system_prompt(
        tool_calling_enabled=False,
        health_context=None,
    )

    assert "[건강 데이터 기록]" in prompt
    assert "9,144걸음" in prompt
    assert "[건강 데이터 기록]" not in no_context_prompt


def test_health_clova_client_uses_shared_prompt_builder(monkeypatch):
    captured: dict = {}

    def fake_builder(**kwargs) -> str:
        captured.update(kwargs)
        return "health shared prompt"

    monkeypatch.setattr(clova_client, "build_health_chat_system_prompt", fake_builder)
    client = clova_client.HealthClovaClient(api_key="key", mock=False)
    messages = [
        clova_client.HealthMessage("user", "어제 걸음 수 알려줘", datetime(2026, 7, 15, 12, 0))
    ]

    async def fake_create(**kwargs):
        class _Message:
            content = " 9,144걸음이야 "

        class _Choice:
            message = _Message()

        class _Response:
            choices = [_Choice()]

        assert kwargs["messages"][0]["content"] == "health shared prompt"
        return _Response()

    monkeypatch.setattr(client._client.chat.completions, "create", fake_create)

    result = anyio.run(client.chat, messages, ["- 2026-07-10: 9,144걸음"])

    assert result == "9,144걸음이야"
    assert captured == {
        "tool_calling_enabled": False,
        "health_context": ["- 2026-07-10: 9,144걸음"],
    }


def test_health_greeting_mock_response_and_diary_prompt_are_unchanged():
    assert "헬시" in clova_client.HEALTH_CHAT_GREETING
    assert "건강 데이터 확인 기능" in clova_client.HEALTH_CHAT_MOCK_RESPONSE

    from app.application.service.diary_chat_prompt import build_diary_chat_system_prompt

    diary_prompt = build_diary_chat_system_prompt(
        max_turns=5,
        current_user_turn=1,
        suggest_finalize=False,
        tool_calling_enabled=True,
    )
    assert "이음이야" in diary_prompt
    assert "search_diary_memories" in diary_prompt
