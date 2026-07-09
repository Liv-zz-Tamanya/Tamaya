from __future__ import annotations

import uuid
from datetime import date, datetime

from app.application.usecase.game_diary_complete import GameProgressUseCase
from app.infrastructure.persistence.models import GameProgressModel


class _FakeDb:
    def __init__(self) -> None:
        self.commit_count = 0
        self.rollback_count = 0

    async def commit(self) -> None:
        self.commit_count += 1

    async def rollback(self) -> None:
        self.rollback_count += 1


class _MemoryGameProgressUseCase(GameProgressUseCase):
    def __init__(self) -> None:
        super().__init__(_FakeDb())
        self._completions: set[tuple[str, date]] = set()
        self._progress_rows: dict[str, GameProgressModel] = {}
        self._reward_ids: dict[str, set[str]] = {}

    @property
    def db(self) -> _FakeDb:
        return self._db

    async def _record_completion_once(self, device_id: str, diary_date: date) -> bool:
        key = (device_id, diary_date)
        if key in self._completions:
            return False
        self._completions.add(key)
        return True

    async def _get_or_create_progress_for_update(self, device_id: str) -> GameProgressModel:
        row = self._progress_rows.get(device_id)
        if row is None:
            now = datetime.now()
            row = GameProgressModel(
                id=uuid.uuid4(),
                device_id=device_id,
                current_streak=0,
                total_diaries=0,
                points=0,
                level=1,
                affinity=0,
                last_diary_date=None,
                created_at=now,
                updated_at=now,
            )
            self._progress_rows[device_id] = row
        return row

    async def _save_new_rewards(
        self, device_id: str, new_rewards: list[tuple[str, str]]
    ) -> None:
        store = self._reward_ids.setdefault(device_id, set())
        for reward_id, _ in new_rewards:
            store.add(reward_id)

    def row(self, device_id: str) -> GameProgressModel:
        return self._progress_rows[device_id]


async def test_same_diary_date_is_counted_once():
    uc = _MemoryGameProgressUseCase()

    first = await uc.on_diary_complete("dev-1", date(2026, 7, 8))
    second = await uc.on_diary_complete("dev-1", date(2026, 7, 8))
    row = uc.row("dev-1")

    assert first == []
    assert second == []
    assert row.current_streak == 1
    assert row.total_diaries == 1
    assert row.points == 10
    assert row.affinity == 2
    assert row.last_diary_date == date(2026, 7, 8)
    assert uc.db.commit_count == 1


async def test_consecutive_days_still_advance_progress():
    uc = _MemoryGameProgressUseCase()

    await uc.on_diary_complete("dev-1", date(2026, 7, 8))
    await uc.on_diary_complete("dev-1", date(2026, 7, 9))
    row = uc.row("dev-1")

    assert row.current_streak == 2
    assert row.total_diaries == 2
    assert row.points == 20
    assert row.affinity == 4
    assert row.last_diary_date == date(2026, 7, 9)


async def test_duplicate_streak_gate_reward_is_not_regranted():
    uc = _MemoryGameProgressUseCase()

    await uc.on_diary_complete("dev-1", date(2026, 7, 8))
    await uc.on_diary_complete("dev-1", date(2026, 7, 9))
    first_reward = await uc.on_diary_complete("dev-1", date(2026, 7, 10))
    duplicate_reward = await uc.on_diary_complete("dev-1", date(2026, 7, 10))
    row = uc.row("dev-1")

    assert first_reward == [("churu_1", "snack")]
    assert duplicate_reward == []
    assert row.current_streak == 3
    assert row.total_diaries == 3
    assert uc._reward_ids["dev-1"] == {"churu_1"}
