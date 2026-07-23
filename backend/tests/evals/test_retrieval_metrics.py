"""Retrieval 순위 지표·집계·baseline 비교 테스트."""

from evals.retrieval_metrics import (
    compare_retrieval_baseline,
    first_relevant_rank,
    hit_at,
    precision_at,
    recall_at,
    reciprocal_rank,
    summarize_retrieval,
)
from evals.retrieval_results import RetrievalCaseResult
from evals.retrieval_schemas import RetrievalKind


def _case_result(case_id: str, **overrides) -> RetrievalCaseResult:
    defaults = dict(
        case_id=case_id,
        kind=RetrievalKind.DIARY,
        device_id="eval-user-test",
        category="direct_recall",
        query="테스트 질의",
        relevant_chunk_ids=["a"],
        hit_at_1=True,
        hit_at_3=True,
        hit_at_5=True,
        precision_at_k=0.2,
        recall_at_k=1.0,
        reciprocal_rank=1.0,
        first_relevant_rank=1,
    )
    defaults.update(overrides)
    return RetrievalCaseResult(**defaults)


def test_rank_metrics_on_second_position():
    relevant = ["a"]
    retrieved = ["x", "a", "y", "z", "w"]
    assert first_relevant_rank(relevant, retrieved) == 2
    assert hit_at(1, relevant, retrieved) is False
    assert hit_at(3, relevant, retrieved) is True
    assert reciprocal_rank(relevant, retrieved) == 0.5
    assert precision_at(5, relevant, retrieved) == 0.2
    assert recall_at(5, relevant, retrieved) == 1.0


def test_rank_metrics_when_missing():
    relevant = ["a"]
    retrieved = ["x", "y", "z", "w", "v"]
    assert first_relevant_rank(relevant, retrieved) is None
    assert hit_at(5, relevant, retrieved) is False
    assert reciprocal_rank(relevant, retrieved) == 0.0
    assert recall_at(5, relevant, retrieved) == 0.0


def test_recall_with_multiple_relevant():
    relevant = ["a", "b", "c"]
    retrieved = ["a", "x", "b", "y", "z"]
    assert recall_at(5, relevant, retrieved) == 0.667
    assert precision_at(5, relevant, retrieved) == 0.4


def test_summarize_excludes_empty_expected_from_rank_metrics():
    results = [
        _case_result("c1"),
        _case_result("c2", hit_at_1=False, hit_at_3=False, hit_at_5=False,
                     reciprocal_rank=0.0, recall_at_k=0.0, first_relevant_rank=None),
        _case_result("c3", relevant_chunk_ids=[], rank_metrics_evaluable=False,
                     hit_at_1=None, hit_at_3=None, hit_at_5=None, precision_at_k=None,
                     recall_at_k=None, reciprocal_rank=None, first_relevant_rank=None,
                     empty_expected=True, empty_check_passed=True),
    ]
    summary = summarize_retrieval(results)
    assert summary.case_count == 3
    assert summary.evaluable_cases == 2
    assert summary.hit_rate_at_1 == 50.0
    assert summary.mrr == 0.5
    assert summary.empty_expected_cases == 1
    assert summary.empty_check_passed_cases == 1


def test_summarize_counts_leaks_and_unknowns():
    results = [
        _case_result("c1", leaked_labels=["other-user-chunk"]),
        _case_result("c2", unknown_ids=["11111111-1111-1111-1111-111111111111"]),
    ]
    summary = summarize_retrieval(results)
    assert summary.leak_violation_cases == 1
    assert summary.unknown_result_cases == 1


def test_baseline_regression_on_lost_hit_and_lower_rr():
    baseline = [_case_result("c1"), _case_result("c2", reciprocal_rank=1.0)]
    current = [
        _case_result("c1", hit_at_5=False, hit_at_1=False, hit_at_3=False, reciprocal_rank=0.0),
        _case_result("c2", reciprocal_rank=0.5),
    ]
    comparison = compare_retrieval_baseline(current, baseline)
    assert set(comparison.regressed_cases) == {"c1", "c2"}
    assert comparison.mrr_delta is not None and comparison.mrr_delta < 0


def test_baseline_regression_on_new_leak():
    baseline = [_case_result("c1")]
    current = [_case_result("c1", leaked_labels=["leak"])]
    comparison = compare_retrieval_baseline(current, baseline)
    assert comparison.regressed_cases == ["c1"]


def test_baseline_improved_and_added_removed():
    baseline = [_case_result("c1", hit_at_5=False, reciprocal_rank=0.0), _case_result("gone")]
    current = [_case_result("c1", reciprocal_rank=1.0), _case_result("new")]
    comparison = compare_retrieval_baseline(current, baseline)
    assert comparison.improved_cases == ["c1"]
    assert comparison.added_cases == ["new"]
    assert comparison.removed_cases == ["gone"]
