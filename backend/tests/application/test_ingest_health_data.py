from __future__ import annotations

from datetime import date

import pytest

from app.domain.model.health_record import HealthDailySummary
from scripts.ingest_health_data import HealthChunkBuilder, _validate_device_id


class _FakeEmbeddingService:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]


def _summary(device_id: str, source_hash: str = "hash-x") -> HealthDailySummary:
    return HealthDailySummary(
        device_id=device_id,
        record_date=date(2026, 7, 10),
        step_count=1000,
        step_goal=6000,
        step_goal_achieved=False,
        step_calories=10.0,
        step_distance_m=700.0,
        has_exercise=False,
        exercise_duration_sec=0,
        exercise_distance_m=0.0,
        exercise_calories=0.0,
        heart_rate_avg=None,
        heart_rate_min=None,
        heart_rate_max=None,
        floors_climbed=0,
        source_hash=source_hash,
    )


def test_validate_device_id_rejects_blank_value():
    with pytest.raises(ValueError, match="빈 값"):
        _validate_device_id("   ")


def test_validate_device_id_rejects_over_64_chars():
    with pytest.raises(ValueError, match="64자"):
        _validate_device_id("x" * 65)


def test_health_chunk_builder_copies_summary_device_id():
    chunks = HealthChunkBuilder(_FakeEmbeddingService()).build([_summary("dev-a")])

    assert len(chunks) == 1
    assert chunks[0].device_id == "dev-a"


def test_same_source_hash_can_belong_to_different_devices_in_domain():
    first = _summary("dev-a", source_hash="hash-x")
    second = _summary("dev-b", source_hash="hash-x")

    assert first.source_hash == second.source_hash
    assert first.device_id != second.device_id
