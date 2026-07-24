"""의료 면책 가드레일 — 결정론 분류 + 고정 면책 문구.

LLM·외부 API 의존이 없는 순수 도메인 서비스. 코칭 생성 **전에** 의료행위(진단·처방·
증상상담) 요구를 단락(short-circuit)시키기 위한 분류기와, 모델이 개입하지 않는 고정 면책
문구를 제공한다. 안전 경로에 LLM을 두지 않아 분류·면책이 결정론적으로 보장된다.

설계 원칙(plan G001): 미검출(위험→safe)이 치명적이므로 과검출을 선호한다.
"""

from __future__ import annotations

import re
from enum import StrEnum


class GuardrailVerdict(StrEnum):
    """가드레일 판정. safe만 코칭 생성으로 진행하고, 나머지는 면책으로 단락된다."""

    SAFE = "safe"
    ADVICE_BOUNDARY = "advice_boundary"
    EMERGENCY = "emergency"


# 응급 신호는 실제 신체 위급 표현 또는 응급 도움 요청으로만 판정한다. 단어 "응급"만으로는
# 회의·업무 같은 일반 문맥을 구분할 수 없으므로 충분한 phrase 조합을 요구한다.
_EMERGENCY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"가슴\s*(?:통증|이?\s*(?:(?:너무|심하게)\s*)?아(?:프|파)\w*)"),
    re.compile(r"숨(?:이|을)?\s*(?:막혀|안\s*쉬|못\s*쉬|쉬기\s*어려|쉬어지)"),
    re.compile(r"의식\s*(?:이\s*)?(?:없|잃)"),
    re.compile(r"쓰러(?:졌|져|질|질\s*것)"),
    re.compile(r"자해\s*(?:하|하고|했|하고\s*싶)"),
    re.compile(r"피\s*(?:를\s*)?토"),
    re.compile(r"(?:응급실|119)\s*(?:에?\s*)?(?:가|필요|불러|연락)"),
)

# 진단은 병명 판단을 요청하는 경우에만 차단한다. "암기" 같은 일반 낱말과 단순 증상 서술은
# 여기서 매치되지 않는다.
_DIAGNOSTIC_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"무슨\s*병(?:이야|인가|인지|일까|인\s*것\s*같)"),
    re.compile(r"어떤\s*병(?:일|인).*가능성"),
    re.compile(r"병명\s*(?:이|을|은)?\s*(?:알려|말해|추측|진단|뭐)"),
    re.compile(r"진단\s*(?:좀\s*)?(?:해|해줘|받|부탁|필요)"),
    re.compile(r"암\s*(?:이|일|인)\s*(?:야|까|가|지|것\s*같|알려)"),
)

# 고신뢰 약물 대상만 인정한다. 모든 '…약' 단어를 매치하면 약속·계약·요약까지 약물로
# 오인하므로, 독립된 '약' 또는 제품에서 지원하는 명시적 약물 종류/이름으로 제한한다.
_MEDICATION_TARGET = re.compile(
    r"(?:감기약|혈압약|수면제|항생제|인슐린|타이레놀|의약품|약물|(?<![가-힣])약(?:을|은|이|도|만)?(?![가-힣]))"
)
_MEDICATION_REQUEST = re.compile(
    r"(?:"
    r"(?:더\s*)?먹어도\s*(?:돼|될까|되나)"
    r"|(?:몇\s*알|얼마나)\s*먹어야"
    r"|용량\s*(?:을?\s*)?(?:알려|물어|조절|어떻게|몇|얼마나)"
    r"|추천\s*해줘"
    r"|처방\s*(?:해줘|받고\s*싶)"
    r"|(?:끊어도|중단해도|바꿔도)\s*(?:돼|될까|되나)"
    r"|복용\s*(?:중인데\s*)?(?:괜찮아|돼|될까)"
    r"|무슨\s*약\s*(?:이|을)?\s*좋"
    r"|무슨\s*약\s*(?:을?\s*)?먹(?:어|어야)\s*(?:해|돼|될까|\?)"
    r")"
)
_OVERDOSE_SIGNAL = re.compile(
    r"(?:과다\s*복용|한꺼번에\s*(?:너무\s*)?많이\s*먹|너무\s*많이\s*먹|복용량.*(?:크게\s*)?초과)"
)
_SUICIDE_INTENT = re.compile(r"^(?:나(?:는|도)?\s*)?죽고\s*싶(?:어|어요|다)[.!?]?$")

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
    if _matches_emergency(normalized):
        return GuardrailVerdict.EMERGENCY
    if _matches_diagnosis_request(normalized):
        return GuardrailVerdict.ADVICE_BOUNDARY
    if _matches_medication_advice_request(normalized):
        return GuardrailVerdict.ADVICE_BOUNDARY
    return GuardrailVerdict.SAFE


