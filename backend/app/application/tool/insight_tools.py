"""INSIGHT 모드 근거 탐색 tool — 기간 raw 목록을 노출하지 않는다.

2층 원칙: 평균·추세·상관은 결정론 코드가 이미 계산해 context로 주입했다.
tool은 Agent가 스스로 판단해야 하는 '근거 탐색'에만 쓴다.
- get_day_facts: 허용된 단일 날짜의 DailyFact 한 행
- get_medical_visit_facts: 기간이 bind된 진료 '사실'만 (병명·약 정보 없음)
"""

from datetime import date

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

from app.domain.model.insight_report import InsightPeriodType
from app.domain.model.medical_visit import MedicalVisit
from app.domain.service.insight_models import DailyFact


class GetDayFactsInput(BaseModel):
    date: str = Field(
        ...,
        description="Evidence date to inspect (YYYY-MM-DD). Must be one of the allowed evidence dates.",
    )


class _EmptyInput(BaseModel):
    """인자 없는 tool 스키마 — 기간은 context에 bind되어 있다."""


GET_DAY_FACTS_DESCRIPTION = (
    "Purpose: inspect one allowed evidence date to ground an insight message in what actually "
    "happened that day. Input: a single date from allowed_evidence_dates. Output: that day's "
    "recorded facts only (steps, sleep minutes, satisfaction, emotion, medical visit, diary "
    "existence). Missing values are null. Never returns ranges, averages, or trends."
)

GET_MEDICAL_VISIT_FACTS_DESCRIPTION = (
    "Purpose: list factual medical visit records (count, date, institution, visit type) for the "
    "analysis period. Use only to state facts like visit counts. Output never includes diagnoses, "
    "conditions, or medication details."
)


def create_get_day_facts_tool(
    facts_by_date: dict[date, DailyFact],
    allowed_dates: frozenset[date],
    period_start: date,
    period_end: date,
) -> BaseTool:
    async def get_day_facts(date: str) -> dict:  # noqa: A002 — tool 인자 계약
        try:
            requested = _parse_date(date)
        except ValueError:
            return {"error": "date must be YYYY-MM-DD"}
        if not period_start <= requested <= period_end:
            return {"error": "date is outside the analysis period"}
        if requested not in allowed_dates:
            return {"error": "date is not in allowed_evidence_dates"}

        fact = facts_by_date.get(requested)
        if fact is None:
            # 허용 날짜인데 행이 없어도 well-formed 응답 (계약: 날짜당 정확히 1행)
            return _day_facts_payload(requested, None)
        return _day_facts_payload(requested, fact)

    return StructuredTool.from_function(
        coroutine=get_day_facts,
        name="get_day_facts",
        description=GET_DAY_FACTS_DESCRIPTION,
        args_schema=GetDayFactsInput,
        return_direct=False,
    )


def create_get_medical_visit_facts_tool(
    visits: list[MedicalVisit],
    period_type: InsightPeriodType,
    period_start: date,
    period_end: date,
) -> BaseTool:
    period_visits = [v for v in visits if period_start <= v.visit_date <= period_end]

    async def get_medical_visit_facts() -> dict:
        by_visit_type: dict[str, int] = {}
        for visit in period_visits:
            by_visit_type[visit.visit_type.value] = by_visit_type.get(visit.visit_type.value, 0) + 1
        return {
            "period_type": period_type.value,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "visit_count": len(period_visits),
            "by_visit_type": by_visit_type,
            "visits": [
                {
                    "date": visit.visit_date.isoformat(),
                    "institution": visit.institution,
                    "visit_type": visit.visit_type.value,
                }
                for visit in sorted(period_visits, key=lambda v: (v.visit_date, v.institution))
            ],
        }

    return StructuredTool.from_function(
        coroutine=get_medical_visit_facts,
        name="get_medical_visit_facts",
        description=GET_MEDICAL_VISIT_FACTS_DESCRIPTION,
        args_schema=_EmptyInput,
        return_direct=False,
    )


def _parse_date(value: str) -> date:
    return date.fromisoformat(value.strip())


def _day_facts_payload(day: date, fact: DailyFact | None) -> dict:
    return {
        "date": day.isoformat(),
        "steps": fact.steps if fact else None,  # 0은 실제 관측 — 결측(null)과 다르다
        "sleep_minutes": fact.sleep_minutes if fact else None,
        "satisfaction": fact.satisfaction if fact else None,
        "emotion": fact.emotion if fact else None,
        "has_medical_visit": fact.has_medical_visit if fact else False,
        "has_diary": (fact.emotion is not None) if fact else False,
    }
