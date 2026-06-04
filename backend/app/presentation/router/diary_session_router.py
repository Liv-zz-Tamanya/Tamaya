from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.application.service.ai_chat_service import AiChatService
from app.application.usecase.diary_session import (
    DiarySessionTurnUseCase,
    FinalizeDiarySessionUseCase,
    StartDiarySessionUseCase,
)
from app.domain.model.user import User
from app.domain.repository.daily_check_repository import DailyCheckRepository
from app.domain.repository.diary_session_repository import DiarySessionRepository
from app.infrastructure.config.dependencies import (
    get_ai_chat_service,
    get_current_user,
    get_daily_check_repo,
    get_diary_session_repo,
)
from app.presentation.router.v1_schemas import (
    DiaryFinalizeResponse,
    DiarySessionStartRequest,
    DiarySessionStartResponse,
    DiarySessionTurnRequest,
    DiarySessionTurnResponse,
)

router = APIRouter(prefix="/v1/diary-session", tags=["diary-session"])


@router.post("/start", response_model=DiarySessionStartResponse, summary="일기 세션 시작")
async def start_session(
    body: DiarySessionStartRequest,
    user: User = Depends(get_current_user),
    session_repo: DiarySessionRepository = Depends(get_diary_session_repo),
    ai: AiChatService = Depends(get_ai_chat_service),
    daily_check_repo: DailyCheckRepository = Depends(get_daily_check_repo),
):
    result = await StartDiarySessionUseCase(session_repo, ai, daily_check_repo).execute(
        user_id=user.id, mode=body.mode, session_date=body.date
    )
    return DiarySessionStartResponse(**result)


@router.post("/{session_id}/turn", response_model=DiarySessionTurnResponse, summary="일기 턴 진행")
async def session_turn(
    session_id: UUID,
    body: DiarySessionTurnRequest,
    user: User = Depends(get_current_user),
    session_repo: DiarySessionRepository = Depends(get_diary_session_repo),
    ai: AiChatService = Depends(get_ai_chat_service),
):
    try:
        result = await DiarySessionTurnUseCase(session_repo, ai).execute(
            user_id=user.id, session_id=session_id, turn=body.turn, user_text=body.user_text
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return DiarySessionTurnResponse(**result)


@router.post("/{session_id}/finalize", response_model=DiaryFinalizeResponse, summary="일기 마무리(HCX)")
async def finalize_session(
    session_id: UUID,
    user: User = Depends(get_current_user),
    session_repo: DiarySessionRepository = Depends(get_diary_session_repo),
    ai: AiChatService = Depends(get_ai_chat_service),
):
    try:
        result = await FinalizeDiarySessionUseCase(session_repo, ai).execute(
            user_id=user.id, session_id=session_id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return DiaryFinalizeResponse(**result)
