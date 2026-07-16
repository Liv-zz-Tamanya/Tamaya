from collections.abc import Sequence

from fastapi import Depends, Header
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.service.ai_chat_service import AiChatService
from app.application.service.clova_connection_tester import ClovaConnectionTester
from app.application.service.diary_memory_query_service import DiaryMemoryQueryService
from app.application.service.embedding_service import EmbeddingService
from app.application.service.health_ai_service import HealthAiService
from app.application.service.health_record_query_service import HealthRecordQueryService
from app.application.service.personal_assistant_timeout import PersonalAssistantTimeoutPolicy
from app.application.service.signal_extraction_service import SignalExtractionService
from app.application.service.tool_calling_chat_model import ToolCallingChatModel
from app.application.usecase.extract_chunks import ExtractChunksUseCase
from app.application.usecase.extract_signals import ExtractSignalsUseCase
from app.application.usecase.get_monthly_insight import GetMonthlyInsightUseCase
from app.application.usecase.get_weekly_insight import GetWeeklyInsightUseCase
from app.application.usecase.personal_assistant_agent_factory import PersonalAssistantAgentFactory
from app.domain.repository.chat_session_repository import ChatSessionRepository
from app.domain.repository.clova_setting_repository import ClovaSettingRepository
from app.domain.repository.diary_repository import DiaryRepository
from app.domain.repository.event_chunk_repository import EventChunkRepository
from app.domain.repository.health_chunk_repository import HealthChunkRepository
from app.domain.repository.health_record_repository import HealthRecordRepository
from app.domain.repository.health_session_repository import HealthSessionRepository
from app.domain.repository.qualitative_signal_repository import QualitativeSignalRepository
from app.domain.service.clova_credential import resolve_clova_credential
from app.infrastructure.config.database import get_db
from app.infrastructure.config.settings import settings
from app.infrastructure.external.clova_client import ClovaClient, HealthClovaClient
from app.infrastructure.external.clova_connection_tester_impl import ClovaConnectionTesterImpl
from app.infrastructure.external.clova_tool_calling import ClovaToolCallingChatModel
from app.infrastructure.external.embedding_service_impl import SentenceTransformerEmbeddingService
from app.infrastructure.external.signal_extraction_clova import SignalExtractionClovaClient
from app.infrastructure.persistence.chat_session_repository_impl import ChatSessionRepositoryImpl
from app.infrastructure.persistence.clova_setting_repository_impl import (
    ClovaSettingRepositoryImpl,
)
from app.infrastructure.persistence.diary_repository_impl import DiaryRepositoryImpl
from app.infrastructure.persistence.event_chunk_repository_impl import EventChunkRepositoryImpl
from app.infrastructure.persistence.health_chunk_repository_impl import HealthChunkRepositoryImpl
from app.infrastructure.persistence.health_record_repository_impl import HealthRecordRepositoryImpl
from app.infrastructure.persistence.health_session_repository_impl import (
    HealthSessionRepositoryImpl,
)
from app.infrastructure.persistence.qualitative_signal_repository_impl import (
    QualitativeSignalRepositoryImpl,
)

_embedding_service: EmbeddingService | None = None
MOCK_TOOL_CALLING_CHAT_RESPONSE = "그랬구나. 오늘 하루 어땠어?"


class MockToolCallingChatModel(ToolCallingChatModel):
    async def ainvoke(
        self,
        messages: Sequence[BaseMessage],
        tools: Sequence[BaseTool],
    ) -> AIMessage:
        return AIMessage(content=MOCK_TOOL_CALLING_CHAT_RESPONSE)


def get_chat_session_repo(db: AsyncSession = Depends(get_db)) -> ChatSessionRepository:
    return ChatSessionRepositoryImpl(db)


def get_diary_repo(db: AsyncSession = Depends(get_db)) -> DiaryRepository:
    return DiaryRepositoryImpl(db)


def get_event_chunk_repo(db: AsyncSession = Depends(get_db)) -> EventChunkRepository:
    return EventChunkRepositoryImpl(db)


def get_ai_chat_service(
    x_clova_api_key: str | None = Header(default=None),
) -> AiChatService:
    # BYOK: 요청 헤더의 사용자 키를 우선순위(user>env>mock)로 해석한다.
    # 키는 마스킹 외 형태로 로깅하지 않으며 settings(env)는 변경하지 않는다.
    cred = resolve_clova_credential(
        user_key=x_clova_api_key,
        env_key=settings.clova_api_key,
        mock_mode=settings.clova_mock_mode,
    )
    return ClovaClient(api_key=cred.api_key, mock=cred.use_mock)


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = SentenceTransformerEmbeddingService()
    return _embedding_service


def get_extract_chunks_usecase(
    ai: AiChatService = Depends(get_ai_chat_service),
    embedding: EmbeddingService = Depends(get_embedding_service),
    event_chunk_repo: EventChunkRepository = Depends(get_event_chunk_repo),
) -> ExtractChunksUseCase:
    return ExtractChunksUseCase(ai, embedding, event_chunk_repo)


