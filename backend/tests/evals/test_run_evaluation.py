from __future__ import annotations

from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.tools import BaseTool

from app.application.service.agent_execution_observability import (
    AgentExecutionRecord,
    AgentTerminationReason,
)
from app.application.service.tool_calling_chat_model import ToolCallingChatModel
from evals.run_evaluation import (
    EvaluationRecorder,
    evaluate_record,
    load_cases,
    messages_for_case,
    run_cases,
    select_cases,
    summarize,
)
from evals.schemas import PersonalAssistantEvalCase


def _case(**overrides: object) -> PersonalAssistantEvalCase:
    return PersonalAssistantEvalCase.model_validate({
        "id": "case-1", "mode": "diary", "input": "지난주 기억", "history": [],
        "expected_tools": ["search_diary_memories"], "forbidden_tools": [],
        "expected_guardrail": "PASS", "expected_document_ids": [], "category": "tool", **overrides,
    })


def _record(*tools: str, reason: AgentTerminationReason = AgentTerminationReason.COMPLETED) -> AgentExecutionRecord:
    return AgentExecutionRecord("trace", "diary", reason, "safe", 1, 1, tools, 1, 2, 3, 0, None, None, 0, 0, 0, 1, 2, 3)


def test_messages_for_case_and_invalid_role():
    case = _case(history=[{"role": "user", "content": "안녕"}, {"role": "assistant", "content": "응"}])
    assert [message.content for message in messages_for_case(case)] == ["안녕", "응", "지난주 기억"]
    with pytest.raises(ValueError, match="unsupported history role"):
        messages_for_case(_case(history=[{"role": "system", "content": "x"}]))


def test_evaluate_tool_checks_duplicate_and_guardrail():
    success = evaluate_record(_case(), "diary", _record("search_diary_memories", "search_diary_memories"), None)
    assert success.actual_tools == ["search_diary_memories", "search_diary_memories"]
    assert success.combined_passed
    missing = evaluate_record(_case(), "diary", _record(), None)
    assert missing.missing_expected_tools == ["search_diary_memories"]
    forbidden = evaluate_record(_case(forbidden_tools=["search_health_records"]), "diary", _record("search_diary_memories", "search_health_records"), None)
    assert forbidden.called_forbidden_tools == ["search_health_records"]
    blocked = evaluate_record(_case(expected_guardrail="BLOCK"), "diary", _record(reason=AgentTerminationReason.INPUT_GUARDRAIL_BLOCKED), None)
    assert blocked.guardrail_check_passed
    timeout = evaluate_record(_case(), "diary", _record(reason=AgentTerminationReason.TIMEOUT), None)
    assert timeout.execution_error and not timeout.guardrail_check_passed


def test_recorder_requires_one_record():
    recorder = EvaluationRecorder()
    with pytest.raises(RuntimeError, match="got 0"):
        recorder.only_record()
    recorder.record(_record())
    recorder.record(_record())
    with pytest.raises(RuntimeError, match="got 2"):
        recorder.only_record()


def test_load_filter_limit_and_summary(tmp_path: Path):
    (tmp_path / "diary_cases.jsonl").write_text(_case().model_dump_json() + "\n", encoding="utf-8")
    for name in ("health", "coaching", "guardrail"):
        (tmp_path / f"{name}_cases.jsonl").write_text("", encoding="utf-8")
    cases = load_cases(tmp_path, ["diary"])
    assert len(select_cases(cases, "case-1", 1)) == 1
    with pytest.raises(ValueError, match="not found"):
        select_cases(cases, "missing", None)
    summary = summarize([evaluate_record(_case(), "diary", _record("search_diary_memories"), None)])
    assert summary.combined_rate == 100


class _ScriptedModel(ToolCallingChatModel):
    async def ainvoke(self, messages: list[BaseMessage], tools: list[BaseTool]) -> AIMessage:
        if any(message.type == "tool" for message in messages):
            return AIMessage(content="done")
        return AIMessage(content="", tool_calls=[{"name": "search_diary_memories", "args": {"query": "x"}, "id": "tool-1"}])


async def test_run_specific_case_with_fake_model():
    results = await run_cases([("diary", _case())], model=_ScriptedModel())
    assert results[0].combined_passed
