"""리포트 회귀 비교 도구 테스트."""

import json

import pytest

from evals.compare_reports import (
    compare_summaries,
    detect_report_kind,
    main,
)

RETRIEVAL_SUMMARY = {
    "hit_rate_at_1": 44.8, "hit_rate_at_3": 93.1, "hit_rate_at_5": 96.6,
    "mean_recall_at_k": 0.966, "mean_precision_at_k": 0.234, "mrr": 0.674,
    "leak_violation_cases": 0, "unknown_result_cases": 0,
}
SIGNAL_SUMMARY = {
    "behavior_precision": 0.938, "behavior_recall": 0.938,
    "behavior_f1": 0.938, "polarity_accuracy": 93.3,
}


def test_detect_report_kind():
    assert detect_report_kind(RETRIEVAL_SUMMARY) == "retrieval"
    assert detect_report_kind(SIGNAL_SUMMARY) == "signal-extraction"
    assert detect_report_kind({"unknown": 1}) is None


def test_compare_detects_regression_by_direction():
    worse = dict(RETRIEVAL_SUMMARY, hit_rate_at_1=40.0, leak_violation_cases=1)
    regressions, _ = compare_summaries("retrieval", RETRIEVAL_SUMMARY, worse)
    assert any("hit_rate_at_1" in r for r in regressions)
    assert any("leak_violation_cases" in r for r in regressions)  # 낮을수록 좋음 → 증가는 회귀
    improvements, _ = compare_summaries(
        "retrieval", RETRIEVAL_SUMMARY, dict(RETRIEVAL_SUMMARY, hit_rate_at_1=50.0)
    )
    assert improvements == []


def test_tolerance_absorbs_noise():
    slightly_worse = dict(SIGNAL_SUMMARY, polarity_accuracy=90.0)
    regressions, _ = compare_summaries("signal-extraction", SIGNAL_SUMMARY, slightly_worse)
    assert regressions  # tolerance 0 → 회귀
    regressions, _ = compare_summaries(
        "signal-extraction", SIGNAL_SUMMARY, slightly_worse, tolerance=5.0
    )
    assert regressions == []  # 3.3 하락은 tolerance 5 안


def test_none_values_are_excluded():
    baseline = dict(SIGNAL_SUMMARY, behavior_f1=None)
    regressions, rows = compare_summaries("signal-extraction", baseline, SIGNAL_SUMMARY)
    assert regressions == []
    assert any("비교 제외" in row for row in rows)


def _write_report(path, summary):
    path.write_text(json.dumps({"summary": summary}), encoding="utf-8")


def test_main_end_to_end(tmp_path, capsys):
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    _write_report(baseline, RETRIEVAL_SUMMARY)
    _write_report(current, dict(RETRIEVAL_SUMMARY, mrr=0.5))
    assert main([str(baseline), str(current)]) == 1
    assert "회귀 감지" in capsys.readouterr().out
    _write_report(current, dict(RETRIEVAL_SUMMARY, mrr=0.7))
    assert main([str(baseline), str(current)]) == 0


def test_main_rejects_mismatched_kinds(tmp_path):
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    _write_report(baseline, RETRIEVAL_SUMMARY)
    _write_report(current, SIGNAL_SUMMARY)
    assert main([str(baseline), str(current)]) == 2


def test_main_rejects_negative_tolerance(tmp_path):
    with pytest.raises(SystemExit):
        main(["a.json", "b.json", "--tolerance", "-1"])