def get_diary_memory_query_service(
    embedding: EmbeddingService = Depends(get_embedding_service),
    event_chunk_repo: EventChunkRepository = Depends(get_event_chunk_repo),
) -> DiaryMemoryQueryService:
    return DiaryMemoryQueryService(embedding, event_chunk_repo)


def get_tool_calling_chat_model(
    x_clova_api_key: str | None = Header(default=None),
) -> ToolCallingChatModel:
    cred = resolve_clova_credential(
        user_key=x_clova_api_key,
        env_key=settings.clova_api_key,
        mock_mode=settings.clova_mock_mode,
    )
    if cred.use_mock:
        return MockToolCallingChatModel()
    return ClovaToolCallingChatModel(api_key=cred.api_key)


def get_coaching_tool_calling_chat_model(
    x_clova_api_key: str | None = Header(default=None),
) -> ToolCallingChatModel:
    cred = resolve_clova_credential(
        user_key=x_clova_api_key,
        env_key=settings.clova_api_key,
        mock_mode=settings.clova_mock_mode,
    )
    if cred.use_mock:
        return MockToolCallingChatModel()
    return ClovaToolCallingChatModel(
        api_key=cred.api_key,
        temperature=0.6,
        max_tokens=300,
    )


def get_signal_extraction_service() -> SignalExtractionService:
    return SignalExtractionClovaClient()


def get_qualitative_signal_repo(
    db: AsyncSession = Depends(get_db),
) -> QualitativeSignalRepository:
    return QualitativeSignalRepositoryImpl(db)


def get_extract_signals_usecase(
    service: SignalExtractionService = Depends(get_signal_extraction_service),
    repo: QualitativeSignalRepository = Depends(get_qualitative_signal_repo),
) -> ExtractSignalsUseCase:
    return ExtractSignalsUseCase(service, repo)


def get_weekly_insight_usecase(
    repo: QualitativeSignalRepository = Depends(get_qualitative_signal_repo),
) -> GetWeeklyInsightUseCase:
    return GetWeeklyInsightUseCase(repo)


def get_monthly_insight_usecase(
    repo: QualitativeSignalRepository = Depends(get_qualitative_signal_repo),
) -> GetMonthlyInsightUseCase:
    return GetMonthlyInsightUseCase(repo)


def get_clova_connection_tester() -> ClovaConnectionTester:
    return ClovaConnectionTesterImpl()


def get_clova_setting_repo(db: AsyncSession = Depends(get_db)) -> ClovaSettingRepository:
    return ClovaSettingRepositoryImpl(db)


def get_health_ai_service(
    x_clova_api_key: str | None = Header(default=None),
) -> HealthAiService:
    cred = resolve_clova_credential(
        user_key=x_clova_api_key,
        env_key=settings.clova_api_key,
        mock_mode=settings.clova_mock_mode,
    )
    return HealthClovaClient(api_key=cred.api_key, mock=cred.use_mock)


def get_health_record_repo(db: AsyncSession = Depends(get_db)) -> HealthRecordRepository:
    return HealthRecordRepositoryImpl(db)


def get_health_chunk_repo(db: AsyncSession = Depends(get_db)) -> HealthChunkRepository:
    return HealthChunkRepositoryImpl(db)


def get_health_record_query_service(
    embedding: EmbeddingService = Depends(get_embedding_service),
    health_chunk_repo: HealthChunkRepository = Depends(get_health_chunk_repo),
) -> HealthRecordQueryService:
    return HealthRecordQueryService(embedding, health_chunk_repo)


def get_personal_assistant_timeout_policy() -> PersonalAssistantTimeoutPolicy:
    return PersonalAssistantTimeoutPolicy(
        model_call_seconds=settings.personal_assistant_model_call_timeout_seconds,
        tool_round_seconds=settings.personal_assistant_tool_round_timeout_seconds,
        execution_seconds=settings.personal_assistant_execution_timeout_seconds,
    )


def get_personal_assistant_agent_factory(
    model: ToolCallingChatModel = Depends(get_tool_calling_chat_model),
    diary_query: DiaryMemoryQueryService = Depends(get_diary_memory_query_service),
    health_query: HealthRecordQueryService = Depends(get_health_record_query_service),
    timeout_policy: PersonalAssistantTimeoutPolicy = Depends(get_personal_assistant_timeout_policy),
) -> PersonalAssistantAgentFactory:
    return PersonalAssistantAgentFactory(model, diary_query, health_query, timeout_policy)


def get_coaching_personal_assistant_agent_factory(
    model: ToolCallingChatModel = Depends(get_coaching_tool_calling_chat_model),
    diary_query: DiaryMemoryQueryService = Depends(get_diary_memory_query_service),
    health_query: HealthRecordQueryService = Depends(get_health_record_query_service),
    timeout_policy: PersonalAssistantTimeoutPolicy = Depends(get_personal_assistant_timeout_policy),
) -> PersonalAssistantAgentFactory:
    return PersonalAssistantAgentFactory(model, diary_query, health_query, timeout_policy)


def get_health_session_repo(db: AsyncSession = Depends(get_db)) -> HealthSessionRepository:
    return HealthSessionRepositoryImpl(db)
