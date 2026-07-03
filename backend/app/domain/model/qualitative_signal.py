"""정성신호 — 코칭 대화에서 추출한 정서 + 건강행동 언급."""

from dataclasses import dataclass, field
from datetime import date

from app.domain.model.emotion import Emotion


@dataclass(frozen=True)
class BehaviorMention:
    behavior: str
    polarity: int  # +1 긍정(운동했다), -1 부정(식사 거름)


@dataclass(frozen=True)
class QualitativeSignal:
    emotion: Emotion
    behavior_mentions: tuple[BehaviorMention, ...] = ()
    recorded_date: date = field(default_factory=date.today)
