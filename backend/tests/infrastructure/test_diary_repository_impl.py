"""DiaryRepositoryImpl — satisfaction_estimated 매핑 3곳(insert/upsert/복원) 검증.

특히 upsert 경로는 하루 1개 정책 때문에 재회고 시 타는 경로인데,
매핑이 누락돼도 신규 저장은 정상 동작해 테스트 없이는 놓치기 쉽다.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

import pytest

from app.domain.model.diary import Diary
from app.domain.model.emotion import Emotion
from app.infrastructure.persistence.diary_repository_impl import DiaryRepositoryImpl
from app.infrastructure.persistence.models import DiaryModel


class _FakeResult:
    def __init__(self, existing: DiaryModel | None) -> None:
        self._existing = existing

    def scalar_one_or_none(self) -> DiaryModel | None:
        return self._existing


class _FakeDb:
    def __init__(self, existing: DiaryModel | None = None) -> None:
        self._existing = existing
        self.added: list[DiaryModel] = []

    async def execute(self, stmt):
        return _FakeResult(self._existing)

    def add(self, model: DiaryModel) -> None:
        self.added.append(model)

    async def commit(self) -> None:
        pass


def _estimated_diary() -> Diary:
    return Diary(
        device_id="dev-a",
        diary_date=date(2026, 7, 28),
        title="짧은 기록",
        content="오늘은 말을 많이 하지 못했다.",
        emotion=Emotion.CALM,
        satisfaction=50,
        satisfaction_estimated=True,
        keywords=["기록"],
    )


@pytest.mark.asyncio
async def test_estimated_persisted_on_insert():
    db = _FakeDb(existing=None)
    await DiaryRepositoryImpl(db).save(_estimated_diary())

    assert len(db.added) == 1
    assert db.added[0].satisfaction_estimated is True


@pytest.mark.asyncio
async def test_estimated_persisted_on_upsert():
    existing = DiaryModel(
        id=uuid4(),
        device_id="dev-a",
        diary_date=date(2026, 7, 28),
        title="아침 회고",
        content="예전 내용",
        emotion="happy",
        satisfaction=70,
        satisfaction_estimated=False,
        keywords=["아침"],
    )
    db = _FakeDb(existing=existing)
    await DiaryRepositoryImpl(db).save(_estimated_diary())

    assert db.added == []  # upsert 경로 — 새 행을 만들지 않는다
    assert existing.satisfaction == 50
    assert existing.satisfaction_estimated is True


def test_estimated_restored_from_model():
    model = DiaryModel(
        id=uuid4(),
        device_id="dev-a",
        diary_date=date(2026, 7, 28),
        title="짧은 기록",
        content="본문",
        emotion="calm",
        satisfaction=50,
        satisfaction_estimated=True,
        keywords=["기록"],
        chat_session_id=None,
        created_at=datetime(2026, 7, 28, 22, 0),
    )

    diary = DiaryRepositoryImpl._to_domain(model)

    assert diary.satisfaction_estimated is True
