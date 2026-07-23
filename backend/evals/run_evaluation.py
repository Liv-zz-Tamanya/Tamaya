"""PersonalAssistantAgent의 도구 선택 및 가드레일 오프라인 평가 실행기 (CLI).

구현은 하위 모듈로 분리되어 있다:

- results  — 결과·리포트 Pydantic 모델
- cases    — 데이터셋 로딩·선택, LangChain 메시지 변환
- judge    — 실행 record 1건의 케이스 판정
- metrics  — summary·반복 안정성·confusion matrix·baseline 비교
- runner   — 프로덕션 AgentFactory 경로로 케이스 실행
- report   — 리포트 조립·저장, 모델/프롬프트/git 메타데이터

아래 재노출(import) 목록은 기존 사용처(tests 등)와의 호환 표면이다.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from evals.cases import dataset_names, load_cases, messages_for_case, select_cases
from evals.judge import EXECUTION_ERROR_REASONS, evaluate_record
from evals.metrics import (
    case_stability,
    compare_baseline,
    stability_summary,
    summarize,
    tool_confusion_matrix,
)
from evals.report import (
    _hash_json,
    _prompt_metadata,
    _tool_schema_payload,
    build_report,
    load_baseline,
    print_summary,
    write_report,
)
from evals.results import (
    BaselineComparison,
    CaseStabilityResult,
    EvaluationCaseResult,
    EvaluationModelConfig,
    EvaluationRunReport,
    EvaluationSummary,
    LlmCallTrace,
    PromptMetadata,
    StabilitySummary,
    ToolCallTrace,
    ToolConfusionMatrix,
)
from evals.runner import (
    EVAL_DEVICE_ID,
    EVAL_SESSION_NAMESPACE,
    EvaluationRecorder,
    _real_evaluation_model,
    run_cases,
    run_repeated_cases,
)

__all__ = [
    "EVAL_DEVICE_ID",
    "EVAL_SESSION_NAMESPACE",
    "EXECUTION_ERROR_REASONS",
    "BaselineComparison",
    "CaseStabilityResult",
    "EvaluationCaseResult",
    "EvaluationModelConfig",
    "EvaluationRecorder",
    "EvaluationRunReport",
    "EvaluationSummary",
    "LlmCallTrace",
    "PromptMetadata",
    "StabilitySummary",
    "ToolCallTrace",
    "ToolConfusionMatrix",
    "_hash_json",
    "_prompt_metadata",
    "_real_evaluation_model",
    "_tool_schema_payload",
    "build_report",
    "case_stability",
    "compare_baseline",
    "dataset_names",
    "evaluate_record",
    "load_baseline",
    "load_cases",
    "main",
    "messages_for_case",
    "print_summary",
    "run_cases",
    "run_repeated_cases",
    "select_cases",
    "stability_summary",
    "summarize",
    "tool_confusion_matrix",
    "write_report",
]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run PersonalAssistantAgent evaluation")
    parser.add_argument("--dataset", choices=[*dataset_names(), "all"], default="all")
    parser.add_argument("--case-id")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--fail-on-mismatch", action="store_true")
    parser.add_argument("--fail-on-regression", action="store_true")
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    if args.repeat < 1:
        parser.error("--repeat must be at least 1")
    if args.fail_on_regression and args.baseline is None:
        parser.error("--fail-on-regression requires --baseline")
    datasets = dataset_names() if args.dataset == "all" else [args.dataset]
    try:
        cases = select_cases(load_cases(Path(__file__).parent / "datasets", datasets), args.case_id, args.limit)
        baseline = load_baseline(args.baseline) if args.baseline else None
        print("This run calls the real LLM API and may incur cost. Production DB and user data are not used.")
        started_at = datetime.now(UTC)
        model = _real_evaluation_model()
        report = build_report(
            asyncio.run(run_repeated_cases(cases, model=model, fail_fast=args.fail_fast, repeat=args.repeat)),
            datasets,
            started_at,
            args.repeat,
            baseline,
            model,
        )
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Evaluation could not start: {exc}", file=sys.stderr)
        return 2
    output = args.output or Path(__file__).parent / "reports" / f"{report.run_id}-personal-assistant-eval.json"
    write_report(report, output)
    print_summary(report)
    print(f"\nReport: {output}")
    mismatch = args.fail_on_mismatch and any(not r.combined_passed for r in report.cases)
    regression = args.fail_on_regression and report.baseline_comparison and report.baseline_comparison.regressed_cases
    return 1 if mismatch or regression else 0


if __name__ == "__main__":
    raise SystemExit(main())
