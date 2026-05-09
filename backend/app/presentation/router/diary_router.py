from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.application.service.ai_chat_service import AiChatService
from app.application.usecase.extract_chunks import ExtractChunksUseCase
from app.application.usecase.finalize_diary import FinalizeDiaryUseCase
from app.application.usecase.get_diary import GetDiaryByDateUseCase
from app.application.usecase.list_diaries import ListDiariesUseCase
from app.domain.repository.chat_session_repository import ChatSessionRepository
from app.domain.repository.diary_repository import DiaryRepository
from app.infrastructure.config.dependencies import (
    get_ai_chat_service,
    get_chat_session_repo,
    get_diary_repo,
    get_extract_chunks_usecase,
)
from app.presentation.router.schemas import DiaryListResponse, DiaryResponse

router = APIRouter(prefix="/api/v1/diaries", tags=["diaries"])


@router.post(
    "/{session_id}/finalize",
    response_model=DiaryResponse,
    summary="대화 기반 일기 생성",
    description="채팅 세션의 대화 내용을 AI가 분석하여 일기를 자동 생성합니다. 하루에 하나의 일기만 작성 가능합니다.",
)
async def finalize_diary(
    session_id: UUID,
    chat_repo: ChatSessionRepository = Depends(get_chat_session_repo),
    diary_repo: DiaryRepository = Depends(get_diary_repo),
    ai: AiChatService = Depends(get_ai_chat_service),
    extract_chunks: ExtractChunksUseCase = Depends(get_extract_chunks_usecase),
):
    usecase = FinalizeDiaryUseCase(chat_repo, diary_repo, ai, extract_chunks)
    try:
        diary = await usecase.execute(session_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return DiaryResponse.from_domain(diary)


@router.get(
    "",
    response_model=DiaryListResponse,
    summary="일기 목록 조회",
    description="작성된 일기를 최신순으로 조회합니다. 페이지네이션을 지원합니다.",
)
async def list_diaries(
    offset: int = Query(0, ge=0, description="건너뛸 항목 수"),
    limit: int = Query(20, ge=1, le=100, description="조회할 항목 수"),
    repo: DiaryRepository = Depends(get_diary_repo),
):
    usecase = ListDiariesUseCase(repo)
    result = await usecase.execute(offset=offset, limit=limit)
    return DiaryListResponse(
        items=[DiaryResponse.from_domain(d) for d in result.items],
        total=result.total,
    )


@router.get(
    "/{diary_date}",
    response_model=DiaryResponse,
    summary="날짜별 일기 조회",
    description="특정 날짜의 일기를 조회합니다. 형식: YYYY-MM-DD",
)
async def get_diary_by_date(
    diary_date: date,
    repo: DiaryRepository = Depends(get_diary_repo),
):
    usecase = GetDiaryByDateUseCase(repo)
    try:
        diary = await usecase.execute(diary_date)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return DiaryResponse.from_domain(diary)
