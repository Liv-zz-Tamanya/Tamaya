"""평가 judge 모델 선택 — Vertex(회사 프로젝트) > Gemini API 키 > CLOVA fallback.

생성 모델(CLOVA)과 같은 모델로 채점하면 자기 채점 편향이 생긴다. 외부 judge를
우선 사용하되, 아무 설정도 없는 환경(CI retrieval 게이트, 로컬 개발)에서도
평가가 깨지지 않도록 CLOVA로 자동 fallback 한다.

- Vertex 모드(GOOGLE_GENAI_USE_VERTEXAI=true + GOOGLE_CLOUD_PROJECT): 회사 정책상
  API 키 발급이 금지라 gcloud 계정 인증(access token)으로 호출한다. 토큰은 약
  1시간 유효 — 평가 1회 실행에는 충분하다. `gcloud auth login`이 선행 조건.
- Gemini/Vertex 모두 OpenAI 호환 엔드포인트로 호출하므로 judge 클라이언트는
  기존 AsyncOpenAI 하나로 통일된다.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass

from app.infrastructure.config.settings import settings


@dataclass(frozen=True)
class JudgeProvider:
    name: str  # "vertex" | "gemini" | "clova"
    api_key: str
    base_url: str
    model: str
    # provider별 추가 요청 필드 — 없으면 None (OpenAI 클라이언트가 그대로 무시)
    extra_body: dict | None = None


def _vertex_access_token() -> str:
    gcloud = shutil.which("gcloud") or "/opt/homebrew/bin/gcloud"
    try:
        result = subprocess.run(
            [gcloud, "auth", "print-access-token"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(
            "Vertex judge 모드에는 gcloud 계정 인증이 필요합니다. "
            "`gcloud auth login`을 초대받은 계정으로 실행하세요."
        ) from exc
    return result.stdout.strip()


def _vertex_base_url() -> str:
    location = settings.google_cloud_location
    host = (
        "aiplatform.googleapis.com"
        if location == "global"
        else f"{location}-aiplatform.googleapis.com"
    )
    return (
        f"https://{host}/v1/projects/{settings.google_cloud_project}"
        f"/locations/{location}/endpoints/openapi"
    )


def resolve_judge_provider() -> JudgeProvider:
    if settings.google_genai_use_vertexai and settings.google_cloud_project:
        return JudgeProvider(
            name="vertex",
            api_key=_vertex_access_token(),
            base_url=_vertex_base_url(),
            # Vertex OpenAI 호환 엔드포인트는 publisher 접두사를 요구한다
            model=f"google/{settings.gemini_model}",
            # judge는 boolean 판정만 하므로 thinking을 끈다 — 켜두면 max_tokens를
            # thinking이 소모해 응답 JSON이 잘린다(finish_reason=length 실측)
            extra_body={"google": {"thinking_config": {"thinking_budget": 0}}},
        )
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
