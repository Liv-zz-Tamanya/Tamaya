from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.application.service.ai_chat_service import AiChatService
from app.application.usecase.chat_agent import ChatAgent
from app.application.usecase.extract_chunks import ExtractChunksUseCase
from app.application.usecase.get_chat_session import GetChatSessionUseCase
from app.application.usecase.send_message import SendMessageUseCase
from app.application.usecase.start_chat_session import StartChatSessionUseCase
from app.domain.repository.chat_session_repository import ChatSessionRepository
from app.domain.repository.diary_repository import DiaryRepository
from app.infrastructure.config.dependencies import (
    get_ai_chat_service,
    get_chat_agent,
    get_chat_session_repo,
    get_diary_repo,
    get_extract_chunks_usecase,
)
from app.presentation.auth_deps import get_current_device_id
from app.presentation.router.schemas import (
    ChatMessageResponse,
    ChatSessionResponse,
    DiaryResponse,
    SendMessageRequest,
    SendMessageResponse,
)

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post(
    "/sessions",
    response_model=ChatSessionResponse,
    summary="채팅 세션 시작/재개",
    description="오늘의 채팅 세션을 시작하거나, 이미 존재하면 기존 세션을 반환합니다. 새 세션 시작 시 AI가 첫 인사 메시지를 자동 생성합니다.",
)
async def start_session(
    device_id: str = Depends(get_current_device_id),
    repo: ChatSessionRepository = Depends(get_chat_session_repo),
    ai: AiChatService = Depends(get_ai_chat_service),
):
    usecase = StartChatSessionUseCase(repo, ai)
    session = await usecase.execute(device_id)
    return ChatSessionResponse.from_domain(session)


@router.get(
    "/sessions/{session_id}",
    response_model=ChatSessionResponse,
    summary="채팅 세션 조회",
    description="세션 ID로 채팅 세션과 전체 메시지 히스토리를 조회합니다.",
)
async def get_session(
    session_id: UUID,
    device_id: str = Depends(get_current_device_id),
    repo: ChatSessionRepository = Depends(get_chat_session_repo),
):
    usecase = GetChatSessionUseCase(repo)
    try:
        session = await usecase.execute(session_id, device_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return ChatSessionResponse.from_domain(session)


@router.post(
    "/sessions/{session_id}/messages",
    response_model=SendMessageResponse,
    summary="메시지 전송",
    description="사용자 메시지를 전송하고 AI 응답을 받습니다. 5-7회 대화 후 AI가 일기 마무리를 제안합니다.",
)
async def send_message(
    session_id: UUID,
    body: SendMessageRequest,
    device_id: str = Depends(get_current_device_id),
    repo: ChatSessionRepository = Depends(get_chat_session_repo),
    ai: AiChatService = Depends(get_ai_chat_service),
    diary_repo: DiaryRepository = Depends(get_diary_repo),
    chat_agent: ChatAgent = Depends(get_chat_agent),
    extract_chunks: ExtractChunksUseCase = Depends(get_extract_chunks_usecase),
):
    usecase = SendMessageUseCase(repo, ai, diary_repo, chat_agent, extract_chunks)
    try:
        user_msg, ai_msg, suggest, diary = await usecase.execute(
            session_id, body.content, device_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return SendMessageResponse(
        user_message=ChatMessageResponse.from_domain(user_msg),
        ai_message=ChatMessageResponse.from_domain(ai_msg),
        should_suggest_finalize=suggest,
        diary=DiaryResponse.from_domain(diary) if diary else None,
    )
