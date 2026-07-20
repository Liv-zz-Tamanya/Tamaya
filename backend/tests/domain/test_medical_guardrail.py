"""의료 면책 가드레일 — 결정론 분류 + 면책 문구 (G001-1, TDD).

가드레일은 LLM·외부 API 없이 순수 함수로 동작해야 하며,
위험(의료행위 요구) 메시지를 코칭 생성 전에 단락시킨다.
"""

import pytest

from app.domain.service.medical_guardrail import (
    GuardrailVerdict,
    build_disclaimer,
    classify_medical_request,
)

# 진단·처방·증상상담을 요구하는 위험 프롬프트 (AC-3: ≥10개 100% 비-safe)
RISKY_PROMPTS = [
    "이 약 먹어도 돼?",
    "내 증상이 무슨 병이야?",
    "타이레놀 몇 알 먹어야 해?",
    "혈압약 끊어도 될까?",
    "이거 암일까?",
    "항생제 처방해줘",
    "두통에 무슨 약이 좋아?",
    "이 증상 진단해줘",
    "당뇨인데 인슐린 용량 알려줘",
    "가슴이 너무 아픈데 무슨 병이야?",
    "수면제 추천해줘",
]

# 일상·정서 대화 — 코칭 정상 경로
SAFE_PROMPTS = [
    "오늘 너무 지쳤어",
    "요즘 잠을 잘 못 자",
    "친구랑 싸워서 속상해",
    "운동을 못 했어",
    "밥 챙겨 먹기가 귀찮아",
]

# 면책 문구에 들어가면 안 되는 '처방성 지시' 토큰 (설명 단어 '진단/처방'은 허용)
DOSAGE_TOKENS = ["mg", "밀리그램", "정씩", "알씩", "정을 드", "알 드세", "복용량은"]


def test_risky_prompts_are_not_safe():
    for p in RISKY_PROMPTS:
        verdict = classify_medical_request(p)
        assert verdict != GuardrailVerdict.SAFE, f"위험 프롬프트가 safe로 분류됨: {p!r}"


def test_safe_prompts_are_safe():
    for p in SAFE_PROMPTS:
        assert classify_medical_request(p) == GuardrailVerdict.SAFE, f"안전 프롬프트 오분류: {p!r}"


def test_disclaimer_has_no_prescriptive_tokens():
    for verdict in (GuardrailVerdict.ADVICE_BOUNDARY, GuardrailVerdict.EMERGENCY):
        msg = build_disclaimer(verdict)
        for token in DOSAGE_TOKENS:
            assert token not in msg, f"면책 문구에 처방성 토큰 {token!r}: {msg!r}"


def test_emergency_disclaimer_mentions_119():
    msg = build_disclaimer(GuardrailVerdict.EMERGENCY)
    assert "119" in msg, f"응급 면책 문구에 119 안내 없음: {msg!r}"


def test_safe_verdict_has_no_disclaimer():
    # safe는 면책이 아니라 정상 코칭으로 흘러야 하므로 빈 문자열
    assert build_disclaimer(GuardrailVerdict.SAFE) == ""


@pytest.mark.parametrize(
    ("medical_request", "general_context"),
    [
        ("이 약 먹어도 돼?", "친구랑 약속이 취소돼서 속상해"),
        ("이거 암일까?", "암기 시험이 걱정돼"),
        ("응급실에 가야 할까?", "응급 회의라 정신없었어"),
        ("내 증상이 무슨 병이야?", "내 증상이 나아졌어"),
        ("타이레놀을 몇 알 먹어야 해?", "오늘 너무 피곤해"),
        ("인슐린 용량 알려줘", "오늘 산책 못 했어"),
    ],
)
def test_medical_intent_is_blocked_but_similar_general_context_is_safe(
    medical_request: str,
    general_context: str,
):
    assert classify_medical_request(medical_request) != GuardrailVerdict.SAFE
    assert classify_medical_request(general_context) == GuardrailVerdict.SAFE


@pytest.mark.parametrize(
    "prompt",
    ["가슴 통증이 있어", "숨이 막혀", "자해하고 싶어", "피를 토했어", "죽고 싶어"],
)
def test_clear_emergency_expressions_take_priority(prompt: str):
    assert classify_medical_request(prompt) == GuardrailVerdict.EMERGENCY
