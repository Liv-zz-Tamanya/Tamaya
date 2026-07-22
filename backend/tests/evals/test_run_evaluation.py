from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.tools import BaseTool

from app.application.service.agent_execution_observability import (
    AgentExecutionRecord,
    AgentTerminationReason,
    LlmCallTraceRecord,
    ToolCallTraceRecord,
)
from app.application.service.tool_calling_chat_model import ToolCallingChatModel
from app.application.usecase.personal_assistant_agent import PersonalAssistantMode
from evals.run_evaluation import (
    CaseStabilityResult,
    EvaluationRecorder,
    _hash_json,
    _prompt_metadata,
    _tool_schema_payload,
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
    write_report,
)
from evals.schemas import PersonalAssistantEvalCase


def _case(**overrides: object) -> PersonalAssistantEvalCase:
    return PersonalAssistantEvalCase.model_validate({
        "id": "case-1", "mode": "diary", "input": "지난주 기억", "history": [],
        "expected_tools": ["search_diary_memories"], "forbidden_tools": [],
        "expected_guardrail": "PASS", "expected_document_ids": [], "category": "tool", **overrides,
    })


def _record(
    *tools: str,
    reason: AgentTerminationReason = AgentTerminationReason.COMPLETED,
    llm_calls: int = 1,
    tool_calls: tuple[ToolCallTraceRecord, ...] = (),
    llm_call_traces: tuple[LlmCallTraceRecord, ...] = (),
) -> AgentExecutionRecord:
    return AgentExecutionRecord(
        "trace",
        "diary",
        reason,
        "safe",
        llm_calls,
        1,
        tools,
        1,
        2,
        3,
        0,
        None,
        None,
        0,
        0,
        0,
        1,
        2,
        3,
        tool_calls,
        llm_call_traces,
        llm_call_traces[0].finish_reason if llm_call_traces else None,
        llm_call_traces[0].response_content if llm_call_traces else None,
        llm_call_traces[-1].response_content if llm_call_traces else None,
    )


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


def test_evaluate_record_copies_tool_call_and_llm_traces():
    tool_call_1 = ToolCallTraceRecord(
        round=1,
        call_id="call-1",
        name="search_diary_memories",
        arguments={"query": "오늘 좋았던 일"},
    )
    tool_call_2 = ToolCallTraceRecord(
        round=1,
        call_id="call-2",
        name="search_health_records",
        arguments={"query": "걸음"},
    )
    first = LlmCallTraceRecord(
        call_number=1,
        finish_reason="tool_calls",
        response_content=None,
        tool_calls=(tool_call_1, tool_call_2),
        input_tokens=10,
        output_tokens=2,
        total_tokens=12,
        duration_ms=123,
    )
    final = LlmCallTraceRecord(
        call_number=2,
        finish_reason="stop",
        response_content="최종 응답",
        tool_calls=(),
        input_tokens=20,
        output_tokens=5,
        total_tokens=25,
        duration_ms=234,
    )

    result = evaluate_record(
        _case(expected_tools=["search_diary_memories"], forbidden_tools=["search_health_records"]),
        "diary",
        _record(
            "search_diary_memories",
            "search_health_records",
            tool_calls=(tool_call_1, tool_call_2),
            llm_call_traces=(first, final),
        ),
        None,
    )

    assert result.actual_tools == ["search_diary_memories", "search_health_records"]
    assert [call.name for call in result.tool_calls] == [
        "search_diary_memories",
        "search_health_records",
    ]
    assert result.tool_calls[0].arguments == {"query": "오늘 좋았던 일"}
    assert result.called_forbidden_tools == ["search_health_records"]
    assert result.first_finish_reason == "tool_calls"
    assert result.first_response_content is None
    assert result.final_response_content == "최종 응답"
    assert len(result.llm_call_traces) == 2
    assert result.llm_call_traces[0].tool_calls[1].arguments == {"query": "걸음"}
    assert result.llm_call_traces[0].duration_ms == 123


def test_evaluate_record_keeps_argument_parse_errors_non_fatal():
    invalid = ToolCallTraceRecord(
        round=1,
        call_id="bad",
        name="search_diary_memories",
        arguments=None,
        arguments_parse_error="invalid json",
    )
    result = evaluate_record(
        _case(),
        "diary",
        _record("search_diary_memories", tool_calls=(invalid,)),
        None,
    )

    assert result.actual_tools == ["search_diary_memories"]
    assert result.tool_calls[0].arguments is None
    assert result.tool_calls[0].arguments_parse_error == "invalid json"
    assert result.execution_error is None


