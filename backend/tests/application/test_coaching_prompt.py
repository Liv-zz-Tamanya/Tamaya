from app.application.service.coaching_prompt import build_coaching_system_prompt


def test_coaching_prompt_preserves_base_policy():
    prompt = build_coaching_system_prompt()

    assert "건강냥" in prompt
    assert "반말" in prompt
    assert "먼저 공감" in prompt
    assert "진단·처방·약 권유는 절대 하지 않아" in prompt
    assert "고정된 체크리스트" in prompt
    assert "감정 라벨을 직접 붙이지 않아" in prompt


def test_coaching_prompt_adds_persona_without_overriding_safety_policy():
    prompt = build_coaching_system_prompt("부모님")

    assert "부모님" in prompt
    assert "진단·처방·약 권유는 절대 하지 않아" in prompt
