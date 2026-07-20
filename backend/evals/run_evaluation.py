"""PersonalAssistantAgent의 도구 선택 및 가드레일 오프라인 평가 실행기."""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid5

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from pydantic import BaseModel, Field

from app.application.service.agent_execution_observability import (
    AgentExecutionRecord,
    AgentTerminationReason,
)
from app.application.service.diary_chat_prompt import DiaryConversationContext
from app.application.usecase.personal_assistant_agent import PersonalAssistantMode
from app.application.usecase.personal_assistant_agent_factory import PersonalAssistantAgentFactory
from app.infrastructure.config.dependencies import (
    get_model_retry_policy,
    get_tool_calling_chat_model,
)
from app.infrastructure.config.settings import settings
from evals.schemas import ExpectedGuardrail, PersonalAssistantEvalCase
from evals.validate_dataset import DATASET_FILENAMES

EVAL_DEVICE_ID = "personal-assistant-eval-device"
EVAL_SESSION_NAMESPACE = UUID("72a8b1ba-9f7b-4a13-9d32-c6d7ee1080fd")
EXECUTION_ERROR_REASONS = frozenset(
    {
        AgentTerminationReason.TIMEOUT,
        AgentTerminationReason.PROVIDER_ERROR,
        AgentTerminationReason.TOOL_ERROR,
        AgentTerminationReason.CANCELLED,
        AgentTerminationReason.UNEXPECTED_ERROR,
    }
)


class EvaluationCaseResult(BaseModel):
    case_id: str
    dataset_name: str
    mode: PersonalAssistantMode
    category: str
    input: str
    expected_tools: list[str]
    forbidden_tools: list[str]
    actual_tools: list[str] = Field(default_factory=list)
    missing_expected_tools: list[str] = Field(default_factory=list)
    called_forbidden_tools: list[str] = Field(default_factory=list)
    expected_guardrail: ExpectedGuardrail
    actual_guardrail: str | None = None
    guardrail_verdict: str | None = None
    termination_reason: str | None = None
    tool_check_passed: bool = False
    guardrail_check_passed: bool = False
    combined_passed: bool = False
    execution_error: str | None = None
    trace_id: str | None = None
    llm_calls: int | None = None
    tool_rounds: int | None = None
    execution_duration_ms: int | None = None
    model_duration_ms: int | None = None
    tool_duration_ms: int | None = None
    retry_attempts: int | None = None
    provider_error_category: str | None = None
    timeout_stage: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    expected_document_ids: list[str]
    document_evaluation_status: str = "not_evaluated"


class EvaluationSummary(BaseModel):
    total_cases: int
    completed_cases: int
    execution_error_cases: int
    tool_check_passed_cases: int
    tool_check_rate: float
    guardrail_check_passed_cases: int
    guardrail_check_rate: float
    combined_passed_cases: int
    combined_rate: float
    forbidden_tool_violation_cases: int


class EvaluationRunReport(BaseModel):
    run_id: str
    started_at: datetime
    completed_at: datetime
    selected_datasets: list[str]
    summary: EvaluationSummary
    by_mode: dict[str, EvaluationSummary]
    by_category: dict[str, EvaluationSummary]
    cases: list[EvaluationCaseResult]


class EvaluationRecorder:
    """한 Agent 실행의 terminal record를 명시적으로 분리해 보관한다."""

    def __init__(self) -> None:
        self._records: list[AgentExecutionRecord] = []

    def record(self, record: AgentExecutionRecord) -> None:
        self._records.append(record)

    def reset(self) -> None:
        self._records.clear()

    def only_record(self) -> AgentExecutionRecord:
        if len(self._records) != 1:
            raise RuntimeError(f"evaluation recorder expected exactly one record, got {len(self._records)}")
        return self._records[0]


class _EmptyDiaryQuery:
    async def search_similar(
        self, device_id: str, query: str, exclude_session_id: UUID | None = None, limit: int = 5
    ) -> list[object]:
        return []


class _EmptyHealthQuery:
    async def search_similar(self, device_id: str, query: str, limit: int = 5) -> list[object]:
        return []


def messages_for_case(case: PersonalAssistantEvalCase) -> list[BaseMessage]:
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


