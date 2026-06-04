from datetime import date
from uuid import UUID

from app.domain.model.daily_check import MAX_COUNT, DailyCheck
from app.domain.repository.daily_check_repository import DailyCheckRepository

POINTS_PER_ITEM = 10


class UpsertDailyCheckUseCase:
    def __init__(self, daily_check_repo: DailyCheckRepository) -> None:
        self._repo = daily_check_repo

    async def execute(
        self,
        user_id: UUID,
        check_date: date,
        food: dict,
        water: int,
        sleep: dict,
        movement: dict,
        sun: dict,
    ) -> dict:
        check = DailyCheck(
            user_id=user_id,
            check_date=check_date,
            food=food,
            water=max(0, min(8, water)),
            sleep=sleep,
            movement=movement,
            sun=sun,
        )
        saved = await self._repo.upsert(check)
        return {
            "done_count": saved.done_count,
            "max_count": MAX_COUNT,
            "points_awarded": saved.done_count * POINTS_PER_ITEM,
        }
