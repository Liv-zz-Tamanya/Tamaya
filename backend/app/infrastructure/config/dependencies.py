from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.service.ai_chat_service import AiChatService
from app.application.service.embedding_service import EmbeddingService
from app.application.service.health_ai_service import HealthAiService
from app.application.usecase.chat_agent import ChatAgent
from app.application.usecase.extract_chunks import ExtractChunksUseCase
from app.application.usecase.health_chat_agent import HealthChatAgent
from app.domain.model.user import User
from app.domain.repository.chat_session_repository import ChatSessionRepository
from app.domain.repository.character_repository import CharacterRepository
from app.domain.repository.consent_repository import ConsentRepository
from app.domain.repository.daily_check_repository import DailyCheckRepository
from app.domain.repository.diary_entry_repository import DiaryEntryRepository
from app.domain.repository.diary_repository import DiaryRepository
from app.domain.repository.diary_session_repository import DiarySessionRepository
from app.domain.repository.event_chunk_repository import EventChunkRepository
from app.domain.repository.user_repository import UserRepository
from app.infrastructure.auth import jwt_service
from app.infrastructure.auth.jwt_service import TokenError
from app.domain.repository.health_chunk_repository import HealthChunkRepository
from app.domain.repository.health_record_repository import HealthRecordRepository
from app.domain.repository.health_session_repository import HealthSessionRepository
from app.infrastructure.config.database import get_db
from app.infrastructure.external.clova_client import ClovaClient, HealthClovaClient
from app.infrastructure.external.embedding_service_impl import SentenceTransformerEmbeddingService
from app.infrastructure.persistence.chat_session_repository_impl import ChatSessionRepositoryImpl
from app.infrastructure.persistence.character_repository_impl import CharacterRepositoryImpl
from app.infrastructure.persistence.consent_repository_impl import ConsentRepositoryImpl
from app.infrastructure.persistence.daily_check_repository_impl import DailyCheckRepositoryImpl
from app.infrastructure.persistence.diary_entry_repository_impl import DiaryEntryRepositoryImpl
from app.infrastructure.persistence.diary_repository_impl import DiaryRepositoryImpl
from app.infrastructure.persistence.diary_session_repository_impl import DiarySessionRepositoryImpl
from app.infrastructure.persistence.event_chunk_repository_impl import EventChunkRepositoryImpl
from app.infrastructure.persistence.user_repository_impl import UserRepositoryImpl
from app.infrastructure.persistence.health_chunk_repository_impl import HealthChunkRepositoryImpl
from app.infrastructure.persistence.health_record_repository_impl import HealthRecordRepositoryImpl
from app.infrastructure.persistence.health_session_repository_impl import HealthSessionRepositoryImpl

_embedding_service: EmbeddingService | None = None


def get_chat_session_repo(db: AsyncSession = Depends(get_db)) -> ChatSessionRepository:
    return ChatSessionRepositoryImpl(db)


def get_diary_repo(db: AsyncSession = Depends(get_db)) -> DiaryRepository:
    return DiaryRepositoryImpl(db)


def get_event_chunk_repo(db: AsyncSession = Depends(get_db)) -> EventChunkRepository:
    return EventChunkRepositoryImpl(db)


def get_ai_chat_service() -> AiChatService:
    return ClovaClient()


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


# ============================================================
# F1·F4·F5 (P0) — repo 팩토리 + 인증
# ============================================================


def get_user_repo(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepositoryImpl(db)


def get_character_repo(db: AsyncSession = Depends(get_db)) -> CharacterRepository:
    return CharacterRepositoryImpl(db)


def get_consent_repo(db: AsyncSession = Depends(get_db)) -> ConsentRepository:
    return ConsentRepositoryImpl(db)


def get_daily_check_repo(db: AsyncSession = Depends(get_db)) -> DailyCheckRepository:
    return DailyCheckRepositoryImpl(db)


def get_diary_session_repo(db: AsyncSession = Depends(get_db)) -> DiarySessionRepository:
    return DiarySessionRepositoryImpl(db)


def get_diary_entry_repo(db: AsyncSession = Depends(get_db)) -> DiaryEntryRepository:
    return DiaryEntryRepositoryImpl(db)


async def get_current_user(
    authorization: str | None = Header(default=None),
    user_repo: UserRepository = Depends(get_user_repo),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="인증 토큰이 필요합니다.")
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = jwt_service.decode_token(token, expected_type="access")
    except TokenError as e:
        raise HTTPException(status_code=401, detail=str(e))

    from uuid import UUID

    user = await user_repo.find_by_id(UUID(payload["sub"]))
    if user is None:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")
    return user
