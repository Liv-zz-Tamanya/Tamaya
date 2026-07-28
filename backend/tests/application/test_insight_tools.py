"""INSIGHT 근거 tool — 날짜 allowlist·기간 bind·민감 필드 미노출 검증."""

from __future__ import annotations

from datetime import date

from app.application.tool.insight_tools import (
    create_get_day_facts_tool,
    create_get_medical_visit_facts_tool,
)
from app.domain.model.insight_report import InsightPeriodType
from app.domain.model.medical_visit import MedicalVisit, MedicalVisitType
from app.domain.service.insight_models import DailyFact

START = date(2026, 7, 27)
END = date(2026, 8, 2)
ALLOWED = date(2026, 7, 29)


def _fact(day: date, steps: int | None, sleep: int | None, satisfaction: int | None) -> DailyFact:
    return DailyFact(
        date=day,
        steps=steps,
        sleep_minutes=sleep,
        satisfaction=satisfaction,
        emotion="tired" if satisfaction is not None else None,
        has_medical_visit=False,
        steps_p75=None,
        is_weekend=False,
    )


def _day_facts_tool(facts_by_date=None, allowed=frozenset({ALLOWED})):
    return create_get_day_facts_tool(
        facts_by_date=facts_by_date or {},
        allowed_dates=allowed,
        period_start=START,
        period_end=END,
    )


async def test_allowed_date_returns_single_day_row():
    tool = _day_facts_tool({ALLOWED: _fact(ALLOWED, steps=0, sleep=216, satisfaction=42)})
    result = await tool.coroutine(date=ALLOWED.isoformat())

    assert result == {
        "date": "2026-07-29",
        "steps": 0,  # 0걸음은 실제 관측 — 결측으로 바꾸지 않는다
        "sleep_minutes": 216,
        "satisfaction": 42,
        "emotion": "tired",
        "has_medical_visit": False,
        "has_diary": True,
    }


async def test_missing_values_are_null_not_zero():
    tool = _day_facts_tool({ALLOWED: _fact(ALLOWED, steps=None, sleep=None, satisfaction=None)})
    result = await tool.coroutine(date=ALLOWED.isoformat())
    assert result["steps"] is None
    assert result["sleep_minutes"] is None
    assert result["has_diary"] is False


async def test_date_outside_period_rejected():
    tool = _day_facts_tool()
    result = await tool.coroutine(date="2026-09-01")
    assert "outside the analysis period" in result["error"]


async def test_date_not_in_allowlist_rejected():
    tool = _day_facts_tool()
    inside_period_but_not_allowed = date(2026, 7, 28)
    result = await tool.coroutine(date=inside_period_but_not_allowed.isoformat())
    assert "allowed_evidence_dates" in result["error"]


async def test_medical_visit_facts_bound_to_period_and_no_sensitive_fields():
    visits = [
        MedicalVisit(
            device_id="dev-1",
            visit_date=date(2026, 7, 28),
            visit_type=MedicalVisitType.OUTPATIENT,
            institution="OO의원",
            prescription_count=3,
            medication_days=7,
        ),
        MedicalVisit(  # 기간 밖 — bind된 기간으로 걸러진다
            device_id="dev-1",
            visit_date=date(2026, 6, 1),
            visit_type=MedicalVisitType.PHARMACY,
            institution="XX약국",
        ),
    ]
    tool = create_get_medical_visit_facts_tool(
        visits=visits,
        period_type=InsightPeriodType.WEEKLY,
        period_start=START,
        period_end=END,
    )
    result = await tool.coroutine()

    assert result["visit_count"] == 1
    assert result["visits"] == [
        {"date": "2026-07-28", "institution": "OO의원", "visit_type": "방문 외래"}
    ]
    serialized = str(result)
    assert "prescription" not in serialized
    assert "medication" not in serialized
