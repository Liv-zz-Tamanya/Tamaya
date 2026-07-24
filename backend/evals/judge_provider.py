"""평가 judge 모델 선택 — GEMINI_API_KEY가 있으면 Gemini, 없으면 CLOVA fallback.

생성 모델(CLOVA)과 같은 모델로 채점하면 자기 채점 편향이 생긴다. 키가 설정된
환경에서는 외부 judge(Gemini)를 기본으로 쓰되, 키가 없는 환경(CI retrieval
게이트, 로컬 개발)에서도 평가가 깨지지 않도록 CLOVA로 자동 fallback 한다.
Gemini는 OpenAI 호환 엔드포인트로 호출하므로 judge 클라이언트는 기존
AsyncOpenAI 하나로 통일된다.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.infrastructure.config.settings import settings


@dataclass(frozen=True)
class JudgeProvider:
    name: str  # "gemini" | "clova"
    api_key: str
    base_url: str
    model: str


def resolve_judge_provider() -> JudgeProvider:
    if settings.gemini_api_key:
        return JudgeProvider(
            name="gemini",
            api_key=settings.gemini_api_key,
            base_url=settings.gemini_base_url,
            model=settings.gemini_model,
        )
    return JudgeProvider(
        name="clova",
        api_key=settings.clova_api_key,
        base_url=settings.clova_base_url,
        model=settings.clova_model,
    )
