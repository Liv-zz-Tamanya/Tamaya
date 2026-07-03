"""
키우기 게임 라우터 — DEC-019, DEC-022.B
GET  /game/state
POST /game/diary-complete
POST /game/claim-reward/{reward_id}

X-Device-Id 헤더 기반 device_id 인증 (MVP Phase 1 단계).
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.usecase.game_diary_complete import GameProgressUseCase
from app.infrastructure.config.database import get_db

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


# ─── 헬퍼 ───────────────────────────────────────────────────────────────────────


def _require_device_id(x_device_id: str | None = Header(default=None)) -> str:
    if not x_device_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Device-Id 헤더 필요",
        )
    return x_device_id


# ─── 라우트 ─────────────────────────────────────────────────────────────────────


@router.get("/state", response_model=GameStateResponse, summary="게임 진행 상태 조회")
async def get_game_state(
    device_id: str = Depends(_require_device_id),
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
    device_id: str = Depends(_require_device_id),
    db: AsyncSession = Depends(get_db),
):
    """
    DEC-022.B: FinalizeDiaryUseCase 내부에서도 호출하지만,
    FE가 명시적으로 호출해도 멱등 처리 (best-effort, 중복 보상 방지는 UNIQUE 제약으로 보장).
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
    device_id: str = Depends(_require_device_id),
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