def test_decision_checks_distinguish_no_tool_and_tool_call():
    no_tool = evaluate_record(_case(expected_tools=[], forbidden_tools=["search_diary_memories"]), "diary", _record(), None)
    unnecessary = evaluate_record(_case(expected_tools=[], forbidden_tools=["search_diary_memories"]), "diary", _record("search_diary_memories"), None)
    tool_call = evaluate_record(_case(), "diary", _record("search_diary_memories"), None)
    missing_tool = evaluate_record(_case(), "diary", _record(), None)
    assert no_tool.expected_decision.value == "NO_TOOL" and no_tool.decision_check_passed
    assert unnecessary.actual_decision.value == "TOOL_CALL" and not unnecessary.decision_check_passed
    assert tool_call.decision_check_passed
    assert not missing_tool.decision_check_passed
    summary = summarize([no_tool, unnecessary, tool_call, missing_tool])
    assert summary.no_tool_accuracy == 50
    assert summary.tool_call_accuracy == 50
    assert summary.unnecessary_tool_call_cases == 1


def test_input_guardrail_block_is_skipped_from_decision_metrics():
    blocked_case = _case(expected_tools=[], forbidden_tools=["search_diary_memories"], expected_guardrail="BLOCK")
    blocked = evaluate_record(
        blocked_case,
        "diary",
        _record(reason=AgentTerminationReason.INPUT_GUARDRAIL_BLOCKED, llm_calls=0),
        None,
    )
    direct = evaluate_record(_case(expected_tools=[], forbidden_tools=["search_diary_memories"]), "diary", _record(), None)
    summary = summarize([blocked, direct])
    assert blocked.guardrail_check_passed
    assert blocked.actual_decision is None
    assert blocked.decision_check_passed is None
    assert blocked.decision_skip_reason == "input_guardrail_blocked"
    assert summary.no_tool_cases == 1
    assert summary.decision_skipped_cases == 1
    assert summary.decision_skipped_input_guardrail_blocked_cases == 1


def test_execution_error_and_missing_expected_decision_are_not_evaluable():
    errored = evaluate_record(_case(), "diary", _record(reason=AgentTerminationReason.TIMEOUT), RuntimeError("timeout"))
    unlabeled = evaluate_record(_case(expected_tools=[], forbidden_tools=[]), "diary", _record(), None)
    assert errored.decision_check_passed is None
    assert errored.decision_skip_reason == "execution_error"
    assert unlabeled.decision_check_passed is None
    assert unlabeled.decision_skip_reason == "expected_decision_missing"


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


def test_diary_abstention_boundary_cases_load_with_expected_decisions():
    cases = load_cases(Path(__file__).parents[2] / "evals" / "datasets", ["diary"])
    decisions = {case.id: case.expected_decision for _, case in cases}
    assert decisions["diary-011"].value == "NO_TOOL"
    assert decisions["diary-012"].value == "NO_TOOL"
    assert decisions["diary-013"].value == "TOOL_CALL"
    assert decisions["diary-014"].value == "TOOL_CALL"


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
    assert report.model_settings.provider == "clova"
    assert report.prompt_metadata.prompt_hash.startswith("sha256:")
    assert report.prompt_metadata.tool_schema_hash.startswith("sha256:")


def test_write_report_keeps_legacy_summary_and_adds_model_config_alias(tmp_path: Path):
    result = evaluate_record(_case(), "diary", _record("search_diary_memories"), None)
    report = build_report([result], ["diary"], datetime.now(UTC))
    output = tmp_path / "report.json"

    write_report(report, output)

    raw = output.read_text(encoding="utf-8")
    assert "Authorization" not in raw
    assert "CLOVA_API_KEY" not in raw
    data = json.loads(raw)
    assert data["summary"]["total_cases"] == 1
    assert "model_config" in data
    assert "model_settings" not in data
    assert data["model_config"]["seed"] is None
    assert data["model_config"]["parallel_tool_calls"] is None
    assert data["prompt_metadata"]["prompt_hash"].startswith("sha256:")


def test_prompt_and_tool_schema_hashes_are_canonical_and_change_with_inputs():
    left = _hash_json({"b": 2, "a": [{"z": 1, "y": 0}]})
    right = _hash_json({"a": [{"y": 0, "z": 1}], "b": 2})
    assert left == right

    metadata = _prompt_metadata([PersonalAssistantMode.DIARY])
    assert metadata.prompt_hash == _prompt_metadata([PersonalAssistantMode.DIARY]).prompt_hash
    assert metadata.tool_schema_hash == _prompt_metadata([PersonalAssistantMode.DIARY]).tool_schema_hash
    assert metadata.prompt_hash != _prompt_metadata([PersonalAssistantMode.HEALTH]).prompt_hash

    diary_schema = _tool_schema_payload([PersonalAssistantMode.DIARY])
    changed_schema = [{**diary_schema[0], "description": diary_schema[0]["description"] + " changed"}]
    assert _hash_json(diary_schema) != _hash_json(changed_schema)


def test_repeat_validation_and_incompatible_baseline(tmp_path: Path):
    with pytest.raises(SystemExit, match="2"):
        main(["--repeat", "0"])
    bad_baseline = tmp_path / "old.json"
    bad_baseline.write_text('{"summary": {}}', encoding="utf-8")
    with pytest.raises(ValueError, match="incompatible baseline"):
        load_baseline(bad_baseline)
