"""웰빙 리포트 — 일기·라이프로그 기반 집계 결과 (DEC-B5 전면 재정의).

이전 정의(코칭 정성신호 기여분 합산)와 달리 emotion/behavior가
0~100 절대 스케일이고, '모름'은 0이 아니라 None으로 표현한다 —
0은 '매우 나쁨'으로 읽히지만 실제 의미는 '모름'이라 완전히 다르다.

불변식: score is None ⟺ diary_days == 0
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class WellbeingReport:
    score: int | None  # 0–100, 일기가 없으면 None
    emotion_score: float | None  # 기간 일기 satisfaction 평균 (0–100)
    behavior_score: float | None  # 개인 기준선 대비 걸음·수면 (0–100)
    diary_days: int  # satisfaction이 관측된 일기 일수 (estimated 제외)
    lifelog_days: int  # 걸음 또는 수면이 관측된 날 수
    is_partial: bool  # 어떤 축(일기/라이프로그)이 비었는가
