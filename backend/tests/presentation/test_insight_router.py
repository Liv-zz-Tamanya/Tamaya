"""인사이트 라우터 — 수직 슬라이스 + DEC-B1 불변식.

TestClient + dependency_overrides로 실 DB 없이 HTTP→usecase→repo(fake)→순수 스코어러
경로를 검증한다. 빈 기간은 500이 아니라 well-formed 200(score=null·signal_count=0),
잘못된 파라미터는 400.
"""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.domain.model.diary import Diary
from app.domain.model.emotion import Emotion
from app.domain.model.wellbeing_report import WellbeingReport
from app.infrastructure.config.dependencies import (
    get_diary_repo,
    get_health_record_repo,
    get_medical_visit_repo,
    get_sleep_record_repo,
)
from app.main import app
from app.presentation.router.insight_schemas import WellbeingReportResponse
from tests.application.test_get_insight import (
    FakeDiaryRepo,
    FakeHealthRepo,
    FakeSleepRepo,
    FakeVisitRepo,
    _summary,
)


def _use_repos(diaries: list[Diary] | None = None, summaries=None) -> None:
    app.dependency_overrides[get_diary_repo] = lambda: FakeDiaryRepo(diaries)
    app.dependency_overrides[get_health_record_repo] = lambda: FakeHealthRepo(summaries)
    app.dependency_overrides[get_sleep_record_repo] = lambda: FakeSleepRepo()
    app.dependency_overrides[get_medical_visit_repo] = lambda: FakeVisitRepo()


def _diary(day: date, satisfaction: int = 70) -> Diary:
    return Diary(
        device_id="dev-1",
        diary_date=day,
        title="t",
        content="c",
        emotion=Emotion.HAPPY,
        satisfaction=satisfaction,
    )


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_weekly_endpoint_returns_structure():
    _use_repos(diaries=[_diary(date(2026, 6, 1), 80)])
    client = TestClient(app)
    resp = client.get("/api/v1/insights/weekly", params={"device_id": "dev-1", "week": "2026-W23"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["period"] == "2026-W23"
    assert body["report"]["score"] is not None
    assert body["report"]["signal_count"] == 1  # 일기 관측 일수
    assert body["report"]["diary_days"] == 1
    assert len(body["trend"]) == 1  # DEC-B2: 일기 있는 날만


def test_weekly_empty_period_no_500():
    _use_repos()
    client = TestClient(app)
    resp = client.get("/api/v1/insights/weekly", params={"device_id": "dev-1", "week": "2026-W23"})

    assert resp.status_code == 200
    body = resp.json()
    # DEC-B1: '모름'은 0이 아니라 null — signal_count=0과 반드시 함께
    assert body["report"]["score"] is None
    assert body["report"]["signal_count"] == 0
    assert body["trend"] == []


def test_weekly_lifelog_only_takes_empty_path():
    # 걸음만 있고 일기 없음 → signal_count=0 → 프론트는 기존 empty 화면을 탄다
    start = date(2026, 6, 1)  # 2026-W23 월요일
    _use_repos(summaries=[_summary(start + timedelta(days=i), 8000) for i in range(7)])
    client = TestClient(app)
    resp = client.get("/api/v1/insights/weekly", params={"device_id": "dev-1", "week": "2026-W23"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["report"]["score"] is None
    assert body["report"]["signal_count"] == 0
    assert body["report"]["lifelog_days"] == 7


def test_weekly_bad_week_format_returns_400():
    _use_repos()
    client = TestClient(app)
    resp = client.get("/api/v1/insights/weekly", params={"device_id": "dev-1", "week": "2026-23"})

    assert resp.status_code == 400


def test_weekly_nonexistent_week53_returns_400_not_500():
    _use_repos()
    client = TestClient(app)
    resp = client.get("/api/v1/insights/weekly", params={"device_id": "dev-1", "week": "2025-W53"})

    assert resp.status_code == 400


def test_monthly_endpoint_returns_structure():
    _use_repos(diaries=[_diary(date(2026, 6, 16), 60)])
    client = TestClient(app)
    resp = client.get("/api/v1/insights/monthly", params={"device_id": "dev-1", "month": "2026-06"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["period"] == "2026-06"
    assert body["report"]["signal_count"] == 1
    assert len(body["trend"]) == 1  # DEC-B2: 일기 있는 주만


def test_monthly_bad_month_returns_400():
    _use_repos()
    client = TestClient(app)
    resp = client.get("/api/v1/insights/monthly", params={"device_id": "dev-1", "month": "2026-13"})

    assert resp.status_code == 400


def test_schema_invariant_rejects_none_score_with_nonzero_count():
    # DEC-B1 불변식: score=None ⟺ signal_count=0 — 어기면 직렬화 단계에서 시끄럽게 실패
    broken = WellbeingReport(
        score=None,
        emotion_score=None,
        behavior_score=None,
        diary_days=3,  # 모순: score가 None인데 일기 관측이 있다고 주장
        lifelog_days=0,
        is_partial=True,
    )
    with pytest.raises(ValueError):
        WellbeingReportResponse.from_domain(broken)


def test_schema_invariant_accepts_consistent_report():
    ok = WellbeingReport(
        score=62,
        emotion_score=65.0,
        behavior_score=55.0,
        diary_days=4,
        lifelog_days=6,
        is_partial=False,
    )
    resp = WellbeingReportResponse.from_domain(ok)
    assert resp.signal_count == 4
    assert resp.diary_days == 4
