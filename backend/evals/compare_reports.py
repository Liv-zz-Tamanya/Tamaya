"""평가 리포트 회귀 비교 도구 — 같은 종류의 리포트 2개를 핵심 지표로 비교한다.

    uv run python -m evals.compare_reports baseline.json current.json
    uv run python -m evals.compare_reports baseline.json current.json --tolerance 1.0

리포트 종류는 summary 필드 구성으로 자동 감지한다. 추적 지표가 tolerance보다
크게 나빠지면 exit 1 — 정기/수동 CLOVA 평가에서 이전 리포트 대비 하락을 잡는다.
(LLM 평가는 비결정적이므로 tolerance 없이 쓰면 잡음에 민감하다 — 기본 0은
결정론 평가(retrieval)용이고, CLOVA 평가 비교에는 3~5 수준을 권장.)
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

# 리포트 종류별 (지표 경로, 높을수록 좋은가). 경로는 summary 안의 키.
# 종류 감지는 아래 지표 키가 모두 존재하는지로 판단한다.
TRACKED_METRICS: dict[str, list[tuple[str, bool]]] = {
    "retrieval": [
        ("hit_rate_at_1", True),
        ("hit_rate_at_3", True),
        ("hit_rate_at_5", True),
        ("mean_recall_at_k", True),
        ("mean_precision_at_k", True),
        ("mrr", True),
        ("leak_violation_cases", False),
        ("unknown_result_cases", False),
    ],
    "personal-assistant": [
        ("tool_check_rate", True),
        ("guardrail_check_rate", True),
        ("combined_rate", True),
        ("forbidden_tool_violation_cases", False),
    ],
    "chunk-extraction": [
        ("mean_recall", True),
        ("mean_precision", True),
        ("event_type_accuracy", True),
        ("who_accuracy", True),
        ("where_accuracy", True),
        ("when_accuracy", True),
    ],
    "generation": [
        ("mean_completeness", True),
        ("faithful_rate", True),
        ("unsupported_claim_runs", False),
        ("prescriptive_content_runs", False),
    ],
    "e2e": [
        ("pass_rate", True),
        ("p95_execution_duration_ms", False),
    ],
    "diary-generation": [
        ("mean_event_recall", True),
        ("sentence_count_ok_rate", True),
        ("emotion_plausible_rate", True),
        ("assistant_confusion_total", False),
    ],
    "signal-extraction": [
        ("behavior_precision", True),
        ("behavior_recall", True),
        ("behavior_f1", True),
        ("polarity_accuracy", True),
    ],
    "conversation": [
        ("pass_rate", True),
        ("blocked_runs", False),
    ],
}


def detect_report_kind(summary: dict) -> str | None:
    """summary 키 구성이 모두 일치하는 종류 중 가장 구체적인(일치 키 많은) 것."""
    best: tuple[int, str] | None = None
    for kind, metrics in TRACKED_METRICS.items():
        keys = [key for key, _ in metrics]
        if all(key in summary for key in keys):
            candidate = (len(keys), kind)
            if best is None or candidate > best:
                best = candidate
    return best[1] if best else None


def compare_summaries(
    kind: str, baseline: dict, current: dict, tolerance: float = 0.0
) -> tuple[list[str], list[str]]:
    """(악화 목록, 전체 비교 행 목록)을 반환한다. None 값은 비교에서 제외."""
    regressions: list[str] = []
    rows: list[str] = []
    for key, higher_is_better in TRACKED_METRICS[kind]:
        before = baseline.get(key)
        after = current.get(key)
        if not isinstance(before, int | float) or not isinstance(after, int | float):
            rows.append(f"{key}: {before} -> {after} (비교 제외)")
            continue
        delta = after - before
        direction = "↑" if higher_is_better else "↓"
        rows.append(f"{key} ({direction} 좋음): {before} -> {after} (Δ {round(delta, 3)})")
        worsened = delta < -tolerance if higher_is_better else delta > tolerance
        if worsened:
            regressions.append(f"{key}: {before} -> {after}")
    return regressions, rows


def load_summary(path: Path) -> dict:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"리포트를 읽을 수 없습니다: {path}: {exc}") from exc
    summary = report.get("summary")
    if not isinstance(summary, dict):
        raise ValueError(f"summary가 없는 리포트입니다: {path}")
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="평가 리포트 회귀 비교")
    parser.add_argument("baseline", type=Path)
    parser.add_argument("current", type=Path)
    parser.add_argument("--tolerance", type=float, default=0.0,
                        help="이만큼까지의 악화는 허용 (LLM 평가 잡음 흡수용, 권장 3~5)")
    args = parser.parse_args(argv)
    if args.tolerance < 0:
        parser.error("--tolerance must be >= 0")
    try:
        baseline = load_summary(args.baseline)
        current = load_summary(args.current)
    except ValueError as exc:
        print(f"비교를 시작할 수 없습니다: {exc}", file=sys.stderr)
        return 2
    kind = detect_report_kind(baseline)
    if kind is None or detect_report_kind(current) != kind:
        print("비교를 시작할 수 없습니다: 두 리포트의 종류가 같지 않거나 알 수 없습니다", file=sys.stderr)
        return 2
    regressions, rows = compare_summaries(kind, baseline, current, args.tolerance)
    print(f"리포트 종류: {kind} (tolerance {args.tolerance})")
    for row in rows:
        print(f"- {row}")
    if regressions:
        print(f"\n회귀 감지 ({len(regressions)}건):")
        for regression in regressions:
            print(f"- {regression}")
        return 1
    print("\n회귀 없음")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
