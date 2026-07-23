"""E2E 실패 단계 분류·집계 테스트."""

from evals.e2e_metrics import classify_stage, e2e_case_stability, summarize_e2e
from evals.e2e_results import E2ECaseResult, E2EFailureStage
from evals.e2e_schemas import E2EEvalCase
from evals.generation_judge import JudgeVerdict


def _case(**overrides) -> E2EEvalCase:
    defaults = dict(
        id="e2e-test-001", mode="diary", device_id="eval-user-hana",
        input="카페 갔던 날 기억나?", expected_decision="TOOL_CALL",
        expected_tools=["search_diary_memories"], forbidden_tools=["search_health_records"],
        relevant_chunk_ids=["hana-0602-cafe"], expected_facts=[["케이크"]],
        category="grounded_recall",
    )
    defaults.update(overrides)
    return E2EEvalCase.model_validate(defaults)


def _classify(case=None, **overrides):
    defaults = dict(
        actual_tools=["search_diary_memories"], retrieved_labels=["hana-0602-cafe"],
        leaked_labels=[], execution_error=None, termination_reason="completed",
        completeness=1.0, verdict=JudgeVerdict(),
    )
    defaults.update(overrides)
    return classify_stage(case or _case(), **defaults)


def test_stage_priority_order():
    assert _classify(execution_error="boom") == E2EFailureStage.EXECUTION_ERROR
    assert _classify(termination_reason="input_guardrail_blocked") == E2EFailureStage.GUARDRAIL_BLOCKED
    assert _classify(actual_tools=[]) == E2EFailureStage.TOOL_UNDER_CALL
    assert _classify(actual_tools=["search_health_records", "search_diary_memories"]) == E2EFailureStage.WRONG_TOOL
    assert _classify(leaked_labels=["sora-0628-cafe"]) == E2EFailureStage.CROSS_USER_LEAK
    assert _classify(retrieved_labels=["hana-0625-jeju"]) == E2EFailureStage.RETRIEVAL_MISS
    assert _classify() == E2EFailureStage.PASS


def test_no_tool_cases():
    case = _case(expected_decision="NO_TOOL", expected_tools=[],
                 relevant_chunk_ids=[], expected_facts=[])
    assert _classify(case, actual_tools=[]) == E2EFailureStage.PASS
    assert _classify(case, actual_tools=["search_diary_memories"]) == E2EFailureStage.TOOL_OVER_CALL


def test_retrieval_partial_vs_miss():
    case = _case(relevant_chunk_ids=["hana-0602-cafe", "hana-0625-jeju"],
                 expected_facts=[["케이크"], ["제주도"]])
    assert _classify(case, retrieved_labels=["hana-0602-cafe"]) == E2EFailureStage.RETRIEVAL_PARTIAL
    assert _classify(case, retrieved_labels=["hana-0610-praise"]) == E2EFailureStage.RETRIEVAL_MISS


def test_wrong_tool_when_expected_tool_missing():
    # 금지 tool은 아니지만 기대 tool을 안 부르고 다른 tool만 부른 경우
    case = _case(forbidden_tools=[])
    assert _classify(case, actual_tools=["search_health_records"]) == E2EFailureStage.WRONG_TOOL


def test_abstention_branch():
    case = _case(relevant_chunk_ids=[], expected_facts=[], category="empty_retrieval")
    assert _classify(case, retrieved_labels=[], verdict=JudgeVerdict(abstained=True)) == E2EFailureStage.PASS
    assert _classify(case, retrieved_labels=[], verdict=JudgeVerdict(abstained=False)) == E2EFailureStage.ABSTENTION_FAIL
    assert _classify(
        case, retrieved_labels=[],
        verdict=JudgeVerdict(abstained=True, unsupported_claims=["지어냄"]),
    ) == E2EFailureStage.ABSTENTION_FAIL
    # judge가 없으면(오류 등) 보수적으로 PASS 처리하되 judge_error가 별도 집계됨
    assert _classify(case, retrieved_labels=[], verdict=None) == E2EFailureStage.PASS


def test_answer_stage_checks():
    assert _classify(verdict=JudgeVerdict(unsupported_claims=["없는 사실"])) == E2EFailureStage.UNSUPPORTED_CLAIM
    assert _classify(completeness=0.5) == E2EFailureStage.INCOMPLETE_ANSWER


def _result(case_id: str, stage: E2EFailureStage, run_number: int = 1, **overrides) -> E2ECaseResult:
    defaults = dict(
        case_id=case_id, mode="diary", category="grounded_recall",
        device_id="eval-user-hana", input="q", run_number=run_number,
        expected_decision="TOOL_CALL", stage=stage, passed=stage == E2EFailureStage.PASS,
        execution_duration_ms=1000, total_tokens=500,
    )
    defaults.update(overrides)
    return E2ECaseResult.model_validate(defaults)


def test_summarize_and_stability():
    results = [
        _result("c1", E2EFailureStage.PASS, 1),
        _result("c1", E2EFailureStage.RETRIEVAL_MISS, 2, execution_duration_ms=3000),
        _result("c2", E2EFailureStage.TOOL_OVER_CALL, 1),
    ]
    summary = summarize_e2e(results)
    assert summary.case_runs == 3
    assert summary.pass_rate == 33.3
    assert summary.stage_counts == {"PASS": 1, "RETRIEVAL_MISS": 1, "TOOL_OVER_CALL": 1}
    assert summary.p50_execution_duration_ms == 1000
    assert summary.p95_execution_duration_ms == 3000
    assert summary.total_tokens_sum == 1500
    stability = {item.case_id: item for item in e2e_case_stability(results)}
    assert stability["c1"].status == "flaky"
    assert stability["c2"].status == "stable_fail"
    assert stability["c1"].stage_frequency == {"PASS": 1, "RETRIEVAL_MISS": 1}
