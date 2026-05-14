"""
키우기 게임 도메인 모델 — DEC-019 Must-Have 9번 (DEC-022.B, DEC-020 BUG-07 정합)
FE rewardSystem.ts와 1:1 매핑.
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID, uuid4

# FE rewardSystem.ts REWARDS 배열과 동일한 streak gate → reward_id 매핑
STREAK_REWARDS: dict[int, tuple[str, str]] = {
    3:  ("churu_1",      "snack"),
    5:  ("toy_ball",     "toy"),
    7:  ("churu_2",      "snack"),
    10: ("toy_mouse",    "toy"),
    14: ("toy_feather",  "toy"),
    21: ("churu_premium","snack"),
}


@dataclass
class GameProgress:
    """
    device_id 1개당 1레코드.
    level = (total_diaries // 10) + 1
    affinity = 0~100 (일기 1건 finalize 시 +2, DEC-020 정합)
    """
    id: UUID = field(default_factory=uuid4)
    device_id: str = ""
    current_streak: int = 0
    total_diaries: int = 0
    points: int = 0               # 일기 1건 = +10
    level: int = 1
    affinity: int = 0             # 0~100
    last_diary_date: date | None = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class RewardInventory:
    """
    획득·수령한 보상 인벤토리.
    reward_id: FE REWARDS[].id ('churu_1', 'toy_ball' 등)
    """
    id: UUID = field(default_factory=uuid4)
    device_id: str = ""
    reward_id: str = ""
    reward_type: str = ""     # 'toy' | 'snack'
    claimed_at: datetime = field(default_factory=datetime.now)
    is_used: bool = False
    used_at: datetime | None = None


def apply_diary_completion(
    progress: GameProgress,
    diary_date: date,
) -> tuple[GameProgress, list[tuple[str, str]]]:
    """
    일기 finalize 시 호출 (DEC-022.B: FinalizeDiaryUseCase 내부 통합).
    streak 판정 → 포인트 → 레벨 → 호감도 갱신.
    반환: (갱신된 progress, 신규 보상 [(reward_id, reward_type), …])
    """
    is_consecutive = (
        progress.last_diary_date is not None
        and (diary_date - progress.last_diary_date).days == 1
    )

    if is_consecutive:
        progress.current_streak += 1
    else:
        progress.current_streak = 1  # 연속 끊기면 1로 리셋

    progress.total_diaries += 1
    progress.points += 10
    progress.level = (progress.total_diaries // 10) + 1
    progress.affinity = min(100, progress.affinity + 2)
    progress.last_diary_date = diary_date
    progress.updated_at = datetime.now()

    new_rewards = [
        (rid, rtype)
        for gate, (rid, rtype) in STREAK_REWARDS.items()
        if gate == progress.current_streak
    ]
    return progress, new_rewards
