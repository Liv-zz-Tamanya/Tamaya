"""수면 기록 도메인 모델 — 나의건강기록 수입 데이터.

걸음(HealthDailySummary)과 달리 측정일이 희소하다(매일 있지 않음).
'기록 없는 날'과 '0분 잔 날'을 구분해야 하므로 별도 테이블로 둔다.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID, uuid4

MAX_SLEEP_MINUTES = 24 * 60


@dataclass
class SleepRecord:
    device_id: str
    record_date: date
    duration_minutes: int
    source: str = "myhealthrecord"
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if not self.device_id or not self.device_id.strip():
            raise ValueError("device_id는 필수입니다.")
        if len(self.device_id) > 64:
            raise ValueError("device_id는 64자를 초과할 수 없습니다.")
        if not 0 < self.duration_minutes <= MAX_SLEEP_MINUTES:
            raise ValueError(f"duration_minutes는 1~{MAX_SLEEP_MINUTES} 범위여야 합니다.")
        if not self.source or not self.source.strip():
            raise ValueError("source는 필수입니다.")
