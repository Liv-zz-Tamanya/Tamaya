"""
키우기 게임 usecase — DEC-022.B FinalizeDiaryUseCase 내부 통합용
GET /game/state · POST /game/diary-complete · POST /game/claim-reward

best-effort 원칙: 게임 로직 실패 시 로그만 남기고 finalize 성공 유지.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.model.game_progress import GameProgress, RewardInventory, apply_diary_completion
from app.infrastructure.persistence.models import (
    GameDiaryCompletionModel,
    GameProgressModel,
    RewardInventoryModel,
)

logger = logging.getLogger(__name__)


class GameProgressUseCase:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_state(self, device_id: str) -> GameProgress:
        """GET /game/state — 없으면 초기 레코드 생성"""
        row = await self._db.scalar(
            select(GameProgressModel).where(GameProgressModel.device_id == device_id)
        )
        if row is None:
            row = GameProgressModel(device_id=device_id)
            self._db.add(row)
            await self._db.commit()
            await self._db.refresh(row)
        return _to_domain(row)

    async def get_inventory(self, device_id: str) -> list[RewardInventory]:
        rows = (
            await self._db.scalars(
                select(RewardInventoryModel).where(RewardInventoryModel.device_id == device_id)
            )
        ).all()
        return [_reward_to_domain(r) for r in rows]

    async def on_diary_complete(self, device_id: str, diary_date: date) -> list[tuple[str, str]]:
        """
        DEC-022.B: FinalizeDiaryUseCase.execute() 마지막에 호출.
        반환: 신규 보상 [(reward_id, reward_type), …] (FE 팝업용)
        """
        try:
            recorded = await self._record_completion_once(device_id, diary_date)
            if not recorded:
                return []

            row = await self._get_or_create_progress_for_update(device_id)

            progress = _to_domain(row)
            updated, new_rewards = apply_diary_completion(progress, diary_date)

            # 도메인 → ORM 동기화
            row.current_streak = updated.current_streak
            row.total_diaries = updated.total_diaries
            row.points = updated.points
            row.level = updated.level
            row.affinity = updated.affinity
            row.last_diary_date = updated.last_diary_date
            row.updated_at = datetime.now()

            await self._save_new_rewards(device_id, new_rewards)

            await self._db.commit()
            return new_rewards
        except Exception as exc:
            logger.warning("game on_diary_complete failed (best-effort): %s", exc)
            await self._db.rollback()
            return []

    async def _record_completion_once(self, device_id: str, diary_date: date) -> bool:
        stmt = (
            pg_insert(GameDiaryCompletionModel)
            .values(
                id=uuid.uuid4(),
                device_id=device_id,
                diary_date=diary_date,
            )
            .on_conflict_do_nothing(
                index_elements=[
                    GameDiaryCompletionModel.device_id,
                    GameDiaryCompletionModel.diary_date,
                ]
            )
            .returning(GameDiaryCompletionModel.id)
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def _get_or_create_progress_for_update(self, device_id: str) -> GameProgressModel:
        await self._db.execute(
            pg_insert(GameProgressModel)
            .values(id=uuid.uuid4(), device_id=device_id)
            .on_conflict_do_nothing(index_elements=[GameProgressModel.device_id])
        )
        row = await self._db.scalar(
            select(GameProgressModel)
            .where(GameProgressModel.device_id == device_id)
            .with_for_update()
        )
        if row is None:
            raise RuntimeError("game_progress row missing after upsert")
        return row

    async def _save_new_rewards(
        self, device_id: str, new_rewards: list[tuple[str, str]]
    ) -> None:
        for reward_id, reward_type in new_rewards:
            await self._db.execute(
                pg_insert(RewardInventoryModel)
                .values(
                    id=uuid.uuid4(),
                    device_id=device_id,
                    reward_id=reward_id,
                    reward_type=reward_type,
                )
                .on_conflict_do_nothing(
                    index_elements=[
                        RewardInventoryModel.device_id,
                        RewardInventoryModel.reward_id,
                    ]
                )
            )

    async def claim_reward(self, device_id: str, reward_id: str) -> RewardInventory | None:
        """POST /game/claim-reward/{reward_id} — is_used=False 확인"""
        row = await self._db.scalar(
            select(RewardInventoryModel).where(
                RewardInventoryModel.device_id == device_id,
                RewardInventoryModel.reward_id == reward_id,
            )
        )
        if row is None:
            return None
        if not row.is_used:
            row.is_used = True
            row.used_at = datetime.now()
            await self._db.commit()
            await self._db.refresh(row)
        return _reward_to_domain(row)


# ─── ORM → Domain 변환 ──────────────────────────────────────────────────────────


def _to_domain(row: GameProgressModel) -> GameProgress:
    return GameProgress(
        id=row.id,
        device_id=row.device_id,
        current_streak=row.current_streak,
        total_diaries=row.total_diaries,
        points=row.points,
        level=row.level,
        affinity=row.affinity,
        last_diary_date=row.last_diary_date,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _reward_to_domain(row: RewardInventoryModel) -> RewardInventory:
    return RewardInventory(
        id=row.id,
        device_id=row.device_id,
        reward_id=row.reward_id,
        reward_type=row.reward_type,
        claimed_at=row.claimed_at,
        is_used=row.is_used,
        used_at=row.used_at,
    )
