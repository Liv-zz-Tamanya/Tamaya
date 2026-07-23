"""리포트 조립·저장과 실행 환경 메타데이터(모델 설정, prompt 해시, git)."""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid5

from langchain_core.tools import BaseTool

from app.application.service.coaching_prompt import build_coaching_system_prompt
from app.application.service.diary_chat_prompt import build_diary_chat_system_prompt
from app.application.service.health_chat_prompt import build_health_chat_system_prompt
from app.application.tool.read_tools import (
    AgentToolExecutionContext,
    create_read_tools,
    create_search_health_records_tool,
)
from app.application.usecase.personal_assistant_agent import PersonalAssistantMode
from app.infrastructure.config.settings import settings
from evals.metrics import (
    case_stability,
    compare_baseline,
    stability_summary,
    summarize,
    tool_confusion_matrix,
)
from evals.results import (
    CaseStabilityResult,
    EvaluationCaseResult,
    EvaluationModelConfig,
    EvaluationRunReport,
    PromptMetadata,
)
from evals.runner import (
    EVAL_DEVICE_ID,
    EVAL_SESSION_NAMESPACE,
    _EmptyDiaryQuery,
    _EmptyHealthQuery,
)


def _model_config_metadata(model: object | None) -> EvaluationModelConfig:
    delegate = _unwrap_model(model)
    model_name = getattr(delegate, "_model", None)
    temperature = getattr(delegate, "_temperature", None)
    max_tokens = getattr(delegate, "_max_tokens", None)
    timeout = getattr(delegate, "_timeout", None)
    provider = "mock" if delegate.__class__.__name__ == "MockToolCallingChatModel" else "clova"
    return EvaluationModelConfig(
        provider=provider,
        model=model_name if isinstance(model_name, str) else settings.clova_model,
        temperature=temperature if isinstance(temperature, int | float) else settings.clova_agent_temperature,
        top_p=None,
        seed=None,
        parallel_tool_calls=None,
        max_tokens=max_tokens if isinstance(max_tokens, int) else settings.clova_agent_max_tokens,
        timeout_seconds=timeout if isinstance(timeout, int | float) else settings.clova_agent_timeout_seconds,
    )


def _unwrap_model(model: object | None) -> object:
    current = model
    seen: set[int] = set()
    while current is not None and id(current) not in seen and hasattr(current, "_delegate"):
        seen.add(id(current))
        current = current._delegate
    return current if current is not None else object()


def _prompt_metadata(modes: Sequence[PersonalAssistantMode]) -> PromptMetadata:
    return PromptMetadata(
        prompt_hash=_hash_json(_prompt_payload(modes)),
        tool_schema_hash=_hash_json(_tool_schema_payload(modes)),
        **_git_metadata(),
    )


def _modes_for_datasets(datasets: Sequence[str]) -> list[PersonalAssistantMode]:
    modes: list[PersonalAssistantMode] = []
    for dataset in datasets:
        try:
            mode = PersonalAssistantMode(dataset)
        except ValueError:
            continue
        if mode not in modes:
            modes.append(mode)
    return modes


def _prompt_payload(modes: Sequence[PersonalAssistantMode]) -> dict[str, Any]:
    prompts: dict[str, str] = {}
    for mode in modes:
        if mode == PersonalAssistantMode.DIARY:
            prompts[mode.value] = build_diary_chat_system_prompt(
                max_turns=5,
                current_user_turn=1,
                suggest_finalize=False,
                tool_calling_enabled=True,
            )
        elif mode == PersonalAssistantMode.HEALTH:
            prompts[mode.value] = build_health_chat_system_prompt(tool_calling_enabled=True)
        elif mode == PersonalAssistantMode.COACHING:
            prompts[mode.value] = build_coaching_system_prompt(persona=None)
    return {
        "system_prompts": prompts,
        "tool_schemas": _tool_schema_payload(modes),
    }


def _tool_schema_payload(modes: Sequence[PersonalAssistantMode]) -> list[dict[str, Any]]:
    context = AgentToolExecutionContext(
        device_id=EVAL_DEVICE_ID,
        session_id=uuid5(EVAL_SESSION_NAMESPACE, "prompt-metadata"),
    )
    tools: list[BaseTool] = []
    for mode in modes:
        if mode == PersonalAssistantMode.DIARY:
            tools.extend(create_read_tools(_EmptyDiaryQuery(), _EmptyHealthQuery(), context))
        elif mode == PersonalAssistantMode.HEALTH:
            tools.append(create_search_health_records_tool(_EmptyHealthQuery(), context))
    return [_tool_schema(tool) for tool in sorted(tools, key=lambda item: item.name)]


def _tool_schema(tool: BaseTool) -> dict[str, Any]:
    args_schema = tool.args_schema.model_json_schema() if tool.args_schema is not None else {}
    return {
        "name": tool.name,
        "description": tool.description,
        "parameters": args_schema,
    }


def _hash_json(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _git_metadata() -> dict[str, str | bool | None]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "diff", "--quiet"],
            check=False,
            capture_output=True,
            text=True,
        ).returncode != 0
    except (OSError, subprocess.SubprocessError):
        return {"git_commit": None, "git_dirty": None}
    return {"git_commit": commit or None, "git_dirty": dirty}