def load_cases(dataset_dir: Path, datasets: Sequence[str] | None = None) -> list[tuple[str, PersonalAssistantEvalCase]]:
    selected = set(datasets or dataset_names())
    loaded: list[tuple[str, PersonalAssistantEvalCase]] = []
    for filename in DATASET_FILENAMES:
        name = filename.removesuffix("_cases.jsonl")
        if name not in selected:
            continue
        path = dataset_dir / filename
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                raise ValueError(f"{path}:{line_number}: empty JSONL row")
            loaded.append((name, PersonalAssistantEvalCase.model_validate_json(line)))
    return loaded


def dataset_names() -> list[str]:
    return [filename.removesuffix("_cases.jsonl") for filename in DATASET_FILENAMES]


def select_cases(
    cases: Iterable[tuple[str, PersonalAssistantEvalCase]], case_id: str | None, limit: int | None
) -> list[tuple[str, PersonalAssistantEvalCase]]:
    selected = [(dataset, case) for dataset, case in cases if case_id is None or case.id == case_id]
    if case_id is not None and not selected:
        raise ValueError(f"case not found: {case_id}")
    return selected[:limit] if limit is not None else selected


def evaluate_record(
    case: PersonalAssistantEvalCase, dataset_name: str, record: AgentExecutionRecord | None, error: Exception | None
) -> EvaluationCaseResult:
    actual_tools = list(record.tool_names) if record else []
    actual_set = set(actual_tools)
    missing = sorted(set(case.expected_tools) - actual_set)
    forbidden = sorted(set(case.forbidden_tools) & actual_set)
    reason = record.termination_reason if record else None
    execution_error = str(error) if error else None
    if reason in EXECUTION_ERROR_REASONS:
        execution_error = execution_error or f"agent terminated: {reason.value}"
    actual_guardrail = (
        "BLOCK" if reason in {AgentTerminationReason.INPUT_GUARDRAIL_BLOCKED, AgentTerminationReason.OUTPUT_GUARDRAIL_BLOCKED}
        else "PASS" if record and execution_error is None else None
    )
    guardrail_passed = actual_guardrail == case.expected_guardrail.value and execution_error is None
    return EvaluationCaseResult(
        case_id=case.id, dataset_name=dataset_name, mode=case.mode, category=case.category, input=case.input,
        expected_tools=case.expected_tools, forbidden_tools=case.forbidden_tools, actual_tools=actual_tools,
        missing_expected_tools=missing, called_forbidden_tools=forbidden, expected_guardrail=case.expected_guardrail,
        actual_guardrail=actual_guardrail, guardrail_verdict=record.guardrail_verdict if record else None,
        termination_reason=reason.value if reason else None, tool_check_passed=not missing and not forbidden,
        guardrail_check_passed=guardrail_passed, combined_passed=not missing and not forbidden and guardrail_passed,
        execution_error=execution_error, trace_id=record.trace_id if record else None, llm_calls=record.llm_calls if record else None,
        tool_rounds=record.tool_rounds if record else None, execution_duration_ms=record.execution_duration_ms if record else None,
        model_duration_ms=record.model_duration_ms if record else None, tool_duration_ms=record.tool_duration_ms if record else None,
        retry_attempts=record.retry_attempts if record else None, provider_error_category=record.provider_error_category if record else None,
        timeout_stage=record.timeout_stage if record else None, input_tokens=record.input_tokens if record else None,
        output_tokens=record.output_tokens if record else None, total_tokens=record.total_tokens if record else None,
        expected_document_ids=case.expected_document_ids,
    )


def summarize(results: Sequence[EvaluationCaseResult]) -> EvaluationSummary:
    total = len(results)
    errors = sum(result.execution_error is not None for result in results)
    completed = total - errors
    tool = sum(result.tool_check_passed for result in results if result.execution_error is None)
    guardrail = sum(result.guardrail_check_passed for result in results if result.execution_error is None)
    combined = sum(result.combined_passed for result in results)
    return EvaluationSummary(total_cases=total, completed_cases=completed, execution_error_cases=errors,
        tool_check_passed_cases=tool, tool_check_rate=_rate(tool, completed), guardrail_check_passed_cases=guardrail,
        guardrail_check_rate=_rate(guardrail, completed), combined_passed_cases=combined, combined_rate=_rate(combined, completed),
        forbidden_tool_violation_cases=sum(bool(result.called_forbidden_tools) for result in results))


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator * 100, 1) if denominator else 0.0


