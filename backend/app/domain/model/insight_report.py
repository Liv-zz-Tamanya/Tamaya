"""인사이트 리포트 도메인 모델 — 통계 게이트를 통과한 발견의 사용자용 산출물.

순수 Python. 통계·선정은 결정론 코드가 담당하고 LLM은 selected 가설의
해석 멘트(카드)만 생성한다. 게이트를 통과하지 못한 기간은 카드 없이
상태(INSUFFICIENT_DATA/NO_SIGNAL/COOLDOWN)로 정직하게 표현한다.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class InsightPeriodType(StrEnum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"  # DB 구조만 대비 — 생성 usecase·API는 아직 주간만


class InsightReportStatus(StrEnum):
    GENERATED = "generated"  # 후보 선정 + LLM 카드 정상 생성
    INSUFFICIENT_DATA = "insufficient_data"  # 검정 가능한 통계값이 없음 — LLM 호출 금지
    NO_SIGNAL = "no_signal"  # 검정은 했으나 게이트 통과 후보 없음 — LLM 호출 금지
    COOLDOWN = "cooldown"  # 통과 후보가 전부 최근 노출됨 — LLM 호출 금지
    SAFETY_BLOCKED = "safety_blocked"  # output guardrail 감지 — 위험 문구를 저장하지 않음


@dataclass(frozen=True)
class InsightCard:
    hypothesis_key: str
    title: str
    message: str
    evidence_dates: tuple[date, ...]

    def __post_init__(self) -> None:
        if not self.hypothesis_key.strip():
            raise ValueError("hypothesis_key는 필수입니다.")
        if not self.title.strip():
            raise ValueError("title은 비어 있을 수 없습니다.")
        if not self.message.strip():
            raise ValueError("message는 비어 있을 수 없습니다.")
        if len(self.evidence_dates) != len(set(self.evidence_dates)):
            raise ValueError("evidence_dates에 중복이 있습니다.")


@dataclass(frozen=True)
class InsightReport:
    device_id: str
    period_type: InsightPeriodType
    period_key: str  # "2026-W31" | "2026-07"
    status: InsightReportStatus
    cards: tuple[InsightCard, ...]
    selected_hypothesis_keys: tuple[str, ...]
    payload: dict  # 입력·결과 스냅샷 (PR-D 재현성) — raw 일기 본문은 넣지 않는다
    model_meta: dict
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if not self.device_id or not self.device_id.strip():
            raise ValueError("device_id는 필수입니다.")
        if self.status == InsightReportStatus.GENERATED:
            if not self.cards:
                raise ValueError("GENERATED 리포트는 카드가 1개 이상이어야 합니다.")
            if not self.selected_hypothesis_keys:
                raise ValueError("GENERATED 리포트는 선정 가설이 1개 이상이어야 합니다.")
        elif self.cards:
            raise ValueError(f"{self.status.value} 리포트는 카드를 가질 수 없습니다.")