def load_baseline(path: Path) -> list[CaseStabilityResult]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return [CaseStabilityResult.model_validate(item) for item in raw["case_stability"]]
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"incompatible baseline report {path}: expected case_stability: {exc}") from exc


def build_report(
    results: list[EvaluationCaseResult],
    datasets: list[str],
    started_at: datetime,
    repeat: int = 1,
    baseline: Sequence[CaseStabilityResult] | None = None,
    model: object | None = None,
) -> EvaluationRunReport:
    stability = case_stability(results)
    return EvaluationRunReport(run_id=started_at.strftime("%Y%m%dT%H%M%SZ"), started_at=started_at,
        completed_at=datetime.now(UTC), selected_datasets=datasets, summary=summarize(results),
        by_mode={key: summarize([r for r in results if r.mode.value == key]) for key in sorted({r.mode.value for r in results})},
        by_category={key: summarize([r for r in results if r.category == key]) for key in sorted({r.category for r in results})}, cases=results,
        model_settings=_model_config_metadata(model),
        prompt_metadata=_prompt_metadata(_modes_for_datasets(datasets)),
        stability_summary=stability_summary(stability, repeat), case_stability=stability,
        tool_confusion_matrix=tool_confusion_matrix(results), baseline_comparison=compare_baseline(stability, baseline) if baseline is not None else None)


def write_report(report: EvaluationRunReport, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = report.model_dump(mode="json")
    payload["model_config"] = payload.pop("model_settings")
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def print_summary(report: EvaluationRunReport) -> None:
    summary = report.summary
    stability = report.stability_summary
    print("\nPersonal Assistant Evaluation\n")
    print(f"Selected cases: {stability.selected_case_count}\nRepeat: {stability.repeat_count}\nTotal executions: {summary.total_cases}")
    print(f"Completed: {summary.completed_cases}\nExecution errors: {summary.execution_error_cases}\n")
    print(f"Tool checks: {summary.tool_check_passed_cases}/{summary.completed_cases} ({summary.tool_check_rate}%)")
    print(f"Guardrail checks: {summary.guardrail_check_passed_cases}/{summary.completed_cases} ({summary.guardrail_check_rate}%)")
    print(f"Combined: {summary.combined_passed_cases}/{summary.completed_cases} ({summary.combined_rate}%)")
    print(f"Forbidden tool violations: {summary.forbidden_tool_violation_cases}")
    if summary.decision_check_cases:
        print(f"Decision checks: {summary.decision_check_passed_cases}/{summary.decision_check_cases} ({summary.decision_check_rate}%)")
        print(f"NO_TOOL accuracy: {summary.no_tool_accuracy}% ({summary.no_tool_cases} cases)")
        print(f"TOOL_CALL accuracy: {summary.tool_call_accuracy}% ({summary.tool_call_cases} cases)")
        print(f"Unnecessary tool calls: {summary.unnecessary_tool_call_cases}")
    if summary.decision_skipped_cases:
        print(f"Decision skipped: {summary.decision_skipped_cases}")
        print(f"- input guardrail blocked: {summary.decision_skipped_input_guardrail_blocked_cases}")
        print(f"- execution error: {summary.decision_skipped_execution_error_cases}")
        print(f"- agent not invoked: {summary.decision_skipped_agent_not_invoked_cases}")
    print(f"Stable pass cases: {stability.stable_passed_cases}\nFlaky cases: {stability.flaky_cases}\nStable fail cases: {stability.stable_failed_cases}")
    if stability.flaky_cases:
        print("\nFlaky cases:")
        for item in report.case_stability:
            if item.status == "flaky":
                print(f"- {item.case_id}: {item.passed_runs}/{item.total_runs} passed, tools={item.actual_tool_selected_runs}")
    if report.baseline_comparison:
        comparison = report.baseline_comparison
        print(f"\nBaseline comparison:\nImproved: {len(comparison.improved_cases)}\nRegressed: {len(comparison.regressed_cases)}\nAdded: {len(comparison.added_cases)}\nRemoved: {len(comparison.removed_cases)}")
    failures = [r for r in report.cases if not r.combined_passed]
    if failures:
        print("\nFailed cases:")
        for result in failures:
            detail = result.execution_error or (f"missing {', '.join(result.missing_expected_tools)}" if result.missing_expected_tools else f"forbidden {', '.join(result.called_forbidden_tools)}" if result.called_forbidden_tools else f"expected {result.expected_guardrail.value}, actual {result.actual_guardrail}")
            print(f"- {result.case_id}: {detail}{_failure_args_summary(result)}")


def _failure_args_summary(result: EvaluationCaseResult) -> str:
    calls = [call for call in result.tool_calls if call.arguments]
    if not calls:
        return ""
    payload = [
        {"name": call.name, "arguments": call.arguments}
        for call in calls
    ]
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if len(text) > 240:
        text = text[:237] + "..."
    return f"\n  args={text}"
