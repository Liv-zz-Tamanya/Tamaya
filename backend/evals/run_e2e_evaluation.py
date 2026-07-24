"""End-to-End Agent RAG 평가 실행기 (CLI).

사용자 입력 → tool 선택 → query 생성 → 검색(평가 DB) → 최종 답변까지
프로덕션 agent 조립 경로 전체를 실행하고, 실패를 단계별로 분류한다.

    uv run python -m evals.run_e2e_evaluation
    uv run python -m evals.run_e2e_evaluation --case-id e2e-diary-001 --repeat 3

전제: 평가 DB에 fixture가 시드되어 있어야 한다(evals.seed_fixtures).
CLOVA 호출 비용 발생(agent 실행 + 필요한 경우 judge).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid5

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.application.service.agent_execution_observability import (
    AgentExecutionRecord,
    AgentTraceDetail,
)
from app.application.service.diary_chat_prompt import DiaryConversationContext
from app.application.usecase.personal_assistant_agent import PersonalAssistantMode
from app.application.usecase.personal_assistant_agent_factory import PersonalAssistantAgentFactory
from app.infrastructure.config.settings import settings
from evals.e2e_metrics import classify_stage, e2e_case_stability, summarize_e2e
from evals.e2e_results import (
    E2ECaseResult,
    E2EFailureStage,
    E2ERunReport,
    ToolQueryTrace,
)
from evals.e2e_schemas import E2EEvalCase, load_e2e_cases, validate_e2e_cases
from evals.generation_judge import GenerationJudge
from evals.generation_metrics import score_completeness
from evals.judge import EXECUTION_ERROR_REASONS
from evals.report import _git_metadata, _hash_json, _prompt_payload
from evals.retrieval_schemas import RetrievalKind
from evals.run_retrieval_evaluation import ChunkCatalog, verify_seeded
from evals.runner import EvaluationRecorder, _real_evaluation_model
from evals.schemas import ExpectedDecision
from evals.seed_fixtures import require_eval_database_url
from evals.validate_fixtures import FIXTURE_DIR, FixtureSet, load_fixture_set

DATASET_PATH = Path(__file__).parent / "datasets" / "e2e_cases.jsonl"
E2E_SESSION_NAMESPACE = UUID("9c2f0a77-3e1b-4f60-9d5a-6b8e4c2d1f03")
DEFAULT_TOP_K = 5


class RecordingDiaryQuery:
    """실제 검색 service를 감싸 (query, 반환 id)를 기록한다 — 검색 단계 분석용."""

    def __init__(self, inner) -> None:
        self._inner = inner
        self.calls: list[dict] = []

    async def search_similar(self, device_id, query, exclude_session_id=None, limit=5):
        rows = await self._inner.search_similar(
            device_id, query, exclude_session_id=exclude_session_id, limit=limit
        )
        self.calls.append(
            {"tool": "search_diary_memories", "query": query, "ids": [row.id for row in rows]}
        )
        return rows

    def reset(self) -> None:
        self.calls.clear()


class RecordingHealthQuery:
    def __init__(self, inner) -> None:
        self._inner = inner
        self.calls: list[dict] = []

    async def search_similar(self, device_id, query, limit=5):
        rows = await self._inner.search_similar(device_id, query, limit=limit)
        self.calls.append(
            {"tool": "search_health_records", "query": query, "ids": [row.id for row in rows]}
        )
        return rows

    def reset(self) -> None:
        self.calls.clear()


def messages_for_e2e_case(case: E2EEvalCase) -> list[BaseMessage]:
    messages: list[BaseMessage] = []
    for item in case.history:
        if item.role == "user":
            messages.append(HumanMessage(content=item.content))
        elif item.role == "assistant":
            messages.append(AIMessage(content=item.content))
        else:
            raise ValueError(f"case {case.id}: unsupported history role: {item.role}")
    messages.append(HumanMessage(content=case.input))
    return messages


def resolve_retrieval(
    calls: Sequence[dict], catalog: ChunkCatalog, device_id: str
) -> tuple[list[ToolQueryTrace], list[str], list[str], list[str]]:
    """(tool query trace, 검색된 라벨, 유출 라벨, unknown id)."""
    traces: list[ToolQueryTrace] = []
    labels: list[str] = []
    leaked: list[str] = []
    unknown: list[str] = []
    for call in calls:
        kind = RetrievalKind.DIARY if call["tool"] == "search_diary_memories" else RetrievalKind.HEALTH
        traces.append(
            ToolQueryTrace(tool=call["tool"], query=call["query"], result_count=len(call["ids"]))
        )
        for row_id in call["ids"]:
            entry = catalog.lookup(kind, row_id)
            if entry is None:
                unknown.append(str(row_id))
                continue
            label, owner = entry
            labels.append(label)
            if owner != device_id:
                leaked.append(label)
    return traces, labels, leaked, unknown


def build_document_text(fixtures: FixtureSet, labels: Sequence[str]) -> str:
    text_map = {
        chunk.chunk_id: f"[{day.session_date}] {chunk.text}"
        for day in fixtures.diary_days
        for chunk in day.gold_chunks
    }
    text_map.update(
        {day.fixture_id: f"[{day.record_date}] {day.text}" for day in fixtures.health_days}
    )
    return "\n".join(f"- {text_map[label]}" for label in labels if label in text_map)


async def run_e2e_cases(
    cases: Sequence[E2EEvalCase],
    fixtures: FixtureSet,
    model,
    judge,
    diary_query: RecordingDiaryQuery,
    health_query: RecordingHealthQuery,
    repeat: int = 1,
) -> list[E2ECaseResult]:
    catalog = ChunkCatalog(fixtures)
    recorder = EvaluationRecorder()
    factory = PersonalAssistantAgentFactory(
        model,
        diary_query,
        health_query,
        execution_recorder=recorder,
        trace_detail=AgentTraceDetail.FULL,
    )
    results: list[E2ECaseResult] = []
    for case in cases:
        for run_number in range(1, repeat + 1):
            recorder.reset()
            diary_query.reset()
            health_query.reset()
            error: Exception | None = None
            try:
                agent = factory.create(
                    device_id=case.device_id,
                    session_id=uuid5(E2E_SESSION_NAMESPACE, f"{case.id}:{run_number}"),
                    mode=case.mode,
                )
                await agent.run(
                    messages=messages_for_e2e_case(case),
                    mode=case.mode,
                    diary_context=DiaryConversationContext(
                        max_turns=5, current_user_turn=1, suggest_finalize=False
                    )
                    if case.mode == PersonalAssistantMode.DIARY
                    else None,
                    coaching_context={"persona": None}
                    if case.mode == PersonalAssistantMode.COACHING
                    else None,
                )
            except Exception as exc:
                error = exc
            record: AgentExecutionRecord | None
            try:
                record = recorder.only_record()
            except RuntimeError as recorder_error:
                record = None
                error = error or recorder_error
            results.append(
                await _evaluate_run(
                    case, run_number, record, error,
                    diary_query.calls + health_query.calls,
                    catalog, fixtures, judge,
                )
            )
    return results


async def _evaluate_run(
    case: E2EEvalCase,
    run_number: int,
    record: AgentExecutionRecord | None,
    error: Exception | None,
    retrieval_calls: Sequence[dict],
    catalog: ChunkCatalog,
    fixtures: FixtureSet,
    judge,
) -> E2ECaseResult:
    reason = record.termination_reason if record else None
    execution_error = str(error) if error else None
    if reason in EXECUTION_ERROR_REASONS:
        execution_error = execution_error or f"agent terminated: {reason.value}"
    actual_tools = list(record.tool_names) if record else []
    traces, labels, leaked, unknown = resolve_retrieval(retrieval_calls, catalog, case.device_id)
    answer = record.final_response_content if record else None
    completeness, matched, missing_facts = (
        score_completeness(case.expected_facts, answer) if answer else (None, [], [])
    )
    verdict = None
    judge_error = None
    needs_judge = (
        judge is not None
        and answer
        and execution_error is None
        and case.expected_decision == ExpectedDecision.TOOL_CALL
        and actual_tools
    )
    if needs_judge:
        try:
            verdict = await judge.judge(
                build_document_text(fixtures, labels), case.input, answer
            )
        except Exception as exc:
            judge_error = str(exc)
    stage = classify_stage(
        case, actual_tools, labels, leaked, execution_error,
        reason.value if reason else None, completeness, verdict,
    )
    missing_relevant = [c for c in case.relevant_chunk_ids if c not in set(labels)]
    return E2ECaseResult(
        case_id=case.id, mode=case.mode, category=case.category, device_id=case.device_id,
        input=case.input, run_number=run_number, expected_decision=case.expected_decision,
        actual_tools=actual_tools, tool_queries=traces, retrieved_labels=labels,
        missing_relevant=missing_relevant, leaked_labels=leaked, unknown_ids=unknown,
        answer=answer, completeness=completeness, matched_fact_groups=matched,
        missing_fact_groups=missing_facts, judge=verdict, judge_error=judge_error,
        stage=stage, passed=stage == E2EFailureStage.PASS,
        termination_reason=reason.value if reason else None,
        llm_calls=record.llm_calls if record else None,
        tool_rounds=record.tool_rounds if record else None,
        input_tokens=record.input_tokens if record else None,
        output_tokens=record.output_tokens if record else None,
        total_tokens=record.total_tokens if record else None,
        model_duration_ms=record.model_duration_ms if record else None,
        tool_duration_ms=record.tool_duration_ms if record else None,
        execution_duration_ms=record.execution_duration_ms if record else None,
        execution_error=execution_error,
    )


def build_e2e_report(
    results: list[E2ECaseResult], started_at: datetime, repeat: int, top_k: int, judge_model: str | None = None
) -> E2ERunReport:
    return E2ERunReport(
        run_id=started_at.strftime("%Y%m%dT%H%M%SZ"),
        started_at=started_at,
        completed_at=datetime.now(UTC),
        model=settings.clova_model,
        judge_model=judge_model or settings.clova_model,
        prompt_hash=_hash_json(
            _prompt_payload([PersonalAssistantMode.DIARY, PersonalAssistantMode.HEALTH])
        ),
        repeat=repeat,
        top_k=top_k,
        **_git_metadata(),
        summary=summarize_e2e(results),
        by_mode={
            key: summarize_e2e([r for r in results if r.mode.value == key])
            for key in sorted({r.mode.value for r in results})
        },
        by_category={
            key: summarize_e2e([r for r in results if r.category == key])
            for key in sorted({r.category for r in results})
        },
        case_stability=e2e_case_stability(results),
        cases=results,
    )


def write_e2e_report(report: E2ERunReport, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def print_e2e_summary(report: E2ERunReport) -> None:
    summary = report.summary
    print("\nEnd-to-End Agent RAG Evaluation\n")
    print(f"Runs: {summary.case_runs}  Pass: {summary.passed_runs} ({summary.pass_rate}%)")
    print(f"Stages: {summary.stage_counts}")
    print(
        f"Latency: mean {summary.mean_execution_duration_ms}ms, "
        f"p50 {summary.p50_execution_duration_ms}ms, p95 {summary.p95_execution_duration_ms}ms"
    )
    print(f"Tokens: mean {summary.mean_total_tokens}, total {summary.total_tokens_sum}")
    for mode, mode_summary in report.by_mode.items():
        print(f"- {mode}: {mode_summary.pass_rate}% {mode_summary.stage_counts}")
    failures = [r for r in report.cases if not r.passed]
    if failures:
        print("\n실패 실행:")
        for result in failures:
            queries = "; ".join(f"{t.tool}({t.query!r}→{t.result_count})" for t in result.tool_queries)
            print(f"- {result.case_id}#{result.run_number}: {result.stage.value} | tools={result.actual_tools} | {queries}")
            if result.missing_relevant:
                print(f"  누락 문서: {result.missing_relevant} (검색됨: {result.retrieved_labels})")
            if result.judge and result.judge.unsupported_claims:
                print(f"  unsupported: {result.judge.unsupported_claims}")
            if result.answer:
                print(f"  답변: {result.answer[:100]}")


async def _run(args: argparse.Namespace) -> int:
    url = require_eval_database_url(args.database_url)
    fixtures = load_fixture_set(args.fixture_dir)
    cases, errors = load_e2e_cases(args.dataset)
    errors += validate_e2e_cases(cases, fixtures, args.dataset)
    if errors:
        raise ValueError("e2e 데이터셋 검증 실패:\n" + "\n".join(f"- {e}" for e in errors))
    if args.case_id is not None:
        cases = [case for case in cases if case.id == args.case_id]
        if not cases:
            raise ValueError(f"case not found: {args.case_id}")
    if args.limit is not None:
        cases = cases[: args.limit]
    model = _real_evaluation_model()
    judge = GenerationJudge()

    engine = create_async_engine(url.render_as_string(hide_password=False))
    try:
        missing = await verify_seeded(engine, fixtures)
        if missing:
            raise RuntimeError(
                f"평가 DB에 fixture chunk {len(missing)}개가 없습니다. "
                "먼저 실행하세요: uv run python -m evals.seed_fixtures"
            )
        from app.application.service.diary_memory_query_service import DiaryMemoryQueryService
        from app.application.service.health_record_query_service import HealthRecordQueryService
        from app.infrastructure.external.embedding_service_impl import (
            SentenceTransformerEmbeddingService,
        )
        from app.infrastructure.persistence.event_chunk_repository_impl import (
            EventChunkRepositoryImpl,
        )
        from app.infrastructure.persistence.health_chunk_repository_impl import (
            HealthChunkRepositoryImpl,
        )

        print(
            f"This run calls the real CLOVA API ({len(cases)}건 × repeat {args.repeat} × agent+judge) "
            "and may incur cost. 평가 DB만 사용하며 운영 DB와 사용자 데이터는 쓰지 않는다."
        )
        started_at = datetime.now(UTC)
        embedding = SentenceTransformerEmbeddingService()
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            diary_query = RecordingDiaryQuery(
                DiaryMemoryQueryService(embedding, EventChunkRepositoryImpl(session))
            )
            health_query = RecordingHealthQuery(
                HealthRecordQueryService(embedding, HealthChunkRepositoryImpl(session))
            )
            results = await run_e2e_cases(
                cases, fixtures, model, judge, diary_query, health_query, repeat=args.repeat
            )
        report = build_e2e_report(results, started_at, args.repeat, DEFAULT_TOP_K, judge.model)
    finally:
        await engine.dispose()

    output = args.output or Path(__file__).parent / "reports" / f"{report.run_id}-e2e-eval.json"
    write_e2e_report(report, output)
    print_e2e_summary(report)
    print(f"\nReport: {output}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run end-to-end agent RAG evaluation")
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument("--fixture-dir", type=Path, default=FIXTURE_DIR)
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--case-id")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    if args.repeat < 1:
        parser.error("--repeat must be at least 1")
    if args.database_url is None:
        args.database_url = settings.eval_database_url
    try:
        return asyncio.run(_run(args))
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"E2E 평가를 시작할 수 없습니다: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
