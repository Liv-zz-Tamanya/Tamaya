"""INSIGHT 모드 프롬프트 — 검증된 통계 결과의 해석 멘트 생성 전용.

통계 후보와 기간 요약은 tool이 아니라 시스템 프롬프트에 필수 입력으로
주입한다(LLM이 조회를 빼먹는 실패 모드 제거). LLM은 숫자를 계산하지 않고
selected 가설의 해석 문구만 만든다.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.domain.model.insight_report import InsightPeriodType


@dataclass(frozen=True)
class InsightGenerationContext:
    """INSIGHT 실행의 필수 입력 — 결정론 코드가 계산한 값만 담는다."""

    generation_run_id: UUID
    period_type: InsightPeriodType
    period_key: str
    start_date: date
    end_date: date
    period_summary: dict  # wellbeing·coverage 등 결정론 요약 (None은 null 그대로)
    verified_candidates: tuple[dict, ...]  # 게이트 탈락 포함 전체 finding 스냅샷
    selected_candidates: tuple[dict, ...]  # 쿨다운 통과 — 카드 생성이 허용된 가설만
    allowed_evidence_dates: tuple[date, ...]  # get_day_facts가 조회할 수 있는 날짜


INSIGHT_SYSTEM_PROMPT_HEADER = """너는 사용자의 주간 기록에서 통계적으로 검증된 패턴을 설명하는 인사이트 작성 엔진이야.

절대 규칙:
- 입력으로 제공된 검증 결과를 이해하기 쉬운 한국어로 설명해.
- 숫자를 새로 계산하지 마. 평균·비율·증감률·상관계수를 직접 만들지 마.
  숫자는 입력 JSON에 있는 값만 그대로 사용해.
- selected_candidates에 있는 가설만 카드로 만들어. 다른 가설 금지.
- 상관관계를 인과관계로 단정하지 마.
  금지 예: "수면 부족 때문에 우울해졌어요", "걸음수가 낮아서 건강이 나빠졌어요"
  허용 예: "함께 나타나는 경향이 있었어요", "기록된 날들을 보면 이런 패턴이 보였어요",
          "원인이라고 단정할 수는 없지만"
- 질환명 추정, 진단 단정, 약 이름·복용량·복용 권유, 치료 효과 단정 금지.
- coverage가 전체 기간보다 적으면 관측 일수를 반드시 밝혀.
  예: "기록이 함께 남은 N일을 기준으로 보면…" (N은 입력의 paired_days 값 그대로)
- 진료이력은 방문 횟수·날짜·기관·방문 유형 같은 사실만 언급해.
- 정성적인 원인·상황을 말하려면 tool로 찾은 근거가 있어야 해.
  근거를 찾지 못하면 추측하지 말고 통계 패턴만 설명해.
- 반말로, 따뜻하지만 과장 없이 써.

출력 형식:
- 반드시 JSON 하나만 출력해. 코드블록·설명·다른 텍스트 금지.
- 형식:
{"cards":[{"hypothesis_key":"...","title":"...","message":"...","evidence_dates":["YYYY-MM-DD"]}]}
- 카드는 selected_candidates에 있는 가설당 최대 1개, 전체 최대 2개.
- title은 60자 이내, message는 500자 이내.
- evidence_dates는 allowed_evidence_dates에 있는 날짜만 사용해(비워도 됨)."""


def build_insight_system_prompt(context: InsightGenerationContext) -> str:
    payload = {
        "period": {
            "type": context.period_type.value,
            "key": context.period_key,
            "start_date": context.start_date.isoformat(),
            "end_date": context.end_date.isoformat(),
        },
        "period_summary": context.period_summary,
        "verified_candidates": list(context.verified_candidates),
        "selected_candidates": list(context.selected_candidates),
        "allowed_evidence_dates": [d.isoformat() for d in context.allowed_evidence_dates],
    }
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return f"{INSIGHT_SYSTEM_PROMPT_HEADER}\n\n입력 데이터:\n{serialized}"


def insight_prompt_hash() -> str:
    """평가 리포트용 프롬프트 해시 — 기존 diary 평가 패턴과 동일 철학."""
    encoded = json.dumps(
        {"system_header": INSIGHT_SYSTEM_PROMPT_HEADER}, ensure_ascii=False, sort_keys=True
    )
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()
