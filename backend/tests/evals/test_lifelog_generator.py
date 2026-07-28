"""라이프로그 더미 생성기 — seed 재현성·coverage·심은 효과·도메인 제약 검증.

Spearman은 자체 구현 대신 scipy를 쓴다 — satisfaction이 정수라 동점이 잦은데,
동점 평균 순위 처리가 실제 통계 엔진과 같아야 검증이 의미 있다.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from scipy.stats import spearmanr

from app.domain.model.emotion import Emotion
from app.domain.model.health_record import HealthDailySummary
from app.domain.model.sleep_record import SleepRecord
from evals.lifelog_generator import PROFILES, generate_lifelog

END = date(2026, 7, 27)


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


def _same_date_pairs(fixture, predictor_rows: list[dict], value_key: str) -> tuple[list, list]:
    # record_date=기상일 규칙에서 same-date 페어링이 '지난밤 수면 ↔ 오늘 만족도'다
    by_date = {r.get("record_date") or r.get("diary_date"): r[value_key] for r in predictor_rows}
    xs, ys = [], []
    for diary in fixture.diaries:
        if diary["diary_date"] in by_date:
            xs.append(float(by_date[diary["diary_date"]]))
            ys.append(float(diary["satisfaction"]))
    return xs, ys


def test_planted_sleep_effect_present():
    """생성기 자체 검증 — same-date 수면과 satisfaction의 순위 상관이 실제로 심겼는가."""
    fixture = generate_lifelog(PROFILES["planted_strong"], "eval-planted-01", END)
    xs, ys = _same_date_pairs(fixture, fixture.sleep_records, "duration_minutes")

    assert len(xs) >= 40  # 표본이 너무 작으면 검증 자체가 무의미
    rho = spearmanr(xs, ys).statistic
    assert rho >= 0.3, f"심은 효과(0.45)가 관측되지 않음: rho={rho:.3f}"


def test_planted_steps_effect_present():
    fixture = generate_lifelog(PROFILES["planted_strong"], "eval-planted-01", END)
    xs, ys = _same_date_pairs(fixture, fixture.health_summaries, "step_count")

    assert len(xs) >= 40
    rho = spearmanr(xs, ys).statistic
    assert rho >= 0.3, f"심은 효과(0.30)가 관측되지 않음: rho={rho:.3f}"


def test_null_profile_has_no_planted_effect():
    fixture = generate_lifelog(PROFILES["null"], "eval-null-01", END)
    assert fixture.meta["planted_effects"] == {}


def test_planted_keys_use_new_names():
    # 가설 키 개명(sleep_lag1_satisfaction → sleep_satisfaction) 회귀 방지
    assert set(PROFILES["planted_strong"].planted_effects) == {
        "sleep_satisfaction",
        "steps_satisfaction",
    }
    assert set(PROFILES["demo"].planted_effects) == {"sleep_satisfaction"}
    generator_source = (
        Path(__file__).resolve().parents[2] / "evals" / "lifelog_generator.py"
    ).read_text(encoding="utf-8")
    assert "sleep_lag1_satisfaction" not in generator_source


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
