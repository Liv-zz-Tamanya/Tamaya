"""INSIGHT 모드 — HumanMessage 없는 실행·context 검증·output 안전 차단·factory 계약."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import date
from uuid import UUID, uuid4

import pytest
from langchain_core.messages import AIMessage, SystemMessage

from app.application.service.insight_generation_prompt import (
    InsightGenerationContext,
    build_insight_system_prompt,
)
from app.application.usecase.personal_assistant_agent import (
    INSIGHT_SAFETY_BLOCKED_MESSAGE_ID,
    PersonalAssistantAgent,
    PersonalAssistantMode,
)
from app.application.usecase.personal_assistant_agent_factory import PersonalAssistantAgentFactory
from app.domain.model.insight_report import InsightPeriodType

START = date(2026, 7, 27)
END = date(2026, 8, 2)


class _FakeModel:
    def __init__(self, responses: Sequence[AIMessage]) -> None:
        self._responses = list(responses)
        self.calls: list[dict] = []

    async def ainvoke(self, messages, tools) -> AIMessage:
        self.calls.append({"messages": list(messages), "tools": list(tools)})
        return self._responses.pop(0)


class _FakeDiaryQuery:
    async def search_similar(self, device_id, query, exclude_session_id=None, limit=5):
        return []


class _FakeHealthQuery:
    async def search_similar(self, device_id, query, limit=5):
        return []


def _context(**overrides) -> InsightGenerationContext:
    base = dict(
        generation_run_id=uuid4(),
        period_type=InsightPeriodType.WEEKLY,
        period_key="2026-W31",
        start_date=START,
        end_date=END,
        period_summary={"diary_days": 5, "wellbeing_score": 70},
        verified_candidates=(
            {"hypothesis_key": "sleep_satisfaction", "n": 61, "gate_passed": True},
        ),
        selected_candidates=(
            {"hypothesis_key": "sleep_satisfaction", "n": 61, "effect_size": 0.38},
        ),
        allowed_evidence_dates=(START, date(2026, 7, 29)),
    )
    base.update(overrides)
    return InsightGenerationContext(**base)


def _valid_output() -> str:
    return json.dumps(
        {
            "cards": [
                {
                    "hypothesis_key": "sleep_satisfaction",
                    "title": "잠과 만족도의 패턴",
                    "message": "함께 나타나는 경향이 있었어요.",
                    "evidence_dates": ["2026-07-27"],
                }
            ]
        },
        ensure_ascii=False,
    )


async def test_insight_runs_without_human_message():
    model = _FakeModel([AIMessage(content=_valid_output())])
    agent = PersonalAssistantAgent(model, [])
    context = _context()

    response = await agent.run(
        messages=[], mode=PersonalAssistantMode.INSIGHT, insight_context=context
    )

    assert json.loads(response.content)["cards"][0]["hypothesis_key"] == "sleep_satisfaction"
    # 시스템 프롬프트에 context JSON이 필수 입력으로 주입된다
    system_message = model.calls[0]["messages"][0]
    assert isinstance(system_message, SystemMessage)
    assert system_message.content == build_insight_system_prompt(context)
    assert '"sleep_satisfaction"' in system_message.content


async def test_insight_requires_insight_context():
    agent = PersonalAssistantAgent(_FakeModel([AIMessage(content="x")]), [])
    with pytest.raises(ValueError):
        await agent.run(messages=[], mode=PersonalAssistantMode.INSIGHT)


async def test_non_insight_modes_reject_insight_context():
    agent = PersonalAssistantAgent(_FakeModel([AIMessage(content="x")]), [])
    with pytest.raises(ValueError):
        await agent.run(
            messages=[],
            mode=PersonalAssistantMode.HEALTH,
            insight_context=_context(),
        )


async def test_prescriptive_output_replaced_with_safety_marker():
    model = _FakeModel([AIMessage(content="타이레놀을 500mg 복용하세요.")])
    agent = PersonalAssistantAgent(model, [])

    response = await agent.run(
        messages=[], mode=PersonalAssistantMode.INSIGHT, insight_context=_context()
    )

    assert response.id == INSIGHT_SAFETY_BLOCKED_MESSAGE_ID
    assert "mg" not in response.content  # 위험 원문이 밖으로 나가지 않는다


async def test_diagnostic_assertion_output_replaced_with_safety_marker():
    model = _FakeModel([AIMessage(content="기록을 보면 당신은 불면증이 확실해요.")])
    agent = PersonalAssistantAgent(model, [])

    response = await agent.run(
        messages=[], mode=PersonalAssistantMode.INSIGHT, insight_context=_context()
    )

    assert response.id == INSIGHT_SAFETY_BLOCKED_MESSAGE_ID


async def test_safe_correlation_phrase_not_blocked():
    model = _FakeModel([AIMessage(content=_valid_output())])
    agent = PersonalAssistantAgent(model, [])

    response = await agent.run(
        messages=[], mode=PersonalAssistantMode.INSIGHT, insight_context=_context()
    )

    assert response.id != INSIGHT_SAFETY_BLOCKED_MESSAGE_ID


async def test_execution_ref_recorded_on_trace():
    records = []

    class _Recorder:
        def record(self, record):
            records.append(record)

    model = _FakeModel([AIMessage(content=_valid_output())])
    agent = PersonalAssistantAgent(model, [], execution_recorder=_Recorder())
    run_id = uuid4()

    await agent.run(
        messages=[],
        mode=PersonalAssistantMode.INSIGHT,
        insight_context=_context(),
        execution_ref=str(run_id),
    )

    assert records[0].execution_ref == str(run_id)
    assert records[0].trace_id != str(run_id)  # trace_id와 generation_run_id는 별개


# ── factory 계약 ────────────────────────────────────────────────────────────


def _factory(model=None) -> PersonalAssistantAgentFactory:
    return PersonalAssistantAgentFactory(
        model or _FakeModel([AIMessage(content="x")]),
        _FakeDiaryQuery(),
        _FakeHealthQuery(),
    )


def test_create_rejects_insight_mode():
    with pytest.raises(ValueError):
        _factory().create(
            device_id="dev-1", session_id=uuid4(), mode=PersonalAssistantMode.INSIGHT
        )


def test_create_for_insight_exposes_exactly_three_evidence_tools():
    agent = _factory().create_for_insight(
        device_id="dev-1",
        run_id=uuid4(),
        context=_context(),
        day_facts_by_date={},
        medical_visits=[],
    )
    tool_names = [tool.name for tool in agent._tools]
    assert tool_names == [
        "get_day_facts",
        "search_diary_memories",
        "get_medical_visit_facts",
    ]
    # 기간 raw 목록 tool 금지
    assert "search_health_records" not in tool_names
    assert not any("sleep_records" in name or "health_records" in name for name in tool_names)


def test_existing_create_still_requires_session_id():
    import inspect

    signature = inspect.signature(PersonalAssistantAgentFactory.create)
    parameter = signature.parameters["session_id"]
    assert parameter.annotation is UUID
    assert parameter.default is inspect.Parameter.empty
