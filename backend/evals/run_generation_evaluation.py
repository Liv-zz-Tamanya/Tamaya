"""RAG 답변 생성 평가 실행기 (CLI) — 검색을 우회하고 정답 문서를 직접 주입한다.

프로덕션과 동일한 시스템 프롬프트·tool 스키마·tool 결과 wire 형식으로
"tool이 방금 이 문서들을 반환한 상태"를 재구성해 최종 답변만 생성시키고,
결정론 검사(완전성·처방 토큰)와 LLM judge(unsupported claim·abstention·
진단/처방)로 채점한다.

    uv run python -m evals.run_generation_evaluation
    uv run python -m evals.run_generation_evaluation --case-id gen-health-201 --repeat 3

DB 미사용. CLOVA 호출 비용 발생(케이스당 생성 1회 + judge 1회).
주의: 프로덕션의 input guardrail은 여기서 의도적으로 우회한다 —
guardrail이 뚫렸을 때 생성 모델이 마지막 방어선이 되는지를 재는 평가다.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from app.application.service.chat_message_adapter import extract_ai_message_text
from app.application.service.diary_chat_prompt import build_diary_chat_system_prompt
from app.application.service.health_chat_prompt import build_health_chat_system_prompt
from app.application.tool.read_tools import (
    AgentToolExecutionContext,
    DiaryMemoryToolItem,
    HealthRecordToolItem,
    SearchDiaryMemoriesResult,
    SearchHealthRecordsResult,
    create_read_tools,
    create_search_health_records_tool,
)
from app.application.usecase.personal_assistant_agent import PersonalAssistantMode
from app.infrastructure.config.settings import settings
from evals.generation_judge import (
    JUDGE_SYSTEM_PROMPT,
    JUDGE_USER_TEMPLATE,
    GenerationJudge,
)
from evals.generation_metrics import evaluate_answer, summarize_generation
from evals.generation_results import GenerationCaseResult, GenerationRunReport
from evals.generation_schemas import (
    GenerationEvalCase,
    GenerationMode,
    load_generation_cases,
    validate_generation_cases,
)
from evals.report import _git_metadata, _hash_json, _prompt_payload
from evals.runner import (
    EVAL_DEVICE_ID,
    _EmptyDiaryQuery,
    _EmptyHealthQuery,
    _real_evaluation_model,
)
from evals.seed_fixtures import fixture_uuid
from evals.validate_fixtures import FIXTURE_DIR, FixtureSet, load_fixture_set

DATASET_PATH = Path(__file__).parent / "datasets" / "generation_cases.jsonl"
TOOL_CALL_ID = "eval-generation-call-1"


def build_tool_result(case: GenerationEvalCase, fixtures: FixtureSet) -> tuple[dict, str]:
    """(tool 결과 JSON, judge용 문서 텍스트). 프로덕션 결과 모델을 그대로 사용한다."""
    if case.mode == GenerationMode.DIARY:
        chunk_map = {
            chunk.chunk_id: (day, chunk)
            for day in fixtures.diary_days
            for chunk in day.gold_chunks
        }
        items = [
            DiaryMemoryToolItem(
                id=str(fixture_uuid("event-chunk", chunk_id)),
                diary_date=chunk_map[chunk_id][0].session_date,
                text=chunk_map[chunk_id][1].text,
                event_type=chunk_map[chunk_id][1].event_type,
                who=chunk_map[chunk_id][1].who,
                where=chunk_map[chunk_id][1].where,
                when=chunk_map[chunk_id][1].when,
                tags=chunk_map[chunk_id][1].tags,
            )
            for chunk_id in case.context_chunk_ids
        ]
        result = SearchDiaryMemoriesResult(count=len(items), items=items)
        documents = "\n".join(f"- [{item.diary_date}] {item.text}" for item in items)
    else:
        day_map = {day.fixture_id: day for day in fixtures.health_days}
        items = [
            HealthRecordToolItem(
                id=str(fixture_uuid("health-chunk", chunk_id)),
                record_date=day_map[chunk_id].record_date,
                text=day_map[chunk_id].text,
                data_types=list(day_map[chunk_id].data_types),
            )
            for chunk_id in case.context_chunk_ids
        ]
        result = SearchHealthRecordsResult(count=len(items), items=items)
        documents = "\n".join(f"- [{item.record_date}] {item.text}" for item in items)
    return result.model_dump(mode="json"), documents


def build_generation_messages(case: GenerationEvalCase, tool_result: dict) -> list:
    if case.mode == GenerationMode.DIARY:
        system_prompt = build_diary_chat_system_prompt(
            max_turns=5, current_user_turn=1, suggest_finalize=False, tool_calling_enabled=True
        )
        tool_name = "search_diary_memories"
    else:
        system_prompt = build_health_chat_system_prompt(tool_calling_enabled=True)
        tool_name = "search_health_records"
    return [
        SystemMessage(content=system_prompt),
        HumanMessage(content=case.question),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": tool_name,
                    "args": {"query": case.question, "limit": 5},
                    "id": TOOL_CALL_ID,
                    "type": "tool_call",
                }
            ],
        ),
        ToolMessage(
            content=json.dumps(tool_result, ensure_ascii=False),
            tool_call_id=TOOL_CALL_ID,
            name=tool_name,
        ),
    ]


def tools_for_mode(mode: GenerationMode) -> list:
    context = AgentToolExecutionContext(device_id=EVAL_DEVICE_ID)
    if mode == GenerationMode.DIARY:
        return list(create_read_tools(_EmptyDiaryQuery(), _EmptyHealthQuery(), context))
    return [create_search_health_records_tool(_EmptyHealthQuery(), context)]


async def run_generation_cases(
    cases: Sequence[GenerationEvalCase],
    fixtures: FixtureSet,
    model,
    judge,
    repeat: int = 1,
) -> list[GenerationCaseResult]:
    results: list[GenerationCaseResult] = []
    for case in cases:
        tool_result, documents = build_tool_result(case, fixtures)
        messages = build_generation_messages(case, tool_result)
        tools = tools_for_mode(case.mode)
        for run_number in range(1, repeat + 1):
            try:
                response = await model.ainvoke(messages, tools)
                if response.tool_calls:
                    results.append(
                        GenerationCaseResult(
                            case_id=case.id, mode=case.mode, category=case.category,
                            device_id=case.device_id, question=case.question,
                            context_labels=case.context_chunk_ids, run_number=run_number,
                            answered=False, re_search=True,
                        )
                    )
                    continue
                answer = extract_ai_message_text(response)
                verdict = None
                judge_error = None
                try:
                    verdict = await judge.judge(documents, case.question, answer)
                except Exception as exc:
                    judge_error = str(exc)
                results.append(
                    evaluate_answer(
                        case, answer, verdict,
                        run_number=run_number,
                        context_labels=case.context_chunk_ids,
                        judge_error=judge_error,
                    )
                )
            except Exception as exc:
                results.append(
                    GenerationCaseResult(
                        case_id=case.id, mode=case.mode, category=case.category,
                        device_id=case.device_id, question=case.question,
                        context_labels=case.context_chunk_ids, run_number=run_number,
                        execution_error=str(exc),
                    )
                )
    return results


def build_generation_report(
    results: list[GenerationCaseResult], started_at: datetime, repeat: int
) -> GenerationRunReport:
    return GenerationRunReport(
        run_id=started_at.strftime("%Y%m%dT%H%M%SZ"),
        started_at=started_at,
        completed_at=datetime.now(UTC),
        model=settings.clova_model,
        judge_model=settings.clova_model,
        prompt_hash=_hash_json(
            _prompt_payload([PersonalAssistantMode.DIARY, PersonalAssistantMode.HEALTH])
        ),
        judge_prompt_hash=_hash_json(
            {"system": JUDGE_SYSTEM_PROMPT, "user_template": JUDGE_USER_TEMPLATE}
        ),
        repeat=repeat,
        **_git_metadata(),
        summary=summarize_generation(results),
        by_category={
            key: summarize_generation([r for r in results if r.category.value == key])
            for key in sorted({r.category.value for r in results})
        },
        cases=results,
    )


def write_generation_report(report: GenerationRunReport, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def print_generation_summary(report: GenerationRunReport) -> None:
    summary = report.summary
    print("\nRAG Generation Evaluation\n")
    print(f"Runs: {summary.case_runs} (answered {summary.answered_runs}, re-search {summary.re_search_runs}, errors {summary.execution_error_runs}, judge errors {summary.judge_error_runs})")
    print(f"Completeness: {summary.mean_completeness}  Faithful: {summary.faithful_rate}%  Unsupported-claim runs: {summary.unsupported_claim_runs}")
    print(f"Abstention: {summary.abstention_passed}/{summary.abstention_cases}  Boundary: {summary.boundary_passed}/{summary.boundary_cases}  Bait: {summary.bait_passed}/{summary.bait_cases}")
    print(f"Prescriptive-token runs: {summary.prescriptive_content_runs}")
    for result in report.cases:
        problems = []
        if result.execution_error:
            problems.append(f"ERROR {result.execution_error}")
        if result.re_search:
            problems.append("re-search 시도")
        if result.missing_fact_groups:
            problems.append(f"누락 사실: {', '.join(result.missing_fact_groups)}")
        if result.judge and result.judge.unsupported_claims:
            problems.append(f"unsupported: {result.judge.unsupported_claims}")
        if result.passed is False:
            problems.append("FAIL")
        if result.judge_error:
            problems.append(f"judge error: {result.judge_error}")
        if problems:
            print(f"- {result.case_id}#{result.run_number} [{result.category.value}]: {'; '.join(problems)}")
            if result.answer:
                print(f"  답변: {result.answer[:120]}")


async def _run(args: argparse.Namespace) -> int:
    fixtures = load_fixture_set(args.fixture_dir)
    cases, errors = load_generation_cases(args.dataset)
    errors += validate_generation_cases(cases, fixtures, args.dataset)
    if errors:
        raise ValueError("generation 데이터셋 검증 실패:\n" + "\n".join(f"- {e}" for e in errors))
    if args.case_id is not None:
        cases = [case for case in cases if case.id == args.case_id]
        if not cases:
            raise ValueError(f"case not found: {args.case_id}")
    if args.limit is not None:
        cases = cases[: args.limit]
    model = _real_evaluation_model()
    judge = GenerationJudge()
    print(
        f"This run calls the real CLOVA API ({len(cases)}건 × repeat {args.repeat} × 생성+judge) "
        "and may incur cost. Production DB and user data are not used."
    )
    started_at = datetime.now(UTC)
    results = await run_generation_cases(cases, fixtures, model, judge, repeat=args.repeat)
    report = build_generation_report(results, started_at, args.repeat)
    output = args.output or Path(__file__).parent / "reports" / f"{report.run_id}-generation-eval.json"
    write_generation_report(report, output)
    print_generation_summary(report)
    print(f"\nReport: {output}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run RAG generation evaluation")
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument("--fixture-dir", type=Path, default=FIXTURE_DIR)
    parser.add_argument("--case-id")
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
        print(f"Generation 평가를 시작할 수 없습니다: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
