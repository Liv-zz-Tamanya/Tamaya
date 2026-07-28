from datetime import date
from uuid import UUID

from app.application.service.agent_execution_observability import (
    AgentExecutionRecorder,
    AgentTraceDetail,
    NullAgentExecutionRecorder,
)
from app.application.service.diary_memory_query_service import DiaryMemoryQueryService
from app.application.service.health_record_query_service import HealthRecordQueryService
from app.application.service.insight_generation_prompt import InsightGenerationContext
from app.application.service.personal_assistant_timeout import (
    DEFAULT_PERSONAL_ASSISTANT_TIMEOUT_POLICY,
    PersonalAssistantTimeoutPolicy,
)
from app.application.service.tool_calling_chat_model import ToolCallingChatModel
from app.application.tool.insight_tools import (
    create_get_day_facts_tool,
    create_get_medical_visit_facts_tool,
)
from app.application.tool.read_tools import (
    AgentToolExecutionContext,
    create_read_tools,
    create_search_diary_memories_tool,
    create_search_health_records_tool,
)
from app.application.usecase.personal_assistant_agent import (
    PersonalAssistantAgent,
    PersonalAssistantMode,
)
from app.domain.model.medical_visit import MedicalVisit
from app.domain.service.insight_models import DailyFact


class PersonalAssistantAgentFactory:
    def __init__(
        self,
        model: ToolCallingChatModel,
        diary_query: DiaryMemoryQueryService,
        health_query: HealthRecordQueryService,
        timeout_policy: PersonalAssistantTimeoutPolicy = DEFAULT_PERSONAL_ASSISTANT_TIMEOUT_POLICY,
        execution_recorder: AgentExecutionRecorder = NullAgentExecutionRecorder(),
        trace_detail: AgentTraceDetail = AgentTraceDetail.BASIC,
    ) -> None:
        self._model = model
        self._diary_query = diary_query
        self._health_query = health_query
        self._timeout_policy = timeout_policy
        self._execution_recorder = execution_recorder
        self._trace_detail = trace_detail

    def create(
        self,
        *,
        device_id: str,
        session_id: UUID,
        mode: PersonalAssistantMode,
    ) -> PersonalAssistantAgent:
        execution_context = AgentToolExecutionContext(
            device_id=device_id,
            session_id=session_id,
        )
        if mode == PersonalAssistantMode.DIARY:
            tools = create_read_tools(
                diary_query_service=self._diary_query,
                health_query_service=self._health_query,
                execution_context=execution_context,
            )
        elif mode == PersonalAssistantMode.HEALTH:
            tools = [
                create_search_health_records_tool(
                    query_service=self._health_query,
                    execution_context=execution_context,
                )
            ]
        elif mode == PersonalAssistantMode.COACHING:
            tools = []
        elif mode == PersonalAssistantMode.INSIGHT:
            raise ValueError("insight mode requires create_for_insight()")
        else:
            raise ValueError(f"unsupported personal assistant mode: {mode}")
        return self._build_agent(tools)

    def create_for_insight(
        self,
        *,
        device_id: str,
        run_id: UUID,
        context: InsightGenerationContext,
        day_facts_by_date: dict[date, DailyFact],
        medical_visits: list[MedicalVisit],
    ) -> PersonalAssistantAgent:
        """INSIGHT 전용 진입점 — 채팅 세션이 없으므로 session_id 대신 run_id를 쓴다.

        가짜 세션을 만들지 않는다. tool은 근거 탐색 3종으로 제한되고,
        기간 raw 목록 tool은 존재하지 않는다(2층 원칙의 코드 경계).
        """
        execution_context = AgentToolExecutionContext(
            device_id=device_id,
            session_id=None,  # 세션 없음 — search_diary_memories의 세션 제외도 없음
            run_id=run_id,
        )
        tools = [
            create_get_day_facts_tool(
                facts_by_date=day_facts_by_date,
                allowed_dates=frozenset(context.allowed_evidence_dates),
                period_start=context.start_date,
                period_end=context.end_date,
            ),
            create_search_diary_memories_tool(self._diary_query, execution_context),
            create_get_medical_visit_facts_tool(
                visits=medical_visits,
                period_type=context.period_type,
                period_start=context.start_date,
                period_end=context.end_date,
            ),
        ]
        return self._build_agent(tools)

    def _build_agent(self, tools) -> PersonalAssistantAgent:
        return PersonalAssistantAgent(
            self._model,
            tools,
            timeout_policy=self._timeout_policy,
            execution_recorder=self._execution_recorder,
            trace_detail=self._trace_detail,
        )
