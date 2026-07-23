"""프로덕션 AgentFactory 조립 경로로 평가 케이스를 실행한다.

데이터 액세스(query service)만 empty fake로 치환해 tool 선택·가드레일만 측정한다.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID, uuid5

from app.application.service.agent_execution_observability import (
    AgentExecutionRecord,
    AgentTraceDetail,
)
from app.application.service.diary_chat_prompt import DiaryConversationContext
from app.application.usecase.personal_assistant_agent import PersonalAssistantMode
from app.application.usecase.personal_assistant_agent_factory import PersonalAssistantAgentFactory
from app.infrastructure.config.dependencies import (
    get_model_retry_policy,
    get_tool_calling_chat_model,
)
from app.infrastructure.config.settings import settings
from evals.cases import messages_for_case
from evals.judge import evaluate_record
from evals.results import EvaluationCaseResult
from evals.schemas import PersonalAssistantEvalCase

EVAL_DEVICE_ID = "personal-assistant-eval-device"
EVAL_SESSION_NAMESPACE = UUID("72a8b1ba-9f7b-4a13-9d32-c6d7ee1080fd")


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


async def run_cases(cases: Sequence[tuple[str, PersonalAssistantEvalCase]], model=None, fail_fast: bool = False) -> list[EvaluationCaseResult]:
    return await run_repeated_cases(cases, model=model, fail_fast=fail_fast)


async def run_repeated_cases(
    cases: Sequence[tuple[str, PersonalAssistantEvalCase]],
    model=None,
    fail_fast: bool = False,
    repeat: int = 1,
) -> list[EvaluationCaseResult]:
    model = model or _real_evaluation_model()
    recorder = EvaluationRecorder()
    factory = PersonalAssistantAgentFactory(
        model,
        _EmptyDiaryQuery(),
        _EmptyHealthQuery(),
        execution_recorder=recorder,
        trace_detail=AgentTraceDetail.FULL,
    )
    results: list[EvaluationCaseResult] = []
    for dataset_name, case in cases:
        for run_number in range(1, repeat + 1):
            recorder.reset()
            error: Exception | None = None
            try:
                agent = factory.create(device_id=EVAL_DEVICE_ID, session_id=uuid5(EVAL_SESSION_NAMESPACE, f"{case.id}:{run_number}"), mode=case.mode)
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
            results.append(evaluate_record(case, dataset_name, record, error, run_number))
            if error and fail_fast:
                return results
    return results


def _real_evaluation_model():
    if settings.clova_mock_mode or not settings.clova_api_key.strip():
        raise RuntimeError("Real CLOVA credentials are required. Set CLOVA_MOCK_MODE=false and CLOVA_API_KEY before running evaluation.")
    return get_tool_calling_chat_model(
        x_clova_api_key=None,
        retry_policy=get_model_retry_policy(),
    )