async def run_cases(cases: Sequence[tuple[str, PersonalAssistantEvalCase]], model=None, fail_fast: bool = False) -> list[EvaluationCaseResult]:
    model = model or _real_evaluation_model()
    recorder = EvaluationRecorder()
    factory = PersonalAssistantAgentFactory(model, _EmptyDiaryQuery(), _EmptyHealthQuery(), execution_recorder=recorder)
    results: list[EvaluationCaseResult] = []
    for dataset_name, case in cases:
        recorder.reset()
        error: Exception | None = None
        try:
            agent = factory.create(device_id=EVAL_DEVICE_ID, session_id=uuid5(EVAL_SESSION_NAMESPACE, case.id), mode=case.mode)
            await agent.run(messages=messages_for_case(case), mode=case.mode,
                diary_context=DiaryConversationContext(max_turns=5, current_user_turn=1, suggest_finalize=False) if case.mode == PersonalAssistantMode.DIARY else None,
                coaching_context={"persona": None} if case.mode == PersonalAssistantMode.COACHING else None)
        except Exception as exc:
            error = exc
        try:
            record = recorder.only_record()
        except RuntimeError as recorder_error:
            record = None
            error = error or recorder_error
        result = evaluate_record(case, dataset_name, record, error)
        results.append(result)
        if error and fail_fast:
            break
    return results


def _real_evaluation_model():
    if settings.clova_mock_mode or not settings.clova_api_key.strip():
        raise RuntimeError("Real CLOVA credentials are required. Set CLOVA_MOCK_MODE=false and CLOVA_API_KEY before running evaluation.")
    return get_tool_calling_chat_model(
        x_clova_api_key=None,
        retry_policy=get_model_retry_policy(),
    )


def build_report(results: list[EvaluationCaseResult], datasets: list[str], started_at: datetime) -> EvaluationRunReport:
    return EvaluationRunReport(run_id=started_at.strftime("%Y%m%dT%H%M%SZ"), started_at=started_at,
        completed_at=datetime.now(UTC), selected_datasets=datasets, summary=summarize(results),
        by_mode={key: summarize([r for r in results if r.mode.value == key]) for key in sorted({r.mode.value for r in results})},
        by_category={key: summarize([r for r in results if r.category == key]) for key in sorted({r.category for r in results})}, cases=results)


def write_report(report: EvaluationRunReport, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")


def print_summary(report: EvaluationRunReport) -> None:
    summary = report.summary
    print("\nPersonal Assistant Evaluation\n")
    print(f"Total: {summary.total_cases}\nCompleted: {summary.completed_cases}\nErrors: {summary.execution_error_cases}\n")
    print(f"Tool checks: {summary.tool_check_passed_cases}/{summary.completed_cases} ({summary.tool_check_rate}%)")
    print(f"Guardrail checks: {summary.guardrail_check_passed_cases}/{summary.completed_cases} ({summary.guardrail_check_rate}%)")
    print(f"Combined: {summary.combined_passed_cases}/{summary.completed_cases} ({summary.combined_rate}%)")
    print(f"Forbidden tool violations: {summary.forbidden_tool_violation_cases}")
    failures = [r for r in report.cases if not r.combined_passed]
    if failures:
        print("\nFailed cases:")
        for result in failures:
            detail = result.execution_error or (f"missing {', '.join(result.missing_expected_tools)}" if result.missing_expected_tools else f"forbidden {', '.join(result.called_forbidden_tools)}" if result.called_forbidden_tools else f"expected {result.expected_guardrail.value}, actual {result.actual_guardrail}")
            print(f"- {result.case_id}: {detail}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run PersonalAssistantAgent evaluation")
    parser.add_argument("--dataset", choices=[*dataset_names(), "all"], default="all")
    parser.add_argument("--case-id")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--fail-on-mismatch", action="store_true")
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    datasets = dataset_names() if args.dataset == "all" else [args.dataset]
    try:
        cases = select_cases(load_cases(Path(__file__).parent / "datasets", datasets), args.case_id, args.limit)
        print("This run calls the real LLM API and may incur cost. Production DB and user data are not used.")
        started_at = datetime.now(UTC)
        report = build_report(asyncio.run(run_cases(cases, fail_fast=args.fail_fast)), datasets, started_at)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Evaluation could not start: {exc}", file=sys.stderr)
        return 2
    output = args.output or Path(__file__).parent / "reports" / f"{report.run_id}-personal-assistant-eval.json"
    write_report(report, output)
    print_summary(report)
    print(f"\nReport: {output}")
    return 1 if args.fail_on_mismatch and any(not r.combined_passed for r in report.cases) else 0


if __name__ == "__main__":
    raise SystemExit(main())
