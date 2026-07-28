"""라이프로그 더미 생성기 — 정답을 심은 결정론 픽스처 (인사이트 PR-B).

실사용자가 없는 지금은 '정답을 심을 수 있다'는 것이 강점이다.
심은 효과(planted_effects)를 통계 엔진이 찾아내는지(재현율),
순수 노이즈에서 없는 효과를 만들지 않는지(거짓양성)를 숫자로 검증한다.
PR-B2의 통계 회귀 테스트가 전적으로 이 생성기에 의존한다.

설계 원칙:
- 같은 seed면 항상 같은 출력 (random.Random(seed)만 사용, uuid·now 미사용)
- 진짜 값은 항상 생성하고, coverage는 '기록 여부'만 결정한다(MCAR).
  실제 세계의 인과(전날 수면 → 만족도)는 측정 여부와 무관하게 존재하기 때문.
- 결측은 행 자체를 만들지 않는 것으로 표현한다. 0으로 채우지 않는다.
- SleepRecord.record_date는 기상일 기준(PR-A 확정)이다. 따라서 same-date
  sleep과 satisfaction의 페어링이 제품 의미상 '지난밤 수면과 오늘 만족도'에
  해당한다 — 효과 주입과 통계 검정 모두 이 규칙을 쓴다.

사용:
    uv run python -m evals.lifelog_generator --profile null \\
        --device-id eval-null-01 --end-date 2026-07-27 --out evals/fixtures/lifelog_null.jsonl
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

# 생성 파라미터 — z-score 계산과 노이즈에 같은 sigma를 쓴다(효과 크기의 기준 단위)
SLEEP_SIGMA_MIN = 45.0
STEPS_SIGMA = 1800.0
SATISFACTION_SIGMA = 10.0
WEEKEND_SLEEP_BONUS_MIN = 35.0
WEEKEND_STEPS_PENALTY = 800.0

_EMOTION_WEIGHTS_HIGH = {
    "happy": 0.30, "excited": 0.20, "grateful": 0.20, "calm": 0.20,
    "tired": 0.05, "sad": 0.02, "anxious": 0.02, "angry": 0.01,
}
_EMOTION_WEIGHTS_MID = {
    "calm": 0.35, "tired": 0.20, "happy": 0.15, "anxious": 0.10,
    "sad": 0.10, "excited": 0.05, "grateful": 0.04, "angry": 0.01,
}
_EMOTION_WEIGHTS_LOW = {
    "tired": 0.30, "sad": 0.25, "anxious": 0.20, "angry": 0.10,
    "calm": 0.10, "happy": 0.03, "excited": 0.01, "grateful": 0.01,
}


@dataclass(frozen=True)
class LifelogProfile:
    name: str
    days: int
    sleep_coverage: float  # 0.0~1.0, 수면 기록이 존재하는 날의 비율
    steps_coverage: float
    diary_rate: float  # 일기 작성률
    planted_effects: dict[str, float]  # {"sleep_satisfaction": 0.45}
    seed: int


@dataclass(frozen=True)
class LifelogFixture:
    """3개 테이블에 넣을 행 목록 + 생성 메타.

    행은 id·created_at 없는 순수 dict라 seed 재현성이 깨지지 않는다.
    평가 러너는 meta.planted_effects와 엔진이 찾은 효과를 자동 대조한다.
    """

    meta: dict
    sleep_records: list[dict] = field(default_factory=list)
    health_summaries: list[dict] = field(default_factory=list)
    diaries: list[dict] = field(default_factory=list)


PROFILES: dict[str, LifelogProfile] = {
    "planted_strong": LifelogProfile(
        name="planted_strong",
        days=90,
        sleep_coverage=0.95,
        steps_coverage=0.90,
        diary_rate=0.85,
        # planted rho는 노이즈(σ=10)와 타 효과가 섞여 실현 상관이 더 낮아진다
        # (0.45+0.45 → 실현 r ≈ 0.38). 재현율 검증용이므로 게이트(|rho|>=0.30)
        # 대비 여유가 있어야 해서 둘 다 0.45로 심는다.
        planted_effects={"sleep_satisfaction": 0.45, "steps_satisfaction": 0.45},
        seed=20260702,  # 두 가설 모두 표본 rho >= 0.35가 되는 결정론 seed
    ),
    "null": LifelogProfile(  # 거짓양성 검증 — 가장 중요
        name="null",
        days=90,
        sleep_coverage=0.95,
        steps_coverage=0.90,
        diary_rate=0.85,
        planted_effects={},
        seed=20260702,
    ),
    "sparse": LifelogProfile(  # abstain 검증
        name="sparse",
        days=90,
        sleep_coverage=0.15,
        steps_coverage=0.30,
        diary_rate=0.25,
        planted_effects={},
        seed=20260703,
    ),
    "demo": LifelogProfile(  # 시연·프론트 확인용
        name="demo",
        days=120,
        sleep_coverage=0.95,
        steps_coverage=0.90,
        diary_rate=0.85,
        planted_effects={"sleep_satisfaction": 0.30},
        seed=20260704,
    ),
}


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _pick_emotion(rng: random.Random, satisfaction: int) -> str:
    # satisfaction과 느슨하게만 연동 — 결정론 매핑이면 정보가 중복돼 서술 재료로 무의미
    if satisfaction >= 70:
        weights = _EMOTION_WEIGHTS_HIGH
    elif satisfaction >= 40:
        weights = _EMOTION_WEIGHTS_MID
    else:
        weights = _EMOTION_WEIGHTS_LOW
    return rng.choices(list(weights.keys()), weights=list(weights.values()), k=1)[0]


def _health_summary_row(record_date: date, steps: int) -> dict:
    """걸음수에서 부수 필드를 결정론으로 파생 — 도메인 검증·UNIQUE 제약 통과가 목적.

    source_hash는 PR-A 수입 경로와 동일 규칙(myhr-{date})이라
    (device_id, source_hash) UNIQUE와 재시드 멱등이 함께 보장된다.
    """
    return {
        "record_date": record_date.isoformat(),
        "step_count": steps,
        "step_goal": 10000,
        "step_goal_achieved": steps >= 10000,
        "step_calories": round(steps * 0.04, 1),
        "step_distance_m": round(steps * 0.75, 1),
        "has_exercise": False,
        "exercise_duration_sec": 0,
        "exercise_distance_m": 0.0,
        "exercise_calories": 0.0,
        "heart_rate_avg": None,
        "heart_rate_min": None,
        "heart_rate_max": None,
        "floors_climbed": 0,
        "source_hash": f"myhr-{record_date.isoformat()}",
    }


def _diary_row(diary_date: date, satisfaction: int, emotion: str) -> dict:
    return {
        "diary_date": diary_date.isoformat(),
        "title": f"{diary_date.month}월 {diary_date.day}일의 기록",
        "content": (
            f"오늘 하루를 돌아봤다. 전반적인 만족도는 {satisfaction}점 정도였다. "
            "내일은 또 내일의 일이 있을 것이다."
        ),
        "emotion": emotion,
        "satisfaction": satisfaction,
        "satisfaction_estimated": False,
        "keywords": ["하루", "기록"],
    }


def generate_lifelog(profile: LifelogProfile, device_id: str, end_date: date) -> LifelogFixture:
    """결정론적 생성. 같은 (profile, device_id, end_date)면 항상 같은 결과."""
    rng = random.Random(profile.seed)
    start_date = end_date - timedelta(days=profile.days - 1)

    # 1) 개인 기준선 (사용자마다 다름)
    base_satisfaction = _clip(rng.gauss(62, 8), 20, 90)
    base_sleep_min = _clip(rng.gauss(430, 25), 300, 540)
    base_steps = _clip(rng.gauss(7500, 1500), 3000, 12000)

    sleep_rows: list[dict] = []
    summary_rows: list[dict] = []
    diary_rows: list[dict] = []

    for offset in range(profile.days):
        day = start_date + timedelta(days=offset)
        is_weekend = day.weekday() >= 5

        # 2) 주중/주말 리듬 (전 프로파일 공통 — 현실성 확보용, 심은 효과 아님)
        sleep_mu = base_sleep_min + (WEEKEND_SLEEP_BONUS_MIN if is_weekend else 0.0)
        steps_mu = base_steps - (WEEKEND_STEPS_PENALTY if is_weekend else 0.0)
        sleep_true = _clip(rng.gauss(sleep_mu, SLEEP_SIGMA_MIN), 180, 1440)
        steps_true = max(0, round(rng.gauss(steps_mu, STEPS_SIGMA)))

        # 3) 심은 효과 — z-score × rho × sigma 를 satisfaction에 가산.
        #    수면은 same-date: record_date=기상일이므로 오늘 행의 수면이 곧
        #    '지난밤 수면'이고, 그것이 오늘 만족도에 영향을 준다는 가설이다.
        effect = 0.0
        rho_sleep = profile.planted_effects.get("sleep_satisfaction", 0.0)
        if rho_sleep:
            z_sleep = (sleep_true - base_sleep_min) / SLEEP_SIGMA_MIN
            effect += rho_sleep * z_sleep * SATISFACTION_SIGMA
        rho_steps = profile.planted_effects.get("steps_satisfaction", 0.0)
        if rho_steps:
            z_steps = (steps_true - base_steps) / STEPS_SIGMA
            effect += rho_steps * z_steps * SATISFACTION_SIGMA

        # 4) 노이즈 + clip
        satisfaction = int(
            _clip(round(base_satisfaction + effect + rng.gauss(0, SATISFACTION_SIGMA)), 0, 100)
        )
        emotion = _pick_emotion(rng, satisfaction)

        # 5) coverage에 따라 랜덤 결측 (MCAR — 비무작위 결측은 별도 프로파일에서 다룬다)
        if rng.random() < profile.sleep_coverage:
            sleep_rows.append(
                {"record_date": day.isoformat(), "duration_minutes": round(sleep_true)}
            )
        if rng.random() < profile.steps_coverage:
            summary_rows.append(_health_summary_row(day, steps_true))
        if rng.random() < profile.diary_rate:
            diary_rows.append(_diary_row(day, satisfaction, emotion))

    meta = {
        "profile": profile.name,
        "device_id": device_id,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "days": profile.days,
        "seed": profile.seed,
        "planted_effects": dict(profile.planted_effects),
        "sleep_coverage": profile.sleep_coverage,
        "steps_coverage": profile.steps_coverage,
        "diary_rate": profile.diary_rate,
    }
    return LifelogFixture(
        meta=meta,
        sleep_records=sleep_rows,
        health_summaries=summary_rows,
        diaries=diary_rows,
    )


def write_jsonl(fixture: LifelogFixture, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        f.write(json.dumps({"table": "_meta", **fixture.meta}, ensure_ascii=False) + "\n")
        for table, rows in (
            ("sleep_records", fixture.sleep_records),
            ("health_daily_summaries", fixture.health_summaries),
            ("diaries", fixture.diaries),
        ):
            for row in rows:
                f.write(json.dumps({"table": table, **row}, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=sorted(PROFILES), required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--end-date", type=date.fromisoformat, required=True)
    parser.add_argument("--seed", type=int, default=None, help="프로파일 기본 seed 재정의")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    profile = PROFILES[args.profile]
    if args.seed is not None:
        profile = dataclasses.replace(profile, seed=args.seed)

    fixture = generate_lifelog(profile, args.device_id, args.end_date)
    write_jsonl(fixture, args.out)
    print(
        f"{profile.name}: sleep={len(fixture.sleep_records)} "
        f"steps={len(fixture.health_summaries)} diaries={len(fixture.diaries)} → {args.out}"
    )


if __name__ == "__main__":
    main()
