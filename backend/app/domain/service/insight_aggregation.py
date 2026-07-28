"""인사이트 결정론 집계 — 순수 함수(외부 의존 0, stdlib statistics만 사용).

가장 중요한 규칙: build_daily_facts는 start~end의 **모든 캘린더 날짜에 대해
정확히 1행씩** 생성한다. 데이터가 없는 날을 생략하면 후속 통계(PR-B2)의
lag 계산이 하루씩 밀리는데, 값이 그럴듯해서 발견되지 않는다.
"""

import statistics
from datetime import date, timedelta

from app.domain.model.diary import Diary
from app.domain.model.health_record import HealthDailySummary
from app.domain.model.medical_visit import MedicalVisit
from app.domain.model.sleep_record import SleepRecord
from app.domain.service.insight_models import Baselines, DailyFact

BASELINE_WINDOW_DAYS = 90
BASELINE_MIN_OBSERVED_DAYS = 30


def build_daily_facts(
    summaries: list[HealthDailySummary],
    sleeps: list[SleepRecord],
    diaries: list[Diary],
    visits: list[MedicalVisit],
    start: date,
    end: date,
    steps_p75: float | None = None,
) -> list[DailyFact]:
    """start~end(양끝 포함)의 모든 캘린더 날짜에 대해 정확히 1행씩 생성한다."""
    steps_by_date = {s.record_date: s.step_count for s in summaries}
    sleep_by_date = {s.record_date: s.duration_minutes for s in sleeps}
    diary_by_date = {d.diary_date: d for d in diaries}
    visit_dates = {v.visit_date for v in visits}

    facts: list[DailyFact] = []
    day = start
    while day <= end:
        diary = diary_by_date.get(day)
        satisfaction: int | None = None
        emotion: str | None = None
        if diary is not None:
            emotion = diary.emotion.value
            if not diary.satisfaction_estimated:
                satisfaction = diary.satisfaction
        facts.append(
            DailyFact(
                date=day,
                steps=steps_by_date.get(day),  # 0은 실제 관측, None은 미측정
                sleep_minutes=sleep_by_date.get(day),
                satisfaction=satisfaction,
                emotion=emotion,
                has_medical_visit=day in visit_dates,
                steps_p75=steps_p75,
                is_weekend=day.weekday() >= 5,
            )
        )
        day += timedelta(days=1)
    return facts


def compute_baselines(facts: list[DailyFact]) -> Baselines:
    """최근 90일 창의 facts에서 개인 기준선을 계산한다. 관측 30일 미만이면 unstable."""
    steps_observed = [float(f.steps) for f in facts if f.steps is not None]
    sleep_observed = [float(f.sleep_minutes) for f in facts if f.sleep_minutes is not None]
    observed_days = sum(
        1 for f in facts if f.steps is not None or f.sleep_minutes is not None
    )

    return Baselines(
        steps_mean=statistics.mean(steps_observed) if steps_observed else None,
        steps_stdev=statistics.stdev(steps_observed) if len(steps_observed) >= 2 else None,
        sleep_mean=statistics.mean(sleep_observed) if sleep_observed else None,
        sleep_stdev=statistics.stdev(sleep_observed) if len(sleep_observed) >= 2 else None,
        steps_p75=(
            statistics.quantiles(steps_observed, n=4)[2] if len(steps_observed) >= 4 else None
        ),
        observed_days=observed_days,
        unstable=observed_days < BASELINE_MIN_OBSERVED_DAYS,
    )
