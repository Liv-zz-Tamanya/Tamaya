from uuid import UUID

from app.application.service.diary_memory_query_service import DiaryMemoryQueryService
from app.application.service.health_record_query_service import HealthRecordQueryService
from app.application.service.tool_calling_chat_model import ToolCallingChatModel
from app.application.tool.read_tools import AgentToolExecutionContext, create_read_tools
from app.application.usecase.personal_assistant_agent import PersonalAssistantAgent


class PersonalAssistantAgentFactory:
    def __init__(
        self,
        model: ToolCallingChatModel,
        diary_query: DiaryMemoryQueryService,
        health_query: HealthRecordQueryService,
    ) -> None:
        self._model = model
        self._diary_query = diary_query
        self._health_query = health_query

    def create(
        self,
        *,
        device_id: str,
        session_id: UUID,
    ) -> PersonalAssistantAgent:
        tools = create_read_tools(
            diary_query_service=self._diary_query,
            health_query_service=self._health_query,
            execution_context=AgentToolExecutionContext(
                device_id=device_id,
                session_id=session_id,
            ),
        )
        return PersonalAssistantAgent(self._model, tools)
