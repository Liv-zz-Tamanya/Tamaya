from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.service.ai_chat_service import AiChatService
from app.application.service.clova_connection_tester import ClovaConnectionTester
from app.application.service.coaching_ai_service import CoachingAiService
from app.application.service.embedding_service import EmbeddingService
from app.application.service.health_ai_service import HealthAiService
from app.application.service.signal_extraction_service import SignalExtractionService
from app.application.usecase.chat_agent import ChatAgent
from app.application.usecase.coaching_agent import CoachingAgent
from app.application.usecase.extract_chunks import ExtractChunksUseCase
from app.application.usecase.extract_signals import ExtractSignalsUseCase
from app.application.usecase.get_monthly_insight import GetMonthlyInsightUseCase
from app.application.usecase.get_weekly_insight import GetWeeklyInsightUseCase
from app.application.usecase.health_chat_agent import HealthChatAgent
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
from app.infrastructure.external.coaching_clova import CoachingClovaClient
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


def get_chat_agent(
    ai: AiChatService = Depends(get_ai_chat_service),
    embedding: EmbeddingService = Depends(get_embedding_service),
    event_chunk_repo: EventChunkRepository = Depends(get_event_chunk_repo),
) -> ChatAgent:
    return ChatAgent(ai, embedding, event_chunk_repo)


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


def get_coaching_ai_service(
    x_clova_api_key: str | None = Header(default=None),
) -> CoachingAiService:
    # BYOK: 코칭 경로도 chat과 동일하게 요청별 키를 우선순위대로 해석한다.
    cred = resolve_clova_credential(
        user_key=x_clova_api_key,
        env_key=settings.clova_api_key,
        mock_mode=settings.clova_mock_mode,
    )
    return CoachingClovaClient(api_key=cred.api_key, mock=cred.use_mock)


def get_coaching_agent(
    ai: CoachingAiService = Depends(get_coaching_ai_service),
) -> CoachingAgent:
    return CoachingAgent(ai)


def get_clova_connection_tester() -> ClovaConnectionTester:
    return ClovaConnectionTesterImpl()


def get_clova_setting_repo(db: AsyncSession = Depends(get_db)) -> ClovaSettingRepository:
    return ClovaSettingRepositoryImpl(db)


def get_health_ai_service() -> HealthAiService:
    return HealthClovaClient()


def get_health_record_repo(db: AsyncSession = Depends(get_db)) -> HealthRecordRepository:
    return HealthRecordRepositoryImpl(db)


def get_health_chunk_repo(db: AsyncSession = Depends(get_db)) -> HealthChunkRepository:
    return HealthChunkRepositoryImpl(db)


def get_health_session_repo(db: AsyncSession = Depends(get_db)) -> HealthSessionRepository:
    return HealthSessionRepositoryImpl(db)


def get_health_chat_agent(
    ai: HealthAiService = Depends(get_health_ai_service),
    embedding: EmbeddingService = Depends(get_embedding_service),
    health_chunk_repo: HealthChunkRepository = Depends(get_health_chunk_repo),
) -> HealthChatAgent:
    return HealthChatAgent(ai, embedding, health_chunk_repo)
