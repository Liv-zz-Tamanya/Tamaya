"""라이프로그 더미 생성기 — seed 재현성·coverage·심은 효과·도메인 제약 검증."""

from __future__ import annotations

from datetime import date

from app.domain.model.emotion import Emotion
from app.domain.model.health_record import HealthDailySummary
from app.domain.model.sleep_record import SleepRecord
from evals.lifelog_generator import PROFILES, generate_lifelog

END = date(2026, 7, 27)


def _rank(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    for rank, index in enumerate(order):
        ranks[index] = float(rank)
    return ranks


def _spearman(xs: list[float], ys: list[float]) -> float:
    rx, ry = _rank(xs), _rank(ys)
    n = len(xs)
    mx, my = sum(rx) / n, sum(ry) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry, strict=True))
    vx = sum((a - mx) ** 2 for a in rx) ** 0.5
    vy = sum((b - my) ** 2 for b in ry) ** 0.5
    return cov / (vx * vy)


def test_generator_deterministic():
    a = generate_lifelog(PROFILES["null"], "eval-null-01", END)
    b = generate_lifelog(PROFILES["null"], "eval-null-01", END)
    assert a == b


def test_generator_coverage():
    fixture = generate_lifelog(PROFILES["sparse"], "eval-sparse-01", END)
    days = PROFILES["sparse"].days
    observed_rate = len(fixture.sleep_records) / days
    # sleep_coverage=0.15 → 결측률 0.85 ± 0.05
    assert 0.10 <= observed_rate <= 0.20


def test_planted_effect_present():
    """생성기 자체 검증 — 전날 수면과 satisfaction의 순위 상관이 실제로 심겼는가."""
    fixture = generate_lifelog(PROFILES["planted_strong"], "eval-planted-01", END)
    sleep_by_date = {r["record_date"]: r["duration_minutes"] for r in fixture.sleep_records}

    pairs: list[tuple[float, float]] = []
    for diary in fixture.diaries:
        diary_date = date.fromisoformat(diary["diary_date"])
        prev = (diary_date - date.resolution).isoformat()
        if prev in sleep_by_date:
            pairs.append((float(sleep_by_date[prev]), float(diary["satisfaction"])))

    assert len(pairs) >= 40  # 표본이 너무 작으면 검증 자체가 무의미
    rho = _spearman([p[0] for p in pairs], [p[1] for p in pairs])
    assert rho >= 0.3, f"심은 효과(0.45)가 관측되지 않음: rho={rho:.3f}"


def test_null_profile_has_no_planted_effect():
    fixture = generate_lifelog(PROFILES["null"], "eval-null-01", END)
    assert fixture.meta["planted_effects"] == {}


def test_health_summary_constraints():
    """생성 행이 도메인 검증과 (device_id, source_hash) UNIQUE를 통과해야 한다."""
    fixture = generate_lifelog(PROFILES["planted_strong"], "eval-planted-01", END)

    hashes = [row["source_hash"] for row in fixture.health_summaries]
    assert len(hashes) == len(set(hashes))  # UNIQUE 재현 가능

    for row in fixture.health_summaries:
        HealthDailySummary(
            device_id="eval-planted-01",
            record_date=date.fromisoformat(row["record_date"]),
            **{k: v for k, v in row.items() if k != "record_date"},
        )


def test_sleep_rows_pass_domain_validation():
    fixture = generate_lifelog(PROFILES["sparse"], "eval-sparse-01", END)
    for row in fixture.sleep_records:
        record = SleepRecord(
            device_id="eval-sparse-01",
            record_date=date.fromisoformat(row["record_date"]),
            duration_minutes=row["duration_minutes"],
        )
        assert 0 < record.duration_minutes <= 24 * 60


def test_diary_rows_use_valid_emotions_and_range():
    fixture = generate_lifelog(PROFILES["demo"], "eval-demo-01", END)
    assert fixture.diaries, "demo 프로파일에 일기가 있어야 한다"
    for row in fixture.diaries:
        Emotion(row["emotion"])  # 어휘 밖이면 ValueError
        assert 0 <= row["satisfaction"] <= 100
        assert row["satisfaction_estimated"] is False
