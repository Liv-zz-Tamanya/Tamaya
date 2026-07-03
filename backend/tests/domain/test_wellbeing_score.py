"""순수 웰빙 스코어러 — 결정론 집계 (G002-1, TDD, AC-6).

CLOVA 독립 순수 함수. 정성신호(정서 + 건강행동 언급)를 0–100 스코어로 집계한다.
"""

from datetime import date

from app.domain.model.emotion import Emotion
from app.domain.model.qualitative_signal import BehaviorMention, QualitativeSignal
from app.domain.model.wellbeing_report import WellbeingReport
from app.domain.service.wellbeing_score import compute_wellbeing_score


def _signal(emotion: Emotion, mentions: list[tuple[str, int]], day: int = 1) -> QualitativeSignal:
    return QualitativeSignal(
        emotion=emotion,
        behavior_mentions=tuple(BehaviorMention(behavior=b, polarity=p) for b, p in mentions),
        recorded_date=date(2026, 6, day),
    )


def test_empty_signals_neutral_score():
    report = compute_wellbeing_score([])
    assert isinstance(report, WellbeingReport)
    assert report.score == 50
    assert report.signal_count == 0


def test_positive_signals_raise_score():
    signals = [_signal(Emotion.HAPPY, [("운동", 1), ("수면", 1)])]
    assert compute_wellbeing_score(signals).score > 50


def test_negative_signals_lower_score():
    signals = [_signal(Emotion.SAD, [("식사거름", -1)])]
    assert compute_wellbeing_score(signals).score < 50


def test_week2_higher_than_week1():
    week1 = [_signal(Emotion.ANXIOUS, [("식사거름", -1)], day=1)]
    week2 = [
        _signal(Emotion.HAPPY, [("운동", 1)], day=8),
        _signal(Emotion.GRATEFUL, [("수면", 1), ("산책", 1)], day=9),
    ]
    assert compute_wellbeing_score(week2).score > compute_wellbeing_score(week1).score


def test_score_clamped_0_100():
    many_positive = [_signal(Emotion.EXCITED, [("운동", 1)] * 50)]
    many_negative = [_signal(Emotion.ANGRY, [("폭식", -1)] * 50)]
    assert compute_wellbeing_score(many_positive).score == 100
    assert compute_wellbeing_score(many_negative).score == 0
