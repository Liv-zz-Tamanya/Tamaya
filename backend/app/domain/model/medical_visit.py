"""진료이력 도메인 모델 — 나의건강기록 수입 데이터.

일별 측정이 아니라 이벤트 행이다(같은 날 여러 기관 방문 가능).
병명·진단 정보는 포함하지 않는다 — 원천(나의건강기록 내보내기)에 없고,
민감도와 의료 guardrail 부담을 낮추기 위해 수집하지 않는 것이 정책이다.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class MedicalVisitType(StrEnum):
    OUTPATIENT = "방문 외래"
    PHARMACY = "처방 조제"


@dataclass
class MedicalVisit:
    device_id: str
    visit_date: date
    visit_type: MedicalVisitType
    institution: str
    location: str | None = None
    visit_days: int = 1
    prescription_count: int = 0
    medication_days: int = 0
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if not self.device_id or not self.device_id.strip():
            raise ValueError("device_id는 필수입니다.")
        if len(self.device_id) > 64:
            raise ValueError("device_id는 64자를 초과할 수 없습니다.")
        if not self.institution or not self.institution.strip():
            raise ValueError("institution은 필수입니다.")
        if len(self.institution) > 100:
            raise ValueError("institution은 100자를 초과할 수 없습니다.")
        for name in ("visit_days", "prescription_count", "medication_days"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name}은 음수일 수 없습니다.")
