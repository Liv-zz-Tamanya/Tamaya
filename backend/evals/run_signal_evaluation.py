"""코칭 정성신호 추출 평가 실행기 (CLI).

코칭 fixture 대화를 실제 CLOVA extract_signal에 넣어 감정·행동·polarity
추출을 gold 라벨과 대조한다 — 주간·월간 Insight의 원천 데이터 품질 검증.

    uv run python -m evals.run_signal_evaluation
    uv run python -m evals.run_signal_evaluation --fixture-id coaching-hana-01 --repeat 3

DB 미사용. CLOVA 호출 비용 발생(fixture 10건 × repeat).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime, time
from pathlib import Path

from app.application.service.signal_extraction_prompt import (
    SIGNAL_EXTRACT_SYSTEM_PROMPT,
    SIGNAL_EXTRACT_USER_REQUEST,
)
from app.domain.model.chat_message import ChatMessage
from app.infrastructure.config.settings import settings
from evals.report import _git_metadata, _hash_json
from evals.signal_metrics import evaluate_signal_case, summarize_signal_results
from evals.signal_results import SignalCaseResult, SignalRunReport
from evals.signal_schemas import (
    CoachingSessionFixture,
    default_coaching_path,
    load_coaching_fixtures,
    validate_coaching_fixtures,
)
from evals.validate_fixtures import FIXTURE_DIR, load_fixture_set


def messages_for_session(fixture: CoachingSessionFixture) -> list[ChatMessage]:
    base = datetime.combine(datetime(2026, 7, 1).date(), time(20, 0))
    return [
        ChatMessage(role=message.role, content=message.content, created_at=base)
        for message in fixture.messages
    ]


async def run_signal_cases(
    sessions: Sequence[CoachingSessionFixture],
    service,
    repeat: int = 1,
) -> list[SignalCaseResult]:
    results: list[SignalCaseResult] = []
    for fixture in sessions:
        for run_number in range(1, repeat + 1):
            try:
                extracted = await service.extract_signal(messages_for_session(fixture))
            except Exception as exc:
                results.append(
                    SignalCaseResult(
                        fixture_id=fixture.fixture_id,
                        device_id=fixture.device_id,
                        run_number=run_number,
                        execution_error=str(exc),
                    )
                )
                continue
            results.append(evaluate_signal_case(fixture, extracted, run_number))
    return results


def signal_prompt_hash() -> str:
    return _hash_json(
        {"system": SIGNAL_EXTRACT_SYSTEM_PROMPT, "user_request": SIGNAL_EXTRACT_USER_REQUEST}
    )


def build_signal_report(
    results: list[SignalCaseResult],
    sessions: Sequence[CoachingSessionFixture],
    started_at: datetime,
    repeat: int,
) -> SignalRunReport:
    empty_ids = [fixture.fixture_id for fixture in sessions if not fixture.gold_behaviors]
    return SignalRunReport(
        run_id=started_at.strftime("%Y%m%dT%H%M%SZ"),
        started_at=started_at,
        completed_at=datetime.now(UTC),
        model=settings.clova_model,
        prompt_hash=signal_prompt_hash(),
        repeat=repeat,
        **_git_metadata(),
        summary=summarize_signal_results(results, empty_ids),
        by_device={
            key: summarize_signal_results(
                [r for r in results if r.device_id == key], empty_ids
            )
            for key in sorted({r.device_id for r in results})
        },
        cases=results,
    )


def write_signal_report(report: SignalRunReport, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def print_signal_summary(report: SignalRunReport) -> None:
    summary = report.summary
    print("\nCoaching Signal Extraction Evaluation\n")
    print(
        f"Runs: {summary.case_runs} (완료 {summary.completed_runs}, 추출 None {summary.extraction_none_runs}, "
        f"오류 {summary.execution_error_runs})"
    )
    print(
        f"Behavior — Precision: {summary.behavior_precision}  Recall: {summary.behavior_recall}  "
        f"F1: {summary.behavior_f1}  (TP {summary.true_positives} / FP {summary.false_positives} / FN {summary.false_negatives})"
    )
    print(f"Polarity 정확도: {summary.polarity_accuracy}%  감정 타당: {summary.emotion_plausible_rate}%")
    print(
        f"환각 실행 {summary.hallucination_runs}건  빈 행동 계약: {summary.empty_contract_passed}/{summary.empty_contract_cases}"
    )
    for result in report.cases:
        problems = []
        if result.execution_error:
            problems.append(f"ERROR {result.execution_error}")
        if result.extraction_none:
            problems.append("추출 None(파싱 실패 흡수)")
        if result.missed_behavior_ids:
            problems.append(f"누락: {', '.join(result.missed_behavior_ids)}")
        if result.hallucinated_behaviors:
            problems.append(f"환각: {result.hallucinated_behaviors}")
        for match in result.matches:
            if not match.polarity_match:
                problems.append(
                    f"polarity 오류: {match.behavior_id} gold {match.gold_polarity} → {match.extracted_polarity}"
                )
        if result.emotion_plausible is False:
            problems.append(f"감정 의외: {result.extracted_emotion}")
        if problems:
            print(f"- {result.fixture_id}#{result.run_number}: " + " | ".join(problems))


def _real_signal_client():
    if settings.clova_mock_mode or not settings.clova_api_key.strip():
        raise RuntimeError(
            "Real CLOVA credentials are required. Set CLOVA_MOCK_MODE=false and CLOVA_API_KEY "
            "before running signal evaluation."
        )
    from app.infrastructure.external.signal_extraction_clova import SignalExtractionClovaClient

    return SignalExtractionClovaClient()


async def _run(args: argparse.Namespace) -> int:
    fixtures = load_fixture_set(args.fixture_dir)
    path = default_coaching_path(args.fixture_dir)
    sessions, errors = load_coaching_fixtures(path)
    errors += validate_coaching_fixtures(sessions, fixtures, path)
    if errors:
        raise ValueError("coaching fixture 검증 실패:\n" + "\n".join(f"- {e}" for e in errors))
    if args.fixture_id is not None:
        sessions = [s for s in sessions if s.fixture_id == args.fixture_id]
        if not sessions:
            raise ValueError(f"fixture not found: {args.fixture_id}")
    if args.limit is not None:
        sessions = sessions[: args.limit]
    service = _real_signal_client()
    print(
        f"This run calls the real CLOVA API ({len(sessions)}건 × repeat {args.repeat}) and may incur cost. "
        "Production DB and user data are not used."
    )
    started_at = datetime.now(UTC)
    results = await run_signal_cases(sessions, service, repeat=args.repeat)
    report = build_signal_report(results, sessions, started_at, args.repeat)
    output = args.output or Path(__file__).parent / "reports" / f"{report.run_id}-signal-extraction-eval.json"
    write_signal_report(report, output)
    print_signal_summary(report)
    print(f"\nReport: {output}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run coaching signal extraction evaluation")
    parser.add_argument("--fixture-dir", type=Path, default=FIXTURE_DIR)
    parser.add_argument("--fixture-id")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    if args.repeat < 1:
        parser.error("--repeat must be at least 1")
    try:
        return asyncio.run(_run(args))
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"정성신호 평가를 시작할 수 없습니다: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
