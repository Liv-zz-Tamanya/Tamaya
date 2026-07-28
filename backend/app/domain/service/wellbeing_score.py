"""순수 웰빙 스코어러 — 일기 satisfaction + 개인 기준선 대비 라이프로그.

코칭 QualitativeSignal 의존을 제거하고(PR-F 선행), 사용자가 매일 남기는
일기와 걸음·수면을 점수의 근거로 쓴다. LLM 없음·DB 없음 — list[DailyFact]
in, WellbeingReport out. 테스트가 픽스처만으로 완결된다.
"""

import statistics

from app.domain.model.wellbeing_report import WellbeingReport
from app.domain.service.insight_models import Baselines, DailyFact

# 일기는 사용자가 직접 남긴 주관적 상태고 걸음·수면은 대리 지표다 —
# 주관 쪽에 무게를 둔다. 확정값이 아닌 초기값(측정으로 조정 예정).
WEIGHT_EMOTION = 0.6
WEIGHT_BEHAVIOR = 0.4

# ±2σ 클립은 평균이 아니라 '일 단위'에 먼저 적용한다(winsorize) —
# 16,388걸음 같은 하루가 주간 평균을 통해 점수를 통째로 흔들지 않게.
Z_CLIP_SIGMA = 2.0
_BEHAVIOR_NEUTRAL = 50.0
_BEHAVIOR_WEIGHT_PER_AXIS = 25.0


def _winsorize(value: float, baseline_mean: float | None, baseline_stdev: float | None) -> float:
    """일별 관측값을 기준선 ±2σ 범위로 자른다. 기준선 정보가 없으면 원값."""
    if baseline_mean is None or not baseline_stdev:
        return value
    low = baseline_mean - Z_CLIP_SIGMA * baseline_stdev
    high = baseline_mean + Z_CLIP_SIGMA * baseline_stdev
    return max(low, min(high, value))


def _z_clip(observed_mean: float | None, baseline_mean: float | None, baseline_stdev: float | None) -> float:
    """기준선 대비 z-score(±2σ 클립). 어느 쪽이든 정보가 없으면 중립 0."""
    if observed_mean is None or baseline_mean is None or not baseline_stdev:
        return 0.0
    z = (observed_mean - baseline_mean) / baseline_stdev
    return max(-Z_CLIP_SIGMA, min(Z_CLIP_SIGMA, z))


def compute_wellbeing(facts: list[DailyFact], baselines: Baselines) -> WellbeingReport:
    """기간 facts를 웰빙 리포트로 집계한다(순수·결정론).

    불변식: score is None ⟺ diary_days == 0.
    일기가 한 건도 없으면 0이 아니라 None — '모름'과 '매우 나쁨'을 섞지 않는다.
    """
    diary_facts = [f for f in facts if f.satisfaction is not None]
    lifelog_days = sum(1 for f in facts if f.steps is not None or f.sleep_minutes is not None)

    if not diary_facts:
        return WellbeingReport(
            score=None,
            emotion_score=None,
            behavior_score=None,
            diary_days=0,
            lifelog_days=lifelog_days,
            is_partial=True,
        )

    emotion_score = statistics.mean(float(f.satisfaction) for f in diary_facts)

    steps_observed = [
        _winsorize(float(f.steps), baselines.steps_mean, baselines.steps_stdev)
        for f in facts
        if f.steps is not None
    ]
    sleep_observed = [
        _winsorize(float(f.sleep_minutes), baselines.sleep_mean, baselines.sleep_stdev)
        for f in facts
        if f.sleep_minutes is not None
    ]
    if baselines.unstable or lifelog_days == 0:
        # 기준선이 불안정하거나 기간에 라이프로그가 없으면 판단 유보 — 중립
        behavior_score = _BEHAVIOR_NEUTRAL
    else:
        behavior_score = (
            _BEHAVIOR_NEUTRAL
            + _BEHAVIOR_WEIGHT_PER_AXIS
            * _z_clip(
                statistics.mean(steps_observed) if steps_observed else None,
                baselines.steps_mean,
                baselines.steps_stdev,
            )
            + _BEHAVIOR_WEIGHT_PER_AXIS
            * _z_clip(
                statistics.mean(sleep_observed) if sleep_observed else None,
                baselines.sleep_mean,
                baselines.sleep_stdev,
            )
        )
        behavior_score = max(0.0, min(100.0, behavior_score))

    score = round(WEIGHT_EMOTION * emotion_score + WEIGHT_BEHAVIOR * behavior_score)
    return WellbeingReport(
        score=score,
        emotion_score=round(emotion_score, 1),
        behavior_score=round(behavior_score, 1),
        diary_days=len(diary_facts),
        lifelog_days=lifelog_days,
        is_partial=lifelog_days == 0,
    )
