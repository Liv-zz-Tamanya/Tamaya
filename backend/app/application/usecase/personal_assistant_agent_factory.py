from uuid import UUID

from app.application.service.agent_execution_observability import (
    AgentExecutionRecorder,
    NullAgentExecutionRecorder,
)
from app.application.service.diary_memory_query_service import DiaryMemoryQueryService
from app.application.service.health_record_query_service import HealthRecordQueryService
from app.application.service.personal_assistant_timeout import (
    DEFAULT_PERSONAL_ASSISTANT_TIMEOUT_POLICY,
    PersonalAssistantTimeoutPolicy,
)
from app.application.service.tool_calling_chat_model import ToolCallingChatModel
from app.application.tool.read_tools import (
    AgentToolExecutionContext,
    create_read_tools,
    create_search_health_records_tool,
)
from app.application.usecase.personal_assistant_agent import (
    PersonalAssistantAgent,
    PersonalAssistantMode,
)


class PersonalAssistantAgentFactory:
    def __init__(
        self,
        model: ToolCallingChatModel,
        diary_query: DiaryMemoryQueryService,
        health_query: HealthRecordQueryService,
        timeout_policy: PersonalAssistantTimeoutPolicy = DEFAULT_PERSONAL_ASSISTANT_TIMEOUT_POLICY,
        execution_recorder: AgentExecutionRecorder = NullAgentExecutionRecorder(),
    ) -> None:
        self._model = model
        self._diary_query = diary_query
        self._health_query = health_query
        self._timeout_policy = timeout_policy
        self._execution_recorder = execution_recorder

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
        else:
            raise ValueError(f"unsupported personal assistant mode: {mode}")
        return PersonalAssistantAgent(
            self._model,
            tools,
            timeout_policy=self._timeout_policy,
            execution_recorder=self._execution_recorder,
        )
