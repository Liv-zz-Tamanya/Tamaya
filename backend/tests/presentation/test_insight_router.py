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


# ── 생성형 주간 리포트 API ──────────────────────────────────────────────────


def _report_endpoints_overrides(generate=None, cached=None):
    from app.infrastructure.config.dependencies import (
        get_cached_weekly_insight_report_usecase,
        get_generate_weekly_insight_report_usecase,
    )

    if generate is not None:
        app.dependency_overrides[get_generate_weekly_insight_report_usecase] = lambda: generate
    if cached is not None:
        app.dependency_overrides[get_cached_weekly_insight_report_usecase] = lambda: cached


def _stub_report(status="no_signal", cards=()):
    from datetime import datetime

    from app.domain.model.insight_report import (
        InsightPeriodType,
        InsightReport,
        InsightReportStatus,
    )

    return InsightReport(
        device_id="dev-1",
        period_type=InsightPeriodType.WEEKLY,
        period_key="2026-W31",
        status=InsightReportStatus(status),
        cards=cards,
        selected_hypothesis_keys=tuple(card.hypothesis_key for card in cards),
        payload={"status": status, "cards": []},
        model_meta={},
        created_at=datetime(2026, 8, 3, 9, 0),
        updated_at=datetime(2026, 8, 3, 9, 0),
    )


class _StubGenerateUseCase:
    def __init__(self, report=None, error: Exception | None = None):
        self._report = report or _stub_report()
        self._error = error
        self.calls = 0

    async def execute(self, device_id, year, week):
        self.calls += 1
        if self._error is not None:
            raise self._error
        return self._report, self.calls > 1  # 두 번째 호출부터 캐시로 표시


class _StubCachedUseCase:
    def __init__(self, report=None):
        self._report = report

    async def execute(self, device_id, year, week):
        return self._report


def test_post_weekly_report_generates_then_returns_cache_flag():
    from app.domain.model.insight_report import InsightCard

    card = InsightCard(
        hypothesis_key="sleep_satisfaction",
        title="잠과 만족도의 패턴",
        message="함께 나타나는 경향이 있었어요.",
        evidence_dates=(date(2026, 7, 28),),
    )
    generate = _StubGenerateUseCase(report=_stub_report("generated", (card,)))
    _report_endpoints_overrides(generate=generate)
    client = TestClient(app)

    first = client.post(
        "/api/v1/insights/weekly/report", params={"device_id": "dev-1", "week": "2026-W31"}
    )
    second = client.post(
        "/api/v1/insights/weekly/report", params={"device_id": "dev-1", "week": "2026-W31"}
    )

    assert first.status_code == 200
    body = first.json()
    assert body["status"] == "generated"
    assert body["from_cache"] is False
    assert body["cards"][0]["hypothesis_key"] == "sleep_satisfaction"
    assert second.json()["from_cache"] is True


def test_post_weekly_report_non_generated_status_is_200():
    _report_endpoints_overrides(generate=_StubGenerateUseCase(_stub_report("insufficient_data")))
    client = TestClient(app)
    resp = client.post(
        "/api/v1/insights/weekly/report", params={"device_id": "dev-1", "week": "2026-W31"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "insufficient_data"
    assert resp.json()["cards"] == []


def test_post_weekly_report_bad_week_400():
    _report_endpoints_overrides(generate=_StubGenerateUseCase())
    client = TestClient(app)
    resp = client.post(
        "/api/v1/insights/weekly/report", params={"device_id": "dev-1", "week": "2026-31"}
    )
    assert resp.status_code == 400


def test_post_weekly_report_output_error_returns_502():
    from app.application.service.insight_output_parser import InsightOutputError

    _report_endpoints_overrides(
        generate=_StubGenerateUseCase(error=InsightOutputError("cards는 list여야 합니다"))
    )
    client = TestClient(app)
    resp = client.post(
        "/api/v1/insights/weekly/report", params={"device_id": "dev-1", "week": "2026-W31"}
    )
    assert resp.status_code == 502


def test_get_weekly_report_cache_hit_and_miss():
    _report_endpoints_overrides(cached=_StubCachedUseCase(_stub_report()))
    client = TestClient(app)
    hit = client.get(
        "/api/v1/insights/weekly/report", params={"device_id": "dev-1", "week": "2026-W31"}
    )
    assert hit.status_code == 200
    assert hit.json()["from_cache"] is True

    app.dependency_overrides.clear()
    _report_endpoints_overrides(cached=_StubCachedUseCase(None))
    miss = client.get(
        "/api/v1/insights/weekly/report", params={"device_id": "dev-1", "week": "2026-W31"}
    )
    assert miss.status_code == 404


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
