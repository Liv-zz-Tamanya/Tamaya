"""일반 대화 품질·Output Safety 평가 실행기 (CLI).

검색·DB 없이 프로덕션 agent 대화 경로를 실행하고, LLM judge(기본 CLOVA,
--judge-model로 교체 가능)와 결정론 검사로 채점한다. 판정 신뢰도 한계
때문에 사람 검수용 마크다운(review)을 함께 생성한다.

    uv run python -m evals.run_conversation_evaluation
    uv run python -m evals.run_conversation_evaluation --case-id conv-crisis-001 --repeat 3

CLOVA 호출 비용 발생(케이스당 agent 실행 + judge 1회).
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

from app.application.service.agent_execution_observability import AgentTraceDetail
from app.application.service.diary_chat_prompt import DiaryConversationContext
from app.application.usecase.personal_assistant_agent import PersonalAssistantMode
from app.application.usecase.personal_assistant_agent_factory import PersonalAssistantAgentFactory
from app.domain.service.medical_guardrail import contains_prescriptive_content
from app.infrastructure.config.settings import settings
from evals.conversation_judge import (
    CONVERSATION_JUDGE_SYSTEM_PROMPT,
    CONVERSATION_JUDGE_USER_TEMPLATE,
    ConversationJudge,
)
from evals.conversation_metrics import judge_conversation_pass, summarize_conversation
from evals.conversation_results import ConversationCaseResult, ConversationRunReport
from evals.conversation_schemas import (
    ConversationEvalCase,
    load_conversation_cases,
    validate_conversation_cases,
)
from evals.judge import EXECUTION_ERROR_REASONS
from evals.report import _git_metadata, _hash_json, _prompt_payload
from evals.runner import (
    EVAL_DEVICE_ID,
    EvaluationRecorder,
    _EmptyDiaryQuery,
    _EmptyHealthQuery,
    _real_evaluation_model,
)

DATASET_PATH = Path(__file__).parent / "datasets" / "conversation_cases.jsonl"
CONVERSATION_SESSION_NAMESPACE = UUID("1f7d3c2a-8b41-4e9f-b6d0-5a2c9e8f4b17")
GUARDRAIL_TERMINATIONS = frozenset({"input_guardrail_blocked", "output_guardrail_blocked"})


def messages_for_conversation_case(case: ConversationEvalCase) -> list[BaseMessage]:
    messages: list[BaseMessage] = []
    for item in case.history:
        if item.role == "user":
            messages.append(HumanMessage(content=item.content))
        else:
            messages.append(AIMessage(content=item.content))
    messages.append(HumanMessage(content=case.input))
    return messages


def history_text(case: ConversationEvalCase) -> str:
    return "\n".join(f"{item.role}: {item.content}" for item in case.history)


async def run_conversation_cases(
    cases: Sequence[ConversationEvalCase],
    model,
    judge,
    repeat: int = 1,
) -> list[ConversationCaseResult]:
    recorder = EvaluationRecorder()
    factory = PersonalAssistantAgentFactory(
        model,
        _EmptyDiaryQuery(),
        _EmptyHealthQuery(),
        execution_recorder=recorder,
        trace_detail=AgentTraceDetail.FULL,
    )
    results: list[ConversationCaseResult] = []
    for case in cases:
        for run_number in range(1, repeat + 1):
            recorder.reset()
            error: Exception | None = None
            try:
                agent = factory.create(
                    device_id=EVAL_DEVICE_ID,
                    session_id=uuid5(CONVERSATION_SESSION_NAMESPACE, f"{case.id}:{run_number}"),
                    mode=case.mode,
                )
                await agent.run(
                    messages=messages_for_conversation_case(case),
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
            try:
                record = recorder.only_record()
            except RuntimeError as recorder_error:
                record = None
                error = error or recorder_error
            reason = record.termination_reason if record else None
            execution_error = str(error) if error else None
            if reason in EXECUTION_ERROR_REASONS:
                execution_error = execution_error or f"agent terminated: {reason.value}"
            answer = record.final_response_content if record else None
            blocked = reason is not None and reason.value in GUARDRAIL_TERMINATIONS
            prescriptive = contains_prescriptive_content(answer) if answer else False
            verdict = None
            judge_error = None
            passed = None
            fail_reasons: list[str] = []
            if answer and execution_error is None:
                try:
                    verdict = await judge.judge(history_text(case), case.input, answer)
                except Exception as exc:
                    judge_error = str(exc)
                if verdict is not None:
                    passed, fail_reasons = judge_conversation_pass(
                        case.category, verdict, blocked, prescriptive
                    )
            results.append(
                ConversationCaseResult(
                    case_id=case.id, mode=case.mode, category=case.category, input=case.input,
                    run_number=run_number, answer=answer, blocked=blocked,
                    termination_reason=reason.value if reason else None,
                    actual_tools=list(record.tool_names) if record else [],
                    prescriptive_content=prescriptive, judge=verdict, judge_error=judge_error,
                    passed=passed, fail_reasons=fail_reasons,
                    total_tokens=record.total_tokens if record else None,
                    execution_duration_ms=record.execution_duration_ms if record else None,
                    execution_error=execution_error,
                )
            )
    return results


def build_conversation_report(
    results: list[ConversationCaseResult],
    started_at: datetime,
    repeat: int,
    judge_model: str,
) -> ConversationRunReport:
    return ConversationRunReport(
        run_id=started_at.strftime("%Y%m%dT%H%M%SZ"),
        started_at=started_at,
        completed_at=datetime.now(UTC),
        model=settings.clova_model,
        judge_model=judge_model,
        prompt_hash=_hash_json(
            _prompt_payload(
                [PersonalAssistantMode.DIARY, PersonalAssistantMode.HEALTH, PersonalAssistantMode.COACHING]
            )
        ),
        judge_prompt_hash=_hash_json(
            {"system": CONVERSATION_JUDGE_SYSTEM_PROMPT, "user_template": CONVERSATION_JUDGE_USER_TEMPLATE}
        ),
        repeat=repeat,
        **_git_metadata(),
        summary=summarize_conversation(results),
        cases=results,
    )


def write_conversation_report(report: ConversationRunReport, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_review_markdown(report: ConversationRunReport, output: Path) -> None:
    """사람 검수용 마크다운 — judge 판정을 사람이 재확인하는 워크플로우."""
    lines = [
        f"# 대화 품질 사람 검수 — run {report.run_id}",
        "",
        f"- 생성 모델: {report.model} / judge: {report.judge_model}"
        + (" (자기 채점 한계 있음 — 판정을 그대로 믿지 말 것)" if report.judge_model == report.model else " (외부 judge)"),
        "- 각 케이스의 judge 판정이 타당한지 확인하고 체크하세요.",
        "",
    ]
    for result in report.cases:
        verdict_json = (
            json.dumps(result.judge.model_dump(exclude={"raw_response"}), ensure_ascii=False)
            if result.judge
            else "(judge 없음)"
        )
        status = "PASS" if result.passed else ("FAIL" if result.passed is False else "미판정")
        lines += [
            f"## {result.case_id}#{result.run_number} [{result.category.value}] — {status}",
            "",
            f"- 입력: {result.input}",
            f"- 응답: {result.answer or '(없음)'}",
            f"- 차단: {result.blocked} / 실패 사유: {', '.join(result.fail_reasons) or '없음'}",
            f"- judge: {verdict_json}",
            "- [ ] judge 판정에 동의함",
            "- [ ] 이의 있음 (메모: )",
            "",
        ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")


def print_conversation_summary(report: ConversationRunReport) -> None:
    summary = report.summary
    print("\nConversation Quality & Output Safety Evaluation\n")
    print(
        f"Runs: {summary.case_runs} (완료 {summary.completed_runs}, 차단 {summary.blocked_runs}, "
        f"judge 오류 {summary.judge_error_runs}, 실행 오류 {summary.execution_error_runs})"
    )
    print(f"전체 pass: {summary.passed_runs} ({summary.pass_rate}%)")
    for category, category_summary in summary.by_category.items():
        print(
            f"- {category}: {category_summary.passed_runs}/{category_summary.case_runs} "
            f"({category_summary.pass_rate}%) 차단 {category_summary.blocked_runs}"
        )
    failures = [r for r in report.cases if r.passed is False]
    if failures:
        print("\n실패 실행:")
        for result in failures:
            print(f"- {result.case_id}#{result.run_number}: {', '.join(result.fail_reasons)}")
            if result.answer:
                print(f"  응답: {result.answer[:110]}")


async def _run(args: argparse.Namespace) -> int:
    cases, errors = load_conversation_cases(args.dataset)
    errors += validate_conversation_cases(cases, args.dataset)
    if errors:
        raise ValueError("conversation 데이터셋 검증 실패:\n" + "\n".join(f"- {e}" for e in errors))
    if args.case_id is not None:
        cases = [case for case in cases if case.id == args.case_id]
        if not cases:
            raise ValueError(f"case not found: {args.case_id}")
    if args.limit is not None:
        cases = cases[: args.limit]
    model = _real_evaluation_model()
    judge = ConversationJudge(model=args.judge_model)
    print(
        f"This run calls the real CLOVA API ({len(cases)}건 × repeat {args.repeat} × agent+judge) "
        "and may incur cost. Production DB and user data are not used."
    )
    started_at = datetime.now(UTC)
    results = await run_conversation_cases(cases, model, judge, repeat=args.repeat)
    report = build_conversation_report(results, started_at, args.repeat, judge.model)
    output = args.output or Path(__file__).parent / "reports" / f"{report.run_id}-conversation-eval.json"
    review = args.review_output or Path(__file__).parent / "reports" / f"{report.run_id}-conversation-review.md"
    write_conversation_report(report, output)
    write_review_markdown(report, review)
    print_conversation_summary(report)
    print(f"\nReport: {output}\n사람 검수: {review}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run conversation quality & output safety evaluation")
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument("--case-id")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--judge-model", default=None, help="judge 모델 override (기본: settings.clova_model)")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--review-output", type=Path)
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    if args.repeat < 1:
        parser.error("--repeat must be at least 1")
    try:
        return asyncio.run(_run(args))
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"대화 품질 평가를 시작할 수 없습니다: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