def _matches_emergency(text: str) -> bool:
    return (
        any(pattern.search(text) for pattern in _EMERGENCY_PATTERNS)
        or _SUICIDE_INTENT.fullmatch(text) is not None
        or (_contains_medication_target(text) and _OVERDOSE_SIGNAL.search(text) is not None)
    )


def _matches_diagnosis_request(text: str) -> bool:
    return any(pattern.search(text) for pattern in _DIAGNOSTIC_PATTERNS)


def _matches_medication_advice_request(text: str) -> bool:
    return _contains_medication_target(text) and _MEDICATION_REQUEST.search(text) is not None


def _contains_medication_target(text: str) -> bool:
    return _MEDICATION_TARGET.search(text) is not None


def build_disclaimer(verdict: GuardrailVerdict) -> str:
    """판정에 대응하는 고정 면책 문구. safe는 면책이 아니므로 빈 문자열."""
    if verdict == GuardrailVerdict.EMERGENCY:
        return _EMERGENCY_DISCLAIMER
    if verdict == GuardrailVerdict.ADVICE_BOUNDARY:
        return _ADVICE_DISCLAIMER
    return ""


# ─── DIARY 위기 신호 (비차단 안내) ────────────────────────────────────────────
# 제품 결정(2026-07-23): diary 모드에서 위기 신호는 차단하지 않는다 — 일기는 감정을
# 꺼내놓는 공간이므로. 대신 응답에 공감 + 전문 상담 안내가 반드시 포함되게 한다.
# 미검출이 치명적이므로 과검출을 선호하되(G001), "힘들어 죽겠다" 같은 관용적 과장
# 표현('죽겠' 형태)은 매치하지 않는다.
_CRISIS_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"죽고\s*싶"),
    re.compile(r"죽어\s*버리"),
    re.compile(r"사라지고\s*싶"),
    re.compile(r"살고\s*싶지\s*않"),
    re.compile(r"그만\s*살"),
    re.compile(r"다\s*그만두고\s*싶"),
    re.compile(r"살아야\s*할\s*이유(?:를|가)?\s*모르"),
    re.compile(r"자해"),
    re.compile(r"자살"),
    re.compile(r"손목을?\s*(?:그(?:었|어|을)|긋)"),
    re.compile(r"(?:팔|다리|몸|허벅지)에\s*상처를?\s*(?:냈|내)"),
    re.compile(r"생을\s*마감"),
)

# 응답에 이 표지가 이미 있으면 상담 안내가 포함된 것으로 본다(중복 덧붙임 방지)
CRISIS_GUIDANCE_MARKERS: tuple[str, ...] = ("109", "1577", "1393", "상담")

_DIARY_CRISIS_GUIDANCE = (
    "혹시 마음이 많이 무거운 날엔 혼자 견디지 않아도 돼. "
    "자살예방상담전화 109(24시간, 무료)나 정신건강 위기상담 1577-0199에서 "
    "언제든 네 이야기를 들어줄 수 있어. 나도 여기서 계속 네 곁에 있을게."
)


def contains_crisis_signal(text: str) -> bool:
    """자해·자살 등 위기 신호를 결정론적으로 감지한다(과장 표현 '죽겠'은 제외)."""
    return any(pattern.search(text) for pattern in _CRISIS_PATTERNS)


def build_diary_crisis_guidance() -> str:
    """diary 위기 응답에 덧붙일 고정 상담 안내 문구(모델 미개입·결정론)."""
    return _DIARY_CRISIS_GUIDANCE


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
