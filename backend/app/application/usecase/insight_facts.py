"""인사이트 usecase 공통 — 4개 소스 조회 + DailyFact/기준선 조립.

기준선은 조회 기간과 무관하게 항상 최근 90일 창(end-89 ~ end)에서 계산한다.
주간 조회라도 '평소보다'의 기준은 한 주가 아니라 개인의 최근 이력이어야 하기 때문.
"""

from dataclasses import replace
from datetime import date, timedelta

from app.domain.repository.diary_repository import DiaryRepository
from app.domain.repository.health_record_repository import HealthRecordRepository
from app.domain.repository.medical_visit_repository import MedicalVisitRepository
from app.domain.repository.sleep_record_repository import SleepRecordRepository
from app.domain.service.insight_aggregation import (
    BASELINE_WINDOW_DAYS,
    build_daily_facts,
    compute_baselines,
)
from app.domain.service.insight_models import Baselines, DailyFact


async def load_period_facts(
    health_repo: HealthRecordRepository,
    sleep_repo: SleepRecordRepository,
    diary_repo: DiaryRepository,
    visit_repo: MedicalVisitRepository,
    device_id: str,
    start: date,
    end: date,
) -> tuple[list[DailyFact], Baselines]:
    """[start, end] 기간의 DailyFact와 최근 90일 기준선을 반환한다."""
    baseline_start = end - timedelta(days=BASELINE_WINDOW_DAYS - 1)
    fetch_start = min(start, baseline_start)

    summaries = await health_repo.find_by_date_range(device_id, fetch_start, end)
    sleeps = await sleep_repo.find_by_date_range(device_id, fetch_start, end)
    diaries = await diary_repo.find_by_date_range(device_id, fetch_start, end)
    visits = await visit_repo.find_by_date_range(device_id, fetch_start, end)

    window_facts = build_daily_facts(summaries, sleeps, diaries, visits, fetch_start, end)
    baselines = compute_baselines([f for f in window_facts if f.date >= baseline_start])
    period_facts = [
        replace(f, steps_p75=baselines.steps_p75)
        for f in window_facts
        if start <= f.date <= end
    ]
    return period_facts, baselines
