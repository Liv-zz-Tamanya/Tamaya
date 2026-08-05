"""
키우기 게임 라우터 — DEC-019, DEC-022.B
GET  /game/state
POST /game/diary-complete
POST /game/claim-reward/{reward_id}

device_id는 Bearer 토큰 세션에서 추출한다 — 기존 X-Device-Id 헤더 방식은
헤더 값만 바꾸면 타인 게임 데이터를 조회·조작할 수 있었다.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.usecase.game_diary_complete import GameProgressUseCase
from app.infrastructure.config.database import get_db
from app.presentation.auth_deps import get_current_device_id

router = APIRouter(prefix="/game", tags=["game"])


# ─── 스키마 ─────────────────────────────────────────────────────────────────────


class GameStateResponse(BaseModel):
    device_id: str
    current_streak: int
    total_diaries: int
    points: int
    level: int
    affinity: int  # 0~100 (이음이 호감도, DEC-020 정합)
    last_diary_date: date | None
    inventory: list[str]  # FE rewardSystem.ts와 1:1 매핑 (reward_id 목록)


class DiaryCompleteRequest(BaseModel):
    diary_date: date


class DiaryCompleteResponse(BaseModel):
    state: GameStateResponse
    new_rewards: list[str]  # 신규 unlocked reward_id 목록


class ClaimRewardResponse(BaseModel):
    reward_id: str
    is_used: bool
    used_at: str | None


# ─── 라우트 ─────────────────────────────────────────────────────────────────────


@router.get("/state", response_model=GameStateResponse, summary="게임 진행 상태 조회")
async def get_game_state(
    device_id: str = Depends(get_current_device_id),
    db: AsyncSession = Depends(get_db),
):
    usecase = GameProgressUseCase(db)
    progress = await usecase.get_state(device_id)
    inventory = await usecase.get_inventory(device_id)
    return GameStateResponse(
        device_id=progress.device_id,
        current_streak=progress.current_streak,
        total_diaries=progress.total_diaries,
        points=progress.points,
        level=progress.level,
        affinity=progress.affinity,
        last_diary_date=progress.last_diary_date,
        inventory=[r.reward_id for r in inventory],
    )


@router.post(
    "/diary-complete", response_model=DiaryCompleteResponse, summary="일기 완료 → 게임 보상"
)
async def diary_complete(
    body: DiaryCompleteRequest,
    device_id: str = Depends(get_current_device_id),
    db: AsyncSession = Depends(get_db),
):
    """
    DEC-022.B: FinalizeDiaryUseCase 내부에서도 호출하지만,
    FE가 명시적으로 재호출해도 device_id + diary_date 처리 이력으로 멱등 처리한다.
    """
    usecase = GameProgressUseCase(db)
    new_rewards_raw = await usecase.on_diary_complete(device_id, body.diary_date)
    progress = await usecase.get_state(device_id)
    inventory = await usecase.get_inventory(device_id)
    return DiaryCompleteResponse(
        state=GameStateResponse(
            device_id=progress.device_id,
            current_streak=progress.current_streak,
            total_diaries=progress.total_diaries,
            points=progress.points,
            level=progress.level,
            affinity=progress.affinity,
            last_diary_date=progress.last_diary_date,
            inventory=[r.reward_id for r in inventory],
        ),
        new_rewards=[rid for rid, _ in new_rewards_raw],
    )


@router.post(
    "/claim-reward/{reward_id}",
    response_model=ClaimRewardResponse,
    summary="보상 사용 처리",
)
async def claim_reward(
    reward_id: str,
    device_id: str = Depends(get_current_device_id),
    db: AsyncSession = Depends(get_db),
):
    usecase = GameProgressUseCase(db)
    reward = await usecase.claim_reward(device_id, reward_id)
    if reward is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"보상 '{reward_id}'를 찾을 수 없습니다",
        )
    return ClaimRewardResponse(
        reward_id=reward.reward_id,
        is_used=reward.is_used,
        used_at=str(reward.used_at) if reward.used_at else None,
    )
