"""Retrieval 순위 지표(Hit@k, Precision@k, Recall@k, MRR) 계산과 집계."""

from __future__ import annotations

from collections.abc import Sequence

from evals.retrieval_results import (
    RetrievalBaselineComparison,
    RetrievalCaseResult,
    RetrievalSummary,
)


def first_relevant_rank(relevant_ids: Sequence[str], retrieved_labels: Sequence[str]) -> int | None:
    relevant = set(relevant_ids)
    for index, label in enumerate(retrieved_labels, start=1):
        if label in relevant:
            return index
    return None


def hit_at(k: int, relevant_ids: Sequence[str], retrieved_labels: Sequence[str]) -> bool:
    relevant = set(relevant_ids)
    return any(label in relevant for label in retrieved_labels[:k])


def precision_at(k: int, relevant_ids: Sequence[str], retrieved_labels: Sequence[str]) -> float:
    relevant = set(relevant_ids)
    hits = sum(label in relevant for label in retrieved_labels[:k])
    return round(hits / k, 3) if k else 0.0


def recall_at(k: int, relevant_ids: Sequence[str], retrieved_labels: Sequence[str]) -> float:
    relevant = set(relevant_ids)
    if not relevant:
        return 0.0
    hits = len(relevant & set(retrieved_labels[:k]))
    return round(hits / len(relevant), 3)


def reciprocal_rank(relevant_ids: Sequence[str], retrieved_labels: Sequence[str]) -> float:
    rank = first_relevant_rank(relevant_ids, retrieved_labels)
    return round(1 / rank, 3) if rank else 0.0


def ndcg_at(k: int, relevant_ids: Sequence[str], retrieved_labels: Sequence[str]) -> float:
    """이진 관련도 NDCG@k — 이상 순위는 정답을 상위에 몰아넣은 배치."""
    from math import log2

    relevant = set(relevant_ids)
    if not relevant or k <= 0:
        return 0.0
    dcg = sum(
        1 / log2(rank + 1)
        for rank, label in enumerate(retrieved_labels[:k], start=1)
        if label in relevant
    )
    ideal = sum(1 / log2(rank + 1) for rank in range(1, min(k, len(relevant)) + 1))
    return round(dcg / ideal, 3) if ideal else 0.0


def percentile(values: Sequence[float], q: float) -> float | None:
    """nearest-rank 백분위 — 표본이 작아 보간 없이 결정론적으로 계산한다."""
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round(q * (len(ordered) - 1))))
    return round(ordered[index], 1)


def summarize_retrieval(results: Sequence[RetrievalCaseResult]) -> RetrievalSummary:
    evaluable = [result for result in results if result.rank_metrics_evaluable]
    empty_expected = [result for result in results if result.empty_expected]
    latencies = [
        result.search_latency_ms for result in results if result.search_latency_ms is not None
    ]
    return RetrievalSummary(
        case_count=len(results),
        evaluable_cases=len(evaluable),
        hit_rate_at_1=_rate([result.hit_at_1 for result in evaluable]),
        hit_rate_at_3=_rate([result.hit_at_3 for result in evaluable]),
        hit_rate_at_5=_rate([result.hit_at_5 for result in evaluable]),
        mean_precision_at_k=_mean([result.precision_at_k for result in evaluable]),
        mean_recall_at_k=_mean([result.recall_at_k for result in evaluable]),
        mrr=_mean([result.reciprocal_rank for result in evaluable]),
        mean_ndcg_at_k=_mean([result.ndcg_at_k for result in evaluable]),
        latency_ms_mean=_mean(latencies) if latencies else None,
        latency_ms_p50=percentile(latencies, 0.50),
        latency_ms_p95=percentile(latencies, 0.95),
        empty_expected_cases=len(empty_expected),
        empty_check_passed_cases=sum(bool(result.empty_check_passed) for result in empty_expected),
        leak_violation_cases=sum(bool(result.leaked_labels) for result in results),
        unknown_result_cases=sum(bool(result.unknown_ids) for result in results),
    )


def compare_retrieval_baseline(
    current: Sequence[RetrievalCaseResult], baseline: Sequence[RetrievalCaseResult]
) -> RetrievalBaselineComparison:
    now = {result.case_id: result for result in current}
    before = {result.case_id: result for result in baseline}
    matched = sorted(now.keys() & before.keys())
    improved: list[str] = []
    regressed: list[str] = []
    unchanged: list[str] = []
    for case_id in matched:
        current_case, baseline_case = now[case_id], before[case_id]
        current_rr = current_case.reciprocal_rank or 0.0
        baseline_rr = baseline_case.reciprocal_rank or 0.0
        regression = (
            (baseline_case.hit_at_5 and not current_case.hit_at_5)
            or current_rr < baseline_rr
            or (baseline_case.empty_check_passed and current_case.empty_check_passed is False)
            or (not baseline_case.leaked_labels and bool(current_case.leaked_labels))
        )
        if regression:
            regressed.append(case_id)
        elif current_rr > baseline_rr or (current_case.hit_at_5 and not baseline_case.hit_at_5):
            improved.append(case_id)
        else:
            unchanged.append(case_id)
    current_summary = summarize_retrieval(list(now.values()))
    baseline_summary = summarize_retrieval(list(before.values()))
    return RetrievalBaselineComparison(
        matched_cases=matched,
        added_cases=sorted(now.keys() - before.keys()),
        removed_cases=sorted(before.keys() - now.keys()),
        improved_cases=improved,
        regressed_cases=regressed,
        unchanged_cases=unchanged,
        hit_rate_at_1_delta=_delta(current_summary.hit_rate_at_1, baseline_summary.hit_rate_at_1),
        hit_rate_at_5_delta=_delta(current_summary.hit_rate_at_5, baseline_summary.hit_rate_at_5),
        mean_recall_at_k_delta=_delta(
            current_summary.mean_recall_at_k, baseline_summary.mean_recall_at_k
        ),
        mrr_delta=_delta(current_summary.mrr, baseline_summary.mrr),
    )


def _rate(values: Sequence[bool | None]) -> float | None:
    known = [value for value in values if value is not None]
    return round(sum(known) / len(known) * 100, 1) if known else None


def _mean(values: Sequence[float | None]) -> float | None:
    known = [value for value in values if value is not None]
    return round(sum(known) / len(known), 3) if known else None


def _delta(current: float | None, baseline: float | None) -> float | None:
    return round(current - baseline, 3) if current is not None and baseline is not None else None
