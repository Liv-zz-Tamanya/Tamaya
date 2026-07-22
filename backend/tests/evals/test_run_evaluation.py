from __future__ import annotations

from datetime import UTC, datetime
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
    CaseStabilityResult,
    EvaluationRecorder,
    build_report,
    case_stability,
    compare_baseline,
    evaluate_record,
    load_baseline,
    load_cases,
    main,
    messages_for_case,
    run_cases,
    run_repeated_cases,
    select_cases,
    summarize,
    tool_confusion_matrix,
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


async def test_repeat_records_deterministic_run_numbers():
    results = await run_repeated_cases([("diary", _case())], model=_ScriptedModel(), repeat=3)
    assert [result.run_number for result in results] == [1, 2, 3]
    assert all(result.combined_passed for result in results)


def test_case_stability_counts_flaky_errors_tools_and_percentiles():
    passed = evaluate_record(_case(), "diary", _record("search_diary_memories"), None, 1)
    failed = evaluate_record(_case(), "diary", _record("search_health_records"), None, 2)
    error = evaluate_record(_case(), "diary", _record(reason=AgentTerminationReason.TIMEOUT), RuntimeError("timeout"), 3)
    stability = case_stability([passed, failed, error])[0]
    assert stability.status == "flaky"
    assert stability.case_pass_rate == 33.3
    assert stability.execution_error_runs == 1
    assert stability.actual_tool_selected_runs == {"search_diary_memories": 1, "search_health_records": 1}
    assert stability.p95_execution_duration_ms == 3
    assert stability.average_total_tokens == 3


def test_case_stability_marks_all_failed_runs_stable_fail():
    failed = evaluate_record(_case(), "diary", _record(), None, 1)
    timed_out = evaluate_record(_case(), "diary", _record(reason=AgentTerminationReason.TIMEOUT), RuntimeError("timeout"), 2)
    stability = case_stability([failed, timed_out])[0]
    assert stability.status == "stable_fail"
    assert stability.case_pass_rate == 0


def test_tool_confusion_excludes_unlabeled_and_errors():
    expected = evaluate_record(_case(), "diary", _record("search_diary_memories", "search_diary_memories"), None)
    forbidden = evaluate_record(_case(forbidden_tools=["search_health_records"]), "diary", _record("search_diary_memories", "search_health_records"), None)
    error = evaluate_record(_case(), "diary", _record(reason=AgentTerminationReason.TIMEOUT), RuntimeError("timeout"))
    matrix = tool_confusion_matrix([expected, forbidden, error])
    assert matrix["search_diary_memories"].true_positive == 2
    assert matrix["search_health_records"].false_positive == 1
    assert matrix["search_health_records"].unlabeled == 2
    assert matrix["search_health_records"].recall is None


def test_baseline_comparison_detects_rate_and_status_regressions():
    current = case_stability([evaluate_record(_case(), "diary", _record(), None, 1), evaluate_record(_case(), "diary", _record("search_diary_memories"), None, 2)])
    baseline = [CaseStabilityResult.model_validate({**current[0].model_dump(), "case_pass_rate": 100, "passed_runs": 2, "failed_runs": 0, "status": "stable_pass"})]
    comparison = compare_baseline(current, baseline)
    assert comparison.regressed_cases == ["case-1"]
    added = CaseStabilityResult.model_validate({**current[0].model_dump(), "case_id": "added"})
    comparison = compare_baseline([*current, added], baseline)
    assert comparison.added_cases == ["added"]


def test_build_report_repeat_one_keeps_execution_summary():
    result = evaluate_record(_case(), "diary", _record("search_diary_memories"), None)
    report = build_report([result], ["diary"], datetime.now(UTC))
    assert report.summary.total_cases == 1
    assert report.stability_summary.repeat_count == 1


def test_repeat_validation_and_incompatible_baseline(tmp_path: Path):
    with pytest.raises(SystemExit, match="2"):
        main(["--repeat", "0"])
    bad_baseline = tmp_path / "old.json"
    bad_baseline.write_text('{"summary": {}}', encoding="utf-8")
    with pytest.raises(ValueError, match="incompatible baseline"):
        load_baseline(bad_baseline)
