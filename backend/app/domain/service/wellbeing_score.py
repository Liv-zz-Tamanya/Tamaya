"""순수 웰빙 스코어러 — CLOVA 독립 결정론 집계 (AC-6).

고정 가중치 순수 함수: 중립 기준 50에서 정서 valence와 건강행동 polarity를
가중 합산해 0–100으로 clamp한다. 비결정적 LLM과 분리되어 단위테스트로 검증 가능.
"""

from app.domain.model.emotion import Emotion
from app.domain.model.qualitative_signal import QualitativeSignal
from app.domain.model.wellbeing_report import WellbeingReport

_POSITIVE_EMOTIONS = frozenset({Emotion.HAPPY, Emotion.CALM, Emotion.EXCITED, Emotion.GRATEFUL})
_NEGATIVE_EMOTIONS = frozenset({Emotion.SAD, Emotion.ANGRY, Emotion.ANXIOUS, Emotion.TIRED})

_BASE_SCORE = 50
_WEIGHT_EMOTION = 5
_WEIGHT_BEHAVIOR = 5


def _emotion_valence(emotion: Emotion) -> int:
    if emotion in _POSITIVE_EMOTIONS:
        return 1
    if emotion in _NEGATIVE_EMOTIONS:
        return -1
    return 0


def compute_wellbeing_score(signals: list[QualitativeSignal]) -> WellbeingReport:
    """정성신호 목록을 0–100 웰빙 스코어로 집계한다(순수·결정론)."""
    emotion_sum = sum(_emotion_valence(s.emotion) for s in signals)
    behavior_sum = sum(m.polarity for s in signals for m in s.behavior_mentions)

    emotion_score = emotion_sum * _WEIGHT_EMOTION
    behavior_score = behavior_sum * _WEIGHT_BEHAVIOR
    score = max(0, min(100, _BASE_SCORE + emotion_score + behavior_score))

    return WellbeingReport(
        score=score,
        emotion_score=emotion_score,
        behavior_score=behavior_score,
        signal_count=len(signals),
    )
