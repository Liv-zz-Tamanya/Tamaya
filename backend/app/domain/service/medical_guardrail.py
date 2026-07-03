"""의료 면책 가드레일 — 결정론 분류 + 고정 면책 문구.

LLM·외부 API 의존이 없는 순수 도메인 서비스. 코칭 생성 **전에** 의료행위(진단·처방·
증상상담) 요구를 단락(short-circuit)시키기 위한 분류기와, 모델이 개입하지 않는 고정 면책
문구를 제공한다. 안전 경로에 LLM을 두지 않아 분류·면책이 결정론적으로 보장된다.

설계 원칙(plan G001): 미검출(위험→safe)이 치명적이므로 과검출을 선호한다.
"""

from __future__ import annotations

from enum import StrEnum


class GuardrailVerdict(StrEnum):
    """가드레일 판정. safe만 코칭 생성으로 진행하고, 나머지는 면책으로 단락된다."""

    SAFE = "safe"
    ADVICE_BOUNDARY = "advice_boundary"
    EMERGENCY = "emergency"


# 응급 신호 — 즉시 119 안내 (의료 경계보다 우선 판정)
# 미검출이 치명적이므로 과검출을 선호 — 흉통은 '아프/아파' 활용형·통증 표현을 함께 커버한다.
_EMERGENCY_KEYWORDS: tuple[str, ...] = (
    "가슴이 아프",
    "가슴이 아파",
    "가슴이 너무 아프",
    "가슴이 너무 아파",
    "가슴 통증",
    "숨이 안 쉬",
    "숨이 막",
    "의식이 없",
    "쓰러졌",
    "쓰러질",
    "자해",
    "죽고 싶",
    "피를 토",
    "응급",
)

# 의료행위(진단·처방·약물·증상상담) 요구 신호
_MEDICAL_KEYWORDS: tuple[str, ...] = (
    "약",
    "처방",
    "진단",
    "무슨 병",
    "병이야",
    "암",
    "항생제",
    "인슐린",
    "용량",
    "수면제",
    "복용",
    "증상",
    "타이레놀",
    "혈압약",
    "몇 알",
    "먹어도 돼",
    "끊어도",
)

# 면책 문구(고정·결정론) — 진단/처방 '지시'를 담지 않는다.
_ADVICE_DISCLAIMER = (
    "나는 건강을 함께 돌보는 친구지, 의료 전문가는 아니야. "
    "그래서 어떤 병인지 판단하거나 약을 권하는 건 못 해. "
    "걱정되는 부분이 있으면 꼭 의사나 약사 같은 전문가와 상담해줘."
)

_EMERGENCY_DISCLAIMER = (
    "지금 많이 위급한 상황 같아. 망설이지 말고 바로 119에 연락하거나 "
    "가까운 응급실로 가줘. 나는 곁에 있을게."
)


def classify_medical_request(text: str) -> GuardrailVerdict:
    """메시지를 결정론적으로 분류한다. 응급 > 의료경계 > 안전 순으로 판정."""
    normalized = text.strip()
    if any(keyword in normalized for keyword in _EMERGENCY_KEYWORDS):
        return GuardrailVerdict.EMERGENCY
    if any(keyword in normalized for keyword in _MEDICAL_KEYWORDS):
        return GuardrailVerdict.ADVICE_BOUNDARY
    return GuardrailVerdict.SAFE


def build_disclaimer(verdict: GuardrailVerdict) -> str:
    """판정에 대응하는 고정 면책 문구. safe는 면책이 아니므로 빈 문자열."""
    if verdict == GuardrailVerdict.EMERGENCY:
        return _EMERGENCY_DISCLAIMER
    if verdict == GuardrailVerdict.ADVICE_BOUNDARY:
        return _ADVICE_DISCLAIMER
    return ""


# 생성된 응답에 섞이면 안 되는 처방성 지시 토큰 (post-generation tripwire용)
_PRESCRIPTIVE_TOKENS: tuple[str, ...] = (
    "mg",
    "밀리그램",
    "정씩",
    "알씩",
    "정을 드",
    "알 드세",
    "복용량",
)


def contains_prescriptive_content(text: str) -> bool:
    """생성 응답에 처방성 지시(용량·복용 등)가 섞였는지 검사한다(결정론)."""
    return any(token in text for token in _PRESCRIPTIVE_TOKENS)
