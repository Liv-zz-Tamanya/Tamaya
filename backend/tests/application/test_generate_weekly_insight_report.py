"""주간 인사이트 리포트 생성 usecase — 캐시·비생성 상태의 LLM 비용 0 보장.

fake 모델의 호출 수를 직접 세서 검증한다:
cache hit / insufficient_data / no_signal / cooldown → model call 0,
정상 생성 → model call 1.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime, timedelta

import pytest
from langchain_core.messages import AIMessage

from app.application.service.insight_output_parser import InsightOutputError
from app.application.usecase.generate_weekly_insight_report import (
    GenerateWeeklyInsightReportUseCase,
    GetCachedWeeklyInsightReportUseCase,
)
from app.application.usecase.personal_assistant_agent_factory import PersonalAssistantAgentFactory
from app.domain.model.diary import Diary
from app.domain.model.emotion import Emotion
from app.domain.model.insight_report import (
    InsightPeriodType,
    InsightReport,
    InsightReportStatus,
)
from app.domain.model.sleep_record import SleepRecord
from app.domain.repository.insight_report_repository import InsightReportRepository
from app.domain.service.insight_period import week_bounds
from tests.application.test_get_insight import (
    FakeDiaryRepo,
    FakeHealthRepo,
    FakeSleepRepo,
    FakeVisitRepo,
    _summary,
)

YEAR, WEEK = 2026, 31
WEEK_KEY = "2026-W31"
START, END = week_bounds(YEAR, WEEK)
NOW = datetime(2026, 8, 3, 9, 0)


class InMemoryReportRepo(InsightReportRepository):
    def __init__(self, reports: list[InsightReport] | None = None) -> None:
        self.reports: list[InsightReport] = list(reports or [])

    async def find_by_period(self, device_id, period_type, period_key):
        for report in self.reports:
            if (
                report.device_id == device_id
                and report.period_type == period_type
                and report.period_key == period_key
            ):
                return report
        return None

    async def find_recent(self, device_id, since):
        return [
            r for r in self.reports if r.device_id == device_id and r.created_at >= since
        ]

    async def save(self, report):
        self.reports.append(report)
        return report


class _FakeModel:
    def __init__(self, responses: Sequence[AIMessage]) -> None:
        self._responses = list(responses)
        self.call_count = 0

    async def ainvoke(self, messages, tools) -> AIMessage:
        self.call_count += 1
        return self._responses.pop(0)


class _FakeDiaryQuery:
    async def search_similar(self, device_id, query, exclude_session_id=None, limit=5):
        return []


class _FakeHealthQuery:
    async def search_similar(self, device_id, query, limit=5):
        return []


def _valid_output(key: str = "sleep_satisfaction", evidence: list[str] | None = None) -> str:
    return json.dumps(
        {
            "cards": [
                {
                    "hypothesis_key": key,
                    "title": "잠과 만족도의 패턴",
                    "message": "함께 나타나는 경향이 있었어요.",
                    "evidence_dates": evidence or [],
                }
            ]
        },
        ensure_ascii=False,
    )


def _correlated_week_data() -> tuple[list, list]:
    """주간 7일 전부 + 기준선 창까지 강한 양의 수면↔만족도 상관 데이터."""
    diaries, sleeps = [], []
    for offset in range(90):
        day = END - timedelta(days=offset)
        low = offset % 2 == 0
        sleeps.append(
            SleepRecord(device_id="dev-1", record_date=day, duration_minutes=300 if low else 520)
        )
        diaries.append(
            Diary(
                device_id="dev-1",
                diary_date=day,
                title="t",
                content="c",
                emotion=Emotion.TIRED if low else Emotion.HAPPY,
                satisfaction=25 if low else 85,
            )
        )
    return diaries, sleeps


def _usecase(
    *,
    report_repo: InMemoryReportRepo | None = None,
    model: _FakeModel | None = None,
    diaries=None,
    sleeps=None,
    summaries=None,
) -> tuple[GenerateWeeklyInsightReportUseCase, InMemoryReportRepo, _FakeModel]:
    repo = report_repo or InMemoryReportRepo()
    fake_model = model or _FakeModel([AIMessage(content=_valid_output())])
    factory = PersonalAssistantAgentFactory(fake_model, _FakeDiaryQuery(), _FakeHealthQuery())
    usecase = GenerateWeeklyInsightReportUseCase(
        report_repo=repo,
        health_repo=FakeHealthRepo(summaries),
        sleep_repo=FakeSleepRepo(sleeps),
        diary_repo=FakeDiaryRepo(diaries),
        visit_repo=FakeVisitRepo(),
        agent_factory=factory,
        model_name="test-model",
        clock=lambda: NOW,
    )
    return usecase, repo, fake_model


def _cached_report(status=InsightReportStatus.NO_SIGNAL) -> InsightReport:
    return InsightReport(
        device_id="dev-1",
        period_type=InsightPeriodType.WEEKLY,
        period_key=WEEK_KEY,
        status=status,
        cards=(),
        selected_hypothesis_keys=(),
        payload={"status": status.value, "cards": []},
        model_meta={},
        created_at=NOW - timedelta(days=1),
        updated_at=NOW - timedelta(days=1),
    )


async def test_cache_hit_returns_without_model_call():
    usecase, _, model = _usecase(report_repo=InMemoryReportRepo([_cached_report()]))

    report, from_cache = await usecase.execute("dev-1", YEAR, WEEK)

    assert from_cache is True
    assert report.status == InsightReportStatus.NO_SIGNAL
    assert model.call_count == 0


async def test_insufficient_data_saved_without_model_call():
    usecase, repo, model = _usecase()  # 데이터 전혀 없음

    report, from_cache = await usecase.execute("dev-1", YEAR, WEEK)

    assert report.status == InsightReportStatus.INSUFFICIENT_DATA
    assert report.cards == ()
    assert from_cache is False
    assert model.call_count == 0
    assert len(repo.reports) == 1  # 비생성 상태도 저장(같은 주 재호출 시 캐시)


async def test_no_signal_saved_without_model_call():
    # 검정은 가능하지만(n>=20) 상관 없는 데이터 — 걸음만, 수면 없음
    diaries = [
        Diary(
            device_id="dev-1",
            diary_date=END - timedelta(days=offset),
            title="t",
            content="c",
            emotion=Emotion.CALM,
            satisfaction=50 + ((offset * 17) % 23) - 11,
        )
        for offset in range(60)
    ]
    summaries = [
        _summary(END - timedelta(days=offset), 7000 + ((offset * 991) % 800)) for offset in range(60)
    ]
    usecase, _, model = _usecase(diaries=diaries, summaries=summaries)

    report, _ = await usecase.execute("dev-1", YEAR, WEEK)

    assert report.status == InsightReportStatus.NO_SIGNAL
    assert model.call_count == 0


async def test_cooldown_saved_without_model_call():
    diaries, sleeps = _correlated_week_data()
    exposed = InsightReport(
        device_id="dev-1",
        period_type=InsightPeriodType.WEEKLY,
        period_key="2026-W30",
        status=InsightReportStatus.GENERATED,
        cards=(
            __import__(
                "app.domain.model.insight_report", fromlist=["InsightCard"]
            ).InsightCard(
                hypothesis_key="sleep_satisfaction",
                title="t",
                message="m",
                evidence_dates=(),
            ),
        ),
        selected_hypothesis_keys=("sleep_satisfaction",),
        payload={"status": "generated", "cards": []},
        model_meta={},
        created_at=NOW - timedelta(days=7),
        updated_at=NOW - timedelta(days=7),
    )
    usecase, _, model = _usecase(
        report_repo=InMemoryReportRepo([exposed]), diaries=diaries, sleeps=sleeps
    )

    report, _ = await usecase.execute("dev-1", YEAR, WEEK)

    assert report.status == InsightReportStatus.COOLDOWN
    assert model.call_count == 0


async def test_generated_report_with_single_model_call():
    diaries, sleeps = _correlated_week_data()
    usecase, repo, model = _usecase(diaries=diaries, sleeps=sleeps)

    report, from_cache = await usecase.execute("dev-1", YEAR, WEEK)

    assert report.status == InsightReportStatus.GENERATED
    assert from_cache is False
    assert model.call_count == 1
    assert report.selected_hypothesis_keys == ("sleep_satisfaction",)
    assert report.cards[0].hypothesis_key == "sleep_satisfaction"
    # generation_run_id == report.id (trace 연결용 참조)
    assert report.model_meta["generation_run_id"] == str(report.id)
    assert report.model_meta["model"] == "test-model"
    assert report.payload["status"] == "generated"
    assert report.payload["verified_candidates"]  # gate 탈락 포함 스냅샷
    assert len(repo.reports) == 1


async def test_second_call_uses_cache_without_model_call():
    diaries, sleeps = _correlated_week_data()
    usecase, _, model = _usecase(diaries=diaries, sleeps=sleeps)

    first, first_cached = await usecase.execute("dev-1", YEAR, WEEK)
    second, second_cached = await usecase.execute("dev-1", YEAR, WEEK)

    assert (first_cached, second_cached) == (False, True)
    assert second.id == first.id
    assert model.call_count == 1  # 재호출에 LLM 비용 없음


async def test_safety_blocked_output_not_stored_as_cards():
    diaries, sleeps = _correlated_week_data()
    dangerous = AIMessage(content="수면제를 10mg 복용하면 만족도가 오를 거예요.")
    usecase, repo, model = _usecase(
        diaries=diaries, sleeps=sleeps, model=_FakeModel([dangerous])
    )

    report, _ = await usecase.execute("dev-1", YEAR, WEEK)

    assert report.status == InsightReportStatus.SAFETY_BLOCKED
    assert report.cards == ()
    assert model.call_count == 1
    stored = repo.reports[0]
    assert stored.payload["cards"] == []
    assert "mg" not in json.dumps(stored.payload, ensure_ascii=False)  # 위험 원문 미저장


async def test_parse_failure_raises_and_saves_nothing():
    diaries, sleeps = _correlated_week_data()
    usecase, repo, _ = _usecase(
        diaries=diaries,
        sleeps=sleeps,
        model=_FakeModel([AIMessage(content="이번 주 정말 좋았어요!")]),
    )

    with pytest.raises(InsightOutputError):
        await usecase.execute("dev-1", YEAR, WEEK)

    assert repo.reports == []  # 잘못된 payload를 캐시에 저장하지 않는다


async def test_cached_lookup_usecase():
    repo = InMemoryReportRepo([_cached_report()])
    usecase = GetCachedWeeklyInsightReportUseCase(repo)

    assert (await usecase.execute("dev-1", YEAR, WEEK)) is not None
    assert (await usecase.execute("dev-1", YEAR, 30)) is None
