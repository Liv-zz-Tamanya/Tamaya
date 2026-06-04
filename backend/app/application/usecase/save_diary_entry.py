from datetime import date, timedelta
from uuid import UUID

from app.domain.model.diary_entry import DiaryEntry
from app.domain.repository.diary_entry_repository import DiaryEntryRepository

POINTS_DELTA = 80
MILESTONES = {14: "🦺 조끼", 30: "🎩 모자", 60: "🛋 새 방", 90: "👑 왕관"}


class SaveDiaryEntryUseCase:
    def __init__(self, entry_repo: DiaryEntryRepository) -> None:
        self._entry_repo = entry_repo

    async def execute(
        self,
        user_id: UUID,
        entry_date: date,
        moods: list[str],
        keywords: list[str],
        body: str,
        tomorrow: str,
        daily_check_snapshot: dict,
        session_id: UUID | None,
    ) -> dict:
        if await self._entry_repo.find_by_date(user_id, entry_date):
            raise ValueError("already_saved_today")

        entry = DiaryEntry(
            user_id=user_id,
            entry_date=entry_date,
            body=body,
            moods=moods,
            keywords=keywords,
            tomorrow=tomorrow,
            daily_check_snapshot=daily_check_snapshot,
            points=POINTS_DELTA,
            session_id=session_id,
        )
        await self._entry_repo.save(entry)

        existing_dates = set(await self._entry_repo.list_dates(user_id))
        new_streak = self._compute_streak(existing_dates, entry_date)
        items_unlocked = [MILESTONES[new_streak]] if new_streak in MILESTONES else []

        return {
            "diary_id": entry.id,
            "reward": {
                "points_delta": POINTS_DELTA,
                "streak_delta": 1,
                "new_streak": new_streak,
                "items_unlocked": items_unlocked,
                "level_up": False,
                "item_drop": None,
            },
        }

    @staticmethod
    def _compute_streak(dates: set[date], current: date) -> int:
        streak = 0
        day = current
        while day in dates:
            streak += 1
            day = day - timedelta(days=1)
        return streak
