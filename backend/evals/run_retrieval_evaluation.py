"""Retrieval 검색 평가 실행기 (CLI) — Agent를 제외하고 검색 service를 직접 호출한다.

    uv run python -m evals.run_retrieval_evaluation
    uv run python -m evals.run_retrieval_evaluation --case-id ret-diary-001
    uv run python -m evals.run_retrieval_evaluation --baseline evals/baselines/retrieval-baseline.json --fail-on-regression

전제: 평가 전용 DB에 fixture가 시드되어 있어야 한다(evals.seed_fixtures).
LLM 호출이 없고 임베딩은 로컬 모델이므로 비용이 들지 않는다.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.infrastructure.persistence.models import EventChunkModel, HealthChunkModel
from evals.report import _git_metadata
from evals.retrieval_metrics import (
    compare_retrieval_baseline,
    first_relevant_rank,
    hit_at,
    precision_at,
    recall_at,
    reciprocal_rank,
    summarize_retrieval,
)
from evals.retrieval_results import (
    RetrievalCaseResult,
    RetrievalRunReport,
    RetrievedDoc,
)
from evals.retrieval_schemas import RetrievalEvalCase, RetrievalKind
from evals.seed_fixtures import fixture_uuid, require_eval_database_url
from evals.validate_fixtures import FIXTURE_DIR, FixtureSet, load_fixture_set
from evals.validate_retrieval_dataset import (
    DATASET_DIR,
    RETRIEVAL_DATASET_FILENAME,
    load_retrieval_cases,
    validate_retrieval_cases,
)

DEFAULT_TOP_K = 5


class ChunkCatalog:
    """fixture 기준 chunk UUID → (라벨, 소유 device) 역매핑.

    검색 결과의 UUID를 사람이 읽을 수 있는 chunk_id 라벨로 되돌리고,
    다른 사용자 chunk(유출)와 fixture 밖 데이터(unknown)를 식별한다.
    """

    def __init__(self, fixtures: FixtureSet) -> None:
        self.diary: dict[UUID, tuple[str, str]] = {
            fixture_uuid("event-chunk", chunk.chunk_id): (chunk.chunk_id, day.device_id)
            for day in fixtures.diary_days
            for chunk in day.gold_chunks
        }
        self.health: dict[UUID, tuple[str, str]] = {
            fixture_uuid("health-chunk", day.fixture_id): (day.fixture_id, day.device_id)
            for day in fixtures.health_days
        }

    def lookup(self, kind: RetrievalKind, row_id: UUID) -> tuple[str, str] | None:
        table = self.diary if kind == RetrievalKind.DIARY else self.health
        return table.get(row_id)


def score_case(
    case: RetrievalEvalCase, retrieved_ids: Sequence[UUID], catalog: ChunkCatalog, top_k: int
) -> RetrievalCaseResult:
    retrieved: list[RetrievedDoc] = []
    labels: list[str] = []
    leaked: list[str] = []
    unknown: list[str] = []
    relevant = set(case.relevant_chunk_ids)
    for rank, row_id in enumerate(retrieved_ids, start=1):
        entry = catalog.lookup(case.kind, row_id)
        if entry is None:
            label = f"unknown:{row_id}"
            unknown.append(str(row_id))
            leaked_from = None
        else:
            label, owner = entry
            leaked_from = owner if owner != case.device_id else None
            if leaked_from:
                leaked.append(label)
        labels.append(label)
        retrieved.append(
            RetrievedDoc(rank=rank, label=label, relevant=label in relevant, leaked_from=leaked_from)
        )
    if not case.relevant_chunk_ids:
        return RetrievalCaseResult(
            case_id=case.id, kind=case.kind, device_id=case.device_id, category=case.category,
            query=case.query, relevant_chunk_ids=[], retrieved=retrieved,
            rank_metrics_evaluable=False, empty_expected=True,
            empty_check_passed=not retrieved, leaked_labels=leaked, unknown_ids=unknown,
        )
    return RetrievalCaseResult(
        case_id=case.id, kind=case.kind, device_id=case.device_id, category=case.category,
        query=case.query, relevant_chunk_ids=case.relevant_chunk_ids, retrieved=retrieved,
        hit_at_1=hit_at(1, case.relevant_chunk_ids, labels),
        hit_at_3=hit_at(3, case.relevant_chunk_ids, labels),
        hit_at_5=hit_at(5, case.relevant_chunk_ids, labels),
        precision_at_k=precision_at(top_k, case.relevant_chunk_ids, labels),
        recall_at_k=recall_at(top_k, case.relevant_chunk_ids, labels),
        reciprocal_rank=reciprocal_rank(case.relevant_chunk_ids, labels),
        first_relevant_rank=first_relevant_rank(case.relevant_chunk_ids, labels),
        leaked_labels=leaked, unknown_ids=unknown,
    )


async def run_retrieval_cases(
    cases: Sequence[RetrievalEvalCase],
    diary_query,
    health_query,
    fixtures: FixtureSet,
    top_k: int = DEFAULT_TOP_K,
) -> list[RetrievalCaseResult]:
    catalog = ChunkCatalog(fixtures)
    results: list[RetrievalCaseResult] = []
    for case in cases:
        if case.kind == RetrievalKind.DIARY:
            rows = await diary_query.search_similar(case.device_id, case.query, limit=top_k)
        else:
            rows = await health_query.search_similar(case.device_id, case.query, limit=top_k)
        results.append(score_case(case, [row.id for row in rows], catalog, top_k))
    return results


async def verify_seeded(engine, fixtures: FixtureSet) -> list[str]:
    """fixture의 모든 chunk가 DB에 있는지 확인하고 없는 라벨 목록을 반환한다."""
    catalog = ChunkCatalog(fixtures)
    missing: list[str] = []
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        for model, table in ((EventChunkModel, catalog.diary), (HealthChunkModel, catalog.health)):
            ids = list(table.keys())
            found = set(
                (await session.execute(select(model.id).where(model.id.in_(ids)))).scalars()
            )
            missing.extend(label for row_id, (label, _) in table.items() if row_id not in found)
    return missing


def build_retrieval_report(
    results: list[RetrievalCaseResult],
    started_at: datetime,
    top_k: int,
    embedding_model: str,
    baseline: Sequence[RetrievalCaseResult] | None = None,
) -> RetrievalRunReport:
    return RetrievalRunReport(
        run_id=started_at.strftime("%Y%m%dT%H%M%SZ"),
        started_at=started_at,
        completed_at=datetime.now(UTC),
        top_k=top_k,
        embedding_model=embedding_model,
        **_git_metadata(),
        summary=summarize_retrieval(results),
        by_kind={
            key: summarize_retrieval([r for r in results if r.kind.value == key])
            for key in sorted({r.kind.value for r in results})
        },
        by_category={
            key: summarize_retrieval([r for r in results if r.category == key])
            for key in sorted({r.category for r in results})
        },
        cases=results,
        baseline_comparison=(
            compare_retrieval_baseline(results, baseline) if baseline is not None else None
        ),
    )


def load_retrieval_baseline(path: Path) -> list[RetrievalCaseResult]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return [RetrievalCaseResult.model_validate(item) for item in raw["cases"]]
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"incompatible retrieval baseline {path}: {exc}") from exc


def write_retrieval_report(report: RetrievalRunReport, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def print_retrieval_summary(report: RetrievalRunReport) -> None:
    summary = report.summary
    print("\nRetrieval Evaluation\n")
    print(f"Cases: {summary.case_count} (rank-evaluable {summary.evaluable_cases}, top_k={report.top_k})")
    print(f"Hit@1: {summary.hit_rate_at_1}%  Hit@3: {summary.hit_rate_at_3}%  Hit@5: {summary.hit_rate_at_5}%")
    print(f"Recall@k: {summary.mean_recall_at_k}  Precision@k: {summary.mean_precision_at_k}  MRR: {summary.mrr}")
    print(f"Empty checks: {summary.empty_check_passed_cases}/{summary.empty_expected_cases}")
    print(f"Cross-user leaks: {summary.leak_violation_cases}  Unknown results: {summary.unknown_result_cases}")
    for kind, kind_summary in report.by_kind.items():
        print(f"- {kind}: Hit@1 {kind_summary.hit_rate_at_1}%, Hit@5 {kind_summary.hit_rate_at_5}%, MRR {kind_summary.mrr}")
    misses = [r for r in report.cases if r.rank_metrics_evaluable and not r.hit_at_1]
    if misses:
        print("\nCases without Hit@1:")
        for result in misses:
            top = result.retrieved[0].label if result.retrieved else "(no result)"
            print(f"- {result.case_id} [{result.category}] first_relevant_rank={result.first_relevant_rank} top1={top}")
    if report.baseline_comparison:
        comparison = report.baseline_comparison
        print(f"\nBaseline comparison:\nImproved: {len(comparison.improved_cases)}\nRegressed: {len(comparison.regressed_cases)} {comparison.regressed_cases}")


async def _run(args: argparse.Namespace) -> int:
    url = require_eval_database_url(args.database_url)
    fixtures = load_fixture_set(args.fixture_dir)
    cases, errors = load_retrieval_cases(args.dataset)
    errors += validate_retrieval_cases(cases, fixtures, args.dataset)
    if errors:
        raise ValueError("retrieval 데이터셋 검증 실패:\n" + "\n".join(f"- {e}" for e in errors))
    if args.case_id is not None:
        cases = [case for case in cases if case.id == args.case_id]
        if not cases:
            raise ValueError(f"case not found: {args.case_id}")
    if args.limit is not None:
        cases = cases[: args.limit]
    baseline = load_retrieval_baseline(args.baseline) if args.baseline else None

    engine = create_async_engine(url.render_as_string(hide_password=False))
    try:
        missing = await verify_seeded(engine, fixtures)
        if missing:
            raise RuntimeError(
                f"평가 DB에 fixture chunk {len(missing)}개가 없습니다 "
                f"(예: {missing[:3]}). 먼저 실행하세요: uv run python -m evals.seed_fixtures"
            )
        from app.application.service.diary_memory_query_service import DiaryMemoryQueryService
        from app.application.service.health_record_query_service import HealthRecordQueryService
        from app.infrastructure.external.embedding_service_impl import (
            _MODEL_NAME,
            SentenceTransformerEmbeddingService,
        )
        from app.infrastructure.persistence.event_chunk_repository_impl import (
            EventChunkRepositoryImpl,
        )
        from app.infrastructure.persistence.health_chunk_repository_impl import (
            HealthChunkRepositoryImpl,
        )

        print("LLM 호출 없음 — 로컬 임베딩과 평가 DB만 사용합니다.")
        started_at = datetime.now(UTC)
        embedding = SentenceTransformerEmbeddingService()
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            results = await run_retrieval_cases(
                cases,
                DiaryMemoryQueryService(embedding, EventChunkRepositoryImpl(session)),
                HealthRecordQueryService(embedding, HealthChunkRepositoryImpl(session)),
                fixtures,
                top_k=args.top_k,
            )
        report = build_retrieval_report(results, started_at, args.top_k, _MODEL_NAME, baseline)
    finally:
        await engine.dispose()

    output = args.output or Path(__file__).parent / "reports" / f"{report.run_id}-retrieval-eval.json"
    write_retrieval_report(report, output)
    print_retrieval_summary(report)
    print(f"\nReport: {output}")
    if args.fail_on_regression and report.baseline_comparison and report.baseline_comparison.regressed_cases:
        return 1
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run retrieval evaluation against the eval DB")
    parser.add_argument("--dataset", type=Path, default=DATASET_DIR / RETRIEVAL_DATASET_FILENAME)
    parser.add_argument("--fixture-dir", type=Path, default=FIXTURE_DIR)
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--case-id")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fail-on-regression", action="store_true")
    args = parser.parse_args(argv)
    if args.top_k < DEFAULT_TOP_K:
        parser.error(f"--top-k must be at least {DEFAULT_TOP_K} (Hit@5를 계산해야 합니다)")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    if args.fail_on_regression and args.baseline is None:
        parser.error("--fail-on-regression requires --baseline")
    if args.database_url is None:
        from app.infrastructure.config.settings import settings

        args.database_url = settings.eval_database_url
    try:
        return asyncio.run(_run(args))
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Retrieval 평가를 시작할 수 없습니다: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
