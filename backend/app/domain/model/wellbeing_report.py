"""웰빙 리포트 — 정성신호 집계 결과(0–100 스코어 + 차원 분해)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class WellbeingReport:
    score: int  # 0–100
    emotion_score: int  # 정서 차원 기여분
    behavior_score: int  # 건강행동 차원 기여분
    signal_count: int
