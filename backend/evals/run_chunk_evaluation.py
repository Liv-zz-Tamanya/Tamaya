"""Event Chunk 생성 평가 실행기 (CLI).

diary fixture의 대화를 실제 CLOVA chunk 추출(extract_event_chunks)에 넣고,
fixture의 gold chunk와 임베딩 유사도로 대조해 누락·환각·과분할·병합과
metadata(event_type/who/where/when) 정확도를 잰다.

    uv run python -m evals.run_chunk_evaluation
    uv run python -m evals.run_chunk_evaluation --fixture-id diary-hana-0602 --repeat 3

DB는 사용하지 않는다. CLOVA 호출 비용이 발생한다(fixture 12건 × repeat).
검색 실패가 chunk 생성 문제인지 retriever 문제인지는 이 리포트와
retrieval 평가 리포트를 대조해 분리한다.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime, time
from pathlib import Path

from app.application.service.chunk_extraction_prompt import (
    CHUNK_EXTRACT_SYSTEM_PROMPT,
    CHUNK_EXTRACT_USER_REQUEST,
)
from app.domain.model.chat_message import ChatMessage
from app.infrastructure.config.settings import settings
from evals.chunk_metrics import (
    DEFAULT_SIMILARITY_THRESHOLD,
    analyze_case,
    summarize_chunk_results,
)
from evals.chunk_results import ChunkCaseResult, ChunkRunReport, ExtractedChunk
from evals.report import _git_metadata, _hash_json
from evals.validate_fixtures import FIXTURE_DIR, load_fixture_set


def messages_for_day(day) -> list[ChatMessage]:
    base = datetime.combine(day.session_date, time(21, 0))
    return [
        ChatMessage(role=message.role, content=message.content, created_at=base)
        for message in day.messages
    ]


def parse_extracted(raw_chunks: Sequence[object]) -> tuple[list[ExtractedChunk], int]:
    parsed = [ExtractedChunk.from_raw(raw) for raw in raw_chunks]
    valid = [chunk for chunk in parsed if chunk is not None]
    return valid, len(parsed) - len(valid)


async def run_chunk_cases(
    days,
    ai,
    embedding_service,
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    repeat: int = 1,
) -> list[ChunkCaseResult]:
    results: list[ChunkCaseResult] = []
    for day in days:
        for run_number in range(1, repeat + 1):
            try:
                raw_chunks = await ai.extract_event_chunks(messages_for_day(day))
                extracted, invalid_rows = parse_extracted(raw_chunks)
                gold_texts = [chunk.text for chunk in day.gold_chunks]
                extracted_texts = [chunk.text for chunk in extracted]
                embeddings = (
                    embedding_service.embed(gold_texts + extracted_texts)
                    if gold_texts or extracted_texts
                    else []
                )
                results.append(
                    analyze_case(
                        fixture_id=day.fixture_id,
                        device_id=day.device_id,
                        gold_chunks=day.gold_chunks,
                        extracted=extracted,
                        gold_embeddings=embeddings[: len(gold_texts)],
                        extracted_embeddings=embeddings[len(gold_texts):],
                        threshold=threshold,
                        invalid_rows=invalid_rows,
                        run_number=run_number,
                    )
                )
            except Exception as exc:
                results.append(
                    ChunkCaseResult(
                        fixture_id=day.fixture_id,
                        device_id=day.device_id,
                        run_number=run_number,
                        gold_count=len(day.gold_chunks),
                        execution_error=str(exc),
                    )
                )
    return results


def chunk_prompt_hash() -> str:
    return _hash_json(
        {"system": CHUNK_EXTRACT_SYSTEM_PROMPT, "user_request": CHUNK_EXTRACT_USER_REQUEST}
    )


def build_chunk_report(
    results: list[ChunkCaseResult],
    started_at: datetime,
    threshold: float,
    repeat: int,
    embedding_model: str,
) -> ChunkRunReport:
    return ChunkRunReport(
        run_id=started_at.strftime("%Y%m%dT%H%M%SZ"),
        started_at=started_at,
        completed_at=datetime.now(UTC),
        model=settings.clova_model,
        prompt_hash=chunk_prompt_hash(),
        embedding_model=embedding_model,
        similarity_threshold=threshold,
        repeat=repeat,
        **_git_metadata(),
        summary=summarize_chunk_results(results),
        by_device={
            key: summarize_chunk_results([r for r in results if r.device_id == key])
            for key in sorted({r.device_id for r in results})
        },
        cases=results,
    )


def write_chunk_report(report: ChunkRunReport, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def print_chunk_summary(report: ChunkRunReport) -> None:
    summary = report.summary
    print("\nEvent Chunk Extraction Evaluation\n")
    print(f"Runs: {summary.case_runs} (errors {summary.execution_error_runs}, threshold {report.similarity_threshold})")
    print(f"Gold {summary.gold_total} / Extracted {summary.extracted_total} / Matched {summary.matched_total}")
    print(f"Recall(사건 재현): {summary.mean_recall}  Precision: {summary.mean_precision}  Mean sim: {summary.mean_similarity}")
    print(f"누락 {summary.missed_total} (병합 의심 {summary.merged_total})  환각 의심 {summary.hallucinated_total}  과분할 {summary.over_split_total}  계약 위반 행 {summary.invalid_row_total}")
    print(f"Metadata — event_type: {summary.event_type_accuracy}%  who: {summary.who_accuracy}%  where: {summary.where_accuracy}%  when: {summary.when_accuracy}%")
    for result in report.cases:
        if result.execution_error:
            print(f"- {result.fixture_id}#{result.run_number}: ERROR {result.execution_error}")
    missed = [(r, m) for r in report.cases for m in r.missed]
    if missed:
        print("\n누락된 gold chunk:")
        for result, item in missed:
            suffix = " [병합 의심]" if item.merged else ""
            print(f"- {result.fixture_id}#{result.run_number}: {item.chunk_id} (best sim {item.best_similarity}){suffix}")
    hallucinated = [(r, u) for r in report.cases for u in r.unmatched if not u.over_split]
    if hallucinated:
        print("\n환각 의심 추출문:")
        for result, item in hallucinated:
            print(f"- {result.fixture_id}#{result.run_number}: \"{item.text}\" (best {item.best_gold_id} sim {item.best_similarity})")


def _real_extraction_client():
    if settings.clova_mock_mode or not settings.clova_api_key.strip():
        raise RuntimeError(
            "Real CLOVA credentials are required. Set CLOVA_MOCK_MODE=false and CLOVA_API_KEY "
            "before running chunk evaluation."
        )
    from app.infrastructure.external.clova_client import ClovaClient

    return ClovaClient()


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
    results = await run_chunk_cases(
        days,
        ai,
        SentenceTransformerEmbeddingService(),
        threshold=args.threshold,
        repeat=args.repeat,
    )
    report = build_chunk_report(results, started_at, args.threshold, args.repeat, _MODEL_NAME)
    output = args.output or Path(__file__).parent / "reports" / f"{report.run_id}-chunk-extraction-eval.json"
    write_chunk_report(report, output)
    print_chunk_summary(report)
    print(f"\nReport: {output}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run event chunk extraction evaluation")
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
        print(f"Chunk 평가를 시작할 수 없습니다: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
