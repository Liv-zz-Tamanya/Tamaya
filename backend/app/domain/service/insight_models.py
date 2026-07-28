"""인사이트 집계의 순수 데이터 모델 — DailyFact와 개인 기준선.

결측 표현 원칙:
- 값이 None이면 '측정 안 됨', 0이면 '실제 관측이 0'. 절대 섞지 않는다.
- imputation(평균 대입·전일 복사) 금지 — 표본이 작아 노이즈가 신호를 압도한다.
  소비하는 쪽이 listwise deletion으로 처리하고 남은 n을 보고한다.
"""

from dataclasses import dataclass
from datetime import date as date_type


@dataclass(frozen=True)
class DailyFact:
    """하루 단위로 결합된 걸음·수면·일기·진료 사실.

    satisfaction은 satisfaction_estimated=True(LLM 판단 불가) 행을 None으로
    취급한다 — '모름'을 중립 50으로 섞지 않는다(PR-A2).
    sleep_minutes의 귀속일은 기상일 기준(PR-A 확정), 별도 시프트 없음.
    """

    date: date_type
    steps: int | None
    sleep_minutes: int | None
    satisfaction: int | None  # 0~100
    emotion: str | None  # Emotion enum value
    has_medical_visit: bool
    steps_p75: float | None  # 개인 기준선 대비 파생 — 집계 시 주입
    is_weekend: bool


@dataclass(frozen=True)
class Baselines:
    """개인 기준선(최근 90일). 절대 기준(1만보)이 아니라 개인 분포 기준 —
    '평소보다 많이 걸은 날'은 사람마다 다르다."""

    steps_mean: float | None
    steps_stdev: float | None
    sleep_mean: float | None
    sleep_stdev: float | None
    steps_p75: float | None
    observed_days: int  # 걸음 또는 수면이 관측된 날 수
    unstable: bool  # 관측 30일 미만 — 기준선 대비 판단을 유보한다
