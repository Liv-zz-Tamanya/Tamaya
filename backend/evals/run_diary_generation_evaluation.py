"""일기 생성 품질 평가 실행기 (CLI).

diary fixture의 대화를 실제 CLOVA generate_diary에 넣어 제목·본문·감정·키워드
변환 품질을 잰다. 핵심 사건 반영(gold chunk), 원문에 없는 사건, assistant 발화
혼동을 문장 단위 임베딩 grounding으로 검사한다.

    uv run python -m evals.run_diary_generation_evaluation
    uv run python -m evals.run_diary_generation_evaluation --fixture-id diary-hana-0602 --repeat 3

DB 미사용. CLOVA 호출 비용 발생(fixture 12건 × repeat).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from app.application.service.diary_generation_prompt import (
    DIARY_SYSTEM_PROMPT,
    DIARY_USER_REQUEST,
)
from app.infrastructure.config.settings import settings
from evals.chunk_metrics import DEFAULT_SIMILARITY_THRESHOLD
from evals.diary_generation_metrics import (
    analyze_diary_case,
    parse_diary_output,
    split_sentences,
    summarize_diary_results,
)
from evals.diary_generation_results import DiaryCaseResult, DiaryRunReport
from evals.report import _git_metadata, _hash_json
from evals.run_chunk_evaluation import _real_extraction_client, messages_for_day
from evals.validate_fixtures import FIXTURE_DIR, load_fixture_set


async def run_diary_generation_cases(
    days,
    ai,
    embedding_service,
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    repeat: int = 1,
) -> list[DiaryCaseResult]:
    results: list[DiaryCaseResult] = []
    for day in days:
        for run_number in range(1, repeat + 1):
            try:
                raw = await ai.generate_diary(messages_for_day(day))
            except ValueError as exc:
                # JSON 파싱 실패는 실행 오류가 아니라 출력 계약 위반으로 집계
                results.append(
                    DiaryCaseResult(
                        fixture_id=day.fixture_id, device_id=day.device_id,
                        run_number=run_number, invalid_json=True,
                        schema_errors=[str(exc)[:200]],
                    )
                )
                continue
            except Exception as exc:
                results.append(
                    DiaryCaseResult(
                        fixture_id=day.fixture_id, device_id=day.device_id,
                        run_number=run_number, execution_error=str(exc),
                    )
                )
                continue
            fields, schema_errors = parse_diary_output(raw)
            sentences = split_sentences(fields.get("content", ""))
            gold_texts = [chunk.text for chunk in day.gold_chunks]
            user_texts = [m.content for m in day.messages if m.role == "user"]
            assistant_texts = [m.content for m in day.messages if m.role == "assistant"]
            all_texts = list(sentences) + gold_texts + user_texts + assistant_texts
            embeddings = embedding_service.embed(all_texts) if all_texts else []
            offset_gold = len(sentences)
            offset_user = offset_gold + len(gold_texts)
            offset_assistant = offset_user + len(user_texts)
            results.append(
                analyze_diary_case(
                    day, fields, schema_errors,
                    sentence_embeddings=embeddings[:offset_gold],
                    gold_embeddings=embeddings[offset_gold:offset_user],
                    user_embeddings=embeddings[offset_user:offset_assistant],
                    assistant_embeddings=embeddings[offset_assistant:],
                    sentences=sentences,
                    threshold=threshold,
                    run_number=run_number,
                )
            )
    return results


def diary_prompt_hash() -> str:
    return _hash_json({"system": DIARY_SYSTEM_PROMPT, "user_request": DIARY_USER_REQUEST})


def build_diary_report(
    results: list[DiaryCaseResult],
    started_at: datetime,
    threshold: float,
    repeat: int,
    embedding_model: str,
) -> DiaryRunReport:
    return DiaryRunReport(
        run_id=started_at.strftime("%Y%m%dT%H%M%SZ"),
        started_at=started_at,
        completed_at=datetime.now(UTC),
        model=settings.clova_model,
        prompt_hash=diary_prompt_hash(),
        embedding_model=embedding_model,
        similarity_threshold=threshold,
        repeat=repeat,
        **_git_metadata(),
        summary=summarize_diary_results(results),
        by_device={
            key: summarize_diary_results([r for r in results if r.device_id == key])
            for key in sorted({r.device_id for r in results})
        },
        cases=results,
    )


def write_diary_report(report: DiaryRunReport, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def print_diary_summary(report: DiaryRunReport) -> None:
    summary = report.summary
    print("\nDiary Generation Evaluation\n")
    print(
        f"Runs: {summary.case_runs} (완료 {summary.completed_runs}, JSON 위반 {summary.invalid_json_runs}, "
        f"오류 {summary.execution_error_runs}, threshold {report.similarity_threshold})"
    )
    print(f"핵심 사건 반영률(recall): {summary.mean_event_recall}  누락 사건 {summary.missed_event_total}건")
    print(
        f"원문에 없는 문장 {summary.ungrounded_sentence_total}건({summary.ungrounded_sentence_runs}개 실행)  "
        f"assistant 발화 혼동 {summary.assistant_confusion_total}건({summary.assistant_confusion_runs}개 실행)"
    )
    print(
        f"문장 수(4~5) 준수 {summary.sentence_count_ok_rate}%  감정 타당 {summary.emotion_plausible_rate}%  "
        f"schema 위반 {summary.schema_violation_runs}건  일반어 키워드 {summary.generic_keyword_runs}건  "
        f"미근거 키워드 {summary.ungrounded_keyword_runs}건"
    )
    for result in report.cases:
        problems = []
        if result.execution_error:
            problems.append(f"ERROR {result.execution_error}")
        if result.invalid_json:
            problems.append("JSON 파싱 실패")
        if result.schema_errors and not result.invalid_json:
            problems.append(f"schema: {'; '.join(result.schema_errors)}")
        missed = [item.chunk_id for item in result.event_coverage if not item.covered]
        if missed:
            problems.append(f"누락 사건: {', '.join(missed)}")
        if result.emotion_plausible is False:
            problems.append(f"감정 의외: {result.emotion}")
        if result.ungrounded_keywords:
            problems.append(f"미근거 키워드: {result.ungrounded_keywords}")
        for grounding in result.sentences:
            if grounding.status != "grounded":
                problems.append(f"[{grounding.status} sim={grounding.best_similarity}] \"{grounding.sentence[:60]}\"")
        if problems:
            print(f"- {result.fixture_id}#{result.run_number}: " + " | ".join(problems[:2]))
            for problem in problems[2:]:
                print(f"    {problem}")


async def _run(args: argparse.Namespace) -> int:
    fixtures = load_fixture_set(args.fixture_dir)
    days = fixtures.diary_days
    if args.fixture_id is not None:
        days = [day for day in days if day.fixture_id == args.fixture_id]
        if not days:
            raise ValueError(f"fixture not found: {args.fixture_id}")
    if args.limit is not None:
        days = days[: args.limit]
    ai = _real_extraction_client()
    from app.infrastructure.external.embedding_service_impl import (
        _MODEL_NAME,
        SentenceTransformerEmbeddingService,
    )

    print(
        f"This run calls the real CLOVA API ({len(days)}건 × repeat {args.repeat}) and may incur cost. "
        "Production DB and user data are not used."
    )
    started_at = datetime.now(UTC)
    results = await run_diary_generation_cases(
        days, ai, SentenceTransformerEmbeddingService(),
        threshold=args.threshold, repeat=args.repeat,
    )
    report = build_diary_report(results, started_at, args.threshold, args.repeat, _MODEL_NAME)
    output = args.output or Path(__file__).parent / "reports" / f"{report.run_id}-diary-generation-eval.json"
    write_diary_report(report, output)
    print_diary_summary(report)
    print(f"\nReport: {output}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run diary generation quality evaluation")
    parser.add_argument("--fixture-dir", type=Path, default=FIXTURE_DIR)
    parser.add_argument("--fixture-id")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--threshold", type=float, default=DEFAULT_SIMILARITY_THRESHOLD)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    if args.repeat < 1:
        parser.error("--repeat must be at least 1")
    if not 0.0 < args.threshold <= 1.0:
        parser.error("--threshold must be in (0, 1]")
    try:
        return asyncio.run(_run(args))
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"일기 생성 평가를 시작할 수 없습니다: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
