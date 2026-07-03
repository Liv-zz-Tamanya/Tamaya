"""인사이트 라우터 — 수직 슬라이스 (G002-3, TDD).

TestClient + dependency_overrides로 실 DB 없이 HTTP→usecase→repo(fake)→순수 스코어러
경로를 검증한다. 빈 기간은 500이 아니라 well-formed 200, 잘못된 파라미터는 400.
"""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.domain.model.emotion import Emotion
from app.domain.model.qualitative_signal import BehaviorMention, QualitativeSignal
from app.domain.repository.qualitative_signal_repository import QualitativeSignalRepository
from app.infrastructure.config.dependencies import get_qualitative_signal_repo
from app.main import app


class _FakeRepo(QualitativeSignalRepository):
    def __init__(self, signals: list[QualitativeSignal]) -> None:
        self._signals = signals

    async def save(self, device_id, session_id, signal) -> None:  # pragma: no cover
        raise NotImplementedError

    async def find_by_date_range(self, device_id, start, end) -> list[QualitativeSignal]:
        return [s for s in self._signals if start <= s.recorded_date <= end]


def _use_repo(signals: list[QualitativeSignal]):
    app.dependency_overrides[get_qualitative_signal_repo] = lambda: _FakeRepo(signals)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_weekly_endpoint_returns_structure():
    _use_repo(
        [
            QualitativeSignal(
                emotion=Emotion.HAPPY,
                behavior_mentions=(BehaviorMention("운동", 1),),
                recorded_date=date(2026, 6, 1),
            )
        ]
    )
    client = TestClient(app)
    resp = client.get("/api/v1/insights/weekly", params={"device_id": "dev-1", "week": "2026-W23"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["period"] == "2026-W23"
    assert body["report"]["signal_count"] == 1
    assert body["report"]["score"] > 50
    assert len(body["trend"]) == 7


def test_weekly_empty_period_no_500():
    _use_repo([])
    client = TestClient(app)
    resp = client.get("/api/v1/insights/weekly", params={"device_id": "dev-1", "week": "2026-W23"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["report"]["score"] == 50
    assert body["report"]["signal_count"] == 0


def test_weekly_bad_week_format_returns_400():
    _use_repo([])
    client = TestClient(app)
    resp = client.get("/api/v1/insights/weekly", params={"device_id": "dev-1", "week": "2026-23"})

    assert resp.status_code == 400


def test_weekly_nonexistent_week53_returns_400_not_500():
    # 2025-W53은 달력에 없음 — usecase까지 새어나가 500이 되면 안 됨
    _use_repo([])
    client = TestClient(app)
    resp = client.get("/api/v1/insights/weekly", params={"device_id": "dev-1", "week": "2025-W53"})

    assert resp.status_code == 400


def test_monthly_endpoint_returns_structure():
    _use_repo(
        [
            QualitativeSignal(
                emotion=Emotion.CALM,
                behavior_mentions=(BehaviorMention("산책", 1),),
                recorded_date=date(2026, 6, 16),
            )
        ]
    )
    client = TestClient(app)
    resp = client.get("/api/v1/insights/monthly", params={"device_id": "dev-1", "month": "2026-06"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["period"] == "2026-06"
    assert body["report"]["signal_count"] == 1
    assert len(body["trend"]) >= 4


def test_monthly_bad_month_returns_400():
    _use_repo([])
    client = TestClient(app)
    resp = client.get("/api/v1/insights/monthly", params={"device_id": "dev-1", "month": "2026-13"})

    assert resp.status_code == 400
