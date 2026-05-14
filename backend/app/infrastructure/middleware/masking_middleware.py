"""
마스킹 미들웨어 spec — liv-I4 (마스킹 ≥ 95%) Week 1 자리 확보
Week 2 본 구현 예정: FE에서 토큰 치환된 텍스트 → BE regex 화이트리스트 검증 → 위반 시 422

아키텍처 (R-2026-04-30-01 §3):
  [Device] 온디바이스 DLP 마스킹 → 토큰 치환 텍스트만 POST
  [BE] regex 화이트리스트 검증 → 위반 시 422 + 본문 폐기 (로그 미기록)
  [HCX] 토큰 포함 텍스트 처리 (unmask 불가 — private-first)

토큰 형식 (FE 동일):
  [NAME_<n>], [ORG_<n>], [LOC_<n>], [CONTACT_<n>], [NUM_<n>], [DATE_<n>]

Week 1 구현 범위: regex spec 정의 + 검증 함수 (미들웨어 등록은 Week 2)
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# ─── 허용 토큰 패턴 (FE 마스킹 출력 형식) ──────────────────────────────────────
PII_TOKEN_PATTERN = re.compile(r"\[(NAME|ORG|LOC|CONTACT|NUM|DATE)_\d+\]")

# ─── 원문 PII 탐지 휴리스틱 (violation 검출 — 위반 시 422) ────────────────────
# 아래 5종: 전화·이메일·주민번호·계좌·주소
_RAW_PII_PATTERNS: list[tuple[str, re.Pattern]] = [
    # 1. 전화번호 (010-xxxx-xxxx, 02-xxx-xxxx 등)
    ("phone",    re.compile(r"0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4}")),
    # 2. 이메일
    ("email",    re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")),
    # 3. 주민등록번호 (6자리-7자리, 뒷자리 첫 숫자 1~4)
    ("rrn",      re.compile(r"\d{6}[-\s]?[1-4]\d{6}")),
    # 4. 계좌번호 (10~16자리 숫자, 하이픈 포함)
    ("account",  re.compile(r"\d{3,6}[-\s]?\d{2,6}[-\s]?\d{2,6}")),
    # 5. 한국 도로명 주소 패턴 (시·도 + 로/길/대로)
    ("address",  re.compile(r"(서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주).{1,20}(로|길|대로)\s?\d+")),
]


@dataclass
class MaskingValidationResult:
    token_count: int        # 마스킹 토큰 수
    violation_count: int    # 원문 PII 탐지 건수
    violations: list[str]   # 탐지된 패턴 종류 (로그용, PII 본문 미포함)
    is_valid: bool          # True = 통과, False = 422 반환


def validate_masked_text(text: str) -> MaskingValidationResult:
    """
    마스킹 텍스트 검증.
    - 원문 PII 탐지 시 violation_count > 0 → 422 + 본문 폐기
    - 로그에는 위반 패턴 종류만 기록 (본문 미기록 — liv-I1 Private-First)
    """
    token_count = len(PII_TOKEN_PATTERN.findall(text))
    violations: list[str] = []
    for name, pattern in _RAW_PII_PATTERNS:
        if pattern.search(text):
            violations.append(name)

    violation_count = len(violations)
    return MaskingValidationResult(
        token_count=token_count,
        violation_count=violation_count,
        violations=violations,
        is_valid=violation_count == 0,
    )


# ─── Week 2 구현 예정: FastAPI Middleware 등록 ──────────────────────────────────
# 아래 클래스는 Week 2에 app/main.py에 등록
# app.add_middleware(MaskingValidationMiddleware, protected_paths=["/api/v1/chat"])
#
# class MaskingValidationMiddleware(BaseHTTPMiddleware):
#     async def dispatch(self, request: Request, call_next):
#         if request.url.path in self.protected_paths:
#             body = await request.body()
#             text = ... # body에서 content 필드 추출
#             result = validate_masked_text(text)
#             if not result.is_valid:
#                 logger.warning("PII 위반 탐지: %s (본문 폐기)", result.violations)
#                 return JSONResponse(
#                     status_code=422,
#                     content={"detail": "마스킹되지 않은 개인정보가 포함된 요청은 처리할 수 없습니다."}
#                 )
#         return await call_next(request)


# ─── A5 메트릭 정의 (liv-I4 검증 대상) ─────────────────────────────────────────
# 측정은 Phase 1 실증(6/4~) 테스트셋 1,000건 대상
#
# | 메트릭                  | 정의                      | Target   |
# |------------------------|--------------------------|----------|
# | pii_token_count        | 마스킹 토큰/요청            | —        |
# | pii_violation_count    | 검증 실패 PII              | 0        |
# | mask_recall            | 정탐 / (정탐+미탐)          | ≥ 95%   |
# | mask_precision         | 정탐 / (정탐+오탐)          | ≥ 90%   |
# | device_mask_latency_p95| 온디바이스 처리 p95         | < 200ms  |
