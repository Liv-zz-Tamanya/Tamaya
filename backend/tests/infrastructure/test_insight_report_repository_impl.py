"""InsightReportRepositoryImpl — domain↔ORM 매핑·unique 충돌 안전 처리 검증."""

from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from app.domain.model.insight_report import (
    InsightCard,
    InsightPeriodType,
    InsightReport,
    InsightReportStatus,
)
from app.infrastructure.persistence.insight_report_repository_impl import (
    InsightReportRepositoryImpl,
)
from app.infrastructure.persistence.models import InsightReportModel

NOW = datetime(2026, 8, 3, 9, 0)


def _report(**overrides) -> InsightReport:
    base = dict(
        device_id="dev-1",
        period_type=InsightPeriodType.WEEKLY,
        period_key="2026-W31",
        status=InsightReportStatus.GENERATED,
        cards=(
            InsightCard(
                hypothesis_key="sleep_satisfaction",
                title="잠과 만족도의 패턴",
                message="함께 나타나는 경향이 있었어요.",
                evidence_dates=(date(2026, 7, 28),),
            ),
        ),
        selected_hypothesis_keys=("sleep_satisfaction",),
        payload={
            "schema_version": 1,
            "status": "generated",
            "cards": [
                {
                    "hypothesis_key": "sleep_satisfaction",
                    "title": "잠과 만족도의 패턴",
                    "message": "함께 나타나는 경향이 있었어요.",
                    "evidence_dates": ["2026-07-28"],
                }
            ],
        },
        model_meta={"selected_hypothesis_keys": ["sleep_satisfaction"]},
        created_at=NOW,
        updated_at=NOW,
    )
    base.update(overrides)
    return InsightReport(**base)


class _FakeResult:
    def __init__(self, models):
        self._models = models

    def scalar_one_or_none(self):
        return self._models[0] if self._models else None

    def scalars(self):
        return self

    def all(self):
        return self._models


class _FakeDb:
    def __init__(self, existing=None, commit_error: Exception | None = None):
        self._existing = list(existing or [])
        self._commit_error = commit_error
        self.added = []
        self.rolled_back = False

    async def execute(self, stmt):
        return _FakeResult(self._existing)

    def add(self, model):
        self.added.append(model)

    async def commit(self):
        if self._commit_error is not None:
            error, self._commit_error = self._commit_error, None
            raise error

    async def rollback(self):
        self.rolled_back = True


def _model_row(report: InsightReport) -> InsightReportModel:
    return InsightReportModel(
        id=report.id,
        device_id=report.device_id,
        period_type=report.period_type.value,
        period_key=report.period_key,
        payload=report.payload,
        model_meta=report.model_meta,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


async def test_save_maps_domain_to_orm():
    db = _FakeDb()
    report = _report()
    await InsightReportRepositoryImpl(db).save(report)

    row = db.added[0]
    assert row.period_type == "weekly"
    assert row.payload["status"] == "generated"
    assert row.model_meta["selected_hypothesis_keys"] == ["sleep_satisfaction"]


async def test_unique_violation_returns_existing_report():
    original = _report()
    db = _FakeDb(
        existing=[_model_row(original)],
        commit_error=IntegrityError("insert", {}, Exception("unique")),
    )
    duplicate = _report(id=uuid4())

    saved = await InsightReportRepositoryImpl(db).save(duplicate)

    assert db.rolled_back is True
    assert saved.id == original.id  # 먼저 저장된 리포트를 반환 — 500으로 흘리지 않는다


async def test_round_trip_restores_cards_and_status():
    report = _report()
    restored = InsightReportRepositoryImpl._to_domain(_model_row(report))

    assert restored.status == InsightReportStatus.GENERATED
    assert restored.cards[0].hypothesis_key == "sleep_satisfaction"
    assert restored.cards[0].evidence_dates == (date(2026, 7, 28),)
    assert restored.selected_hypothesis_keys == ("sleep_satisfaction",)


async def test_non_generated_round_trip_has_no_cards():
    report = _report(
        status=InsightReportStatus.COOLDOWN,
        cards=(),
        selected_hypothesis_keys=(),
        payload={"schema_version": 1, "status": "cooldown", "cards": []},
        model_meta={"selected_hypothesis_keys": []},
    )
    restored = InsightReportRepositoryImpl._to_domain(_model_row(report))
    assert restored.status == InsightReportStatus.COOLDOWN
    assert restored.cards == ()
