"""코칭 정성신호 추출 평가의 fixture 스키마와 검증.

코칭 대화 fixture는 DB에 시드되지 않는다(추출 입력으로만 사용).
gold_behaviors의 surface_forms는 같은 행동의 표기 대안 — 추출된 behavior가
그중 하나와 (정규화 후) 포함 관계면 그 행동을 잡은 것으로 본다.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.application.service.diary_generation_prompt import DIARY_EMOTIONS
from evals.fixture_schemas import FixtureMessage
from evals.validate_fixtures import FIXTURE_DIR, FixtureSet

COACHING_FIXTURES_FILENAME = "coaching_fixtures.jsonl"


class GoldBehavior(BaseModel):
    model_config = ConfigDict(extra="forbid")

    behavior_id: str = Field(min_length=1)
    surface_forms: list[str] = Field(min_length=1)
    polarity: Literal[1, -1]


class CoachingSessionFixture(BaseModel):
    """코칭 대화 1건 + 정답 신호 라벨.

    plausible_emotions: 이 대화에서 추출돼도 타당한 감정 집합(사람이 작성).
    gold_behaviors가 비어 있으면 "건강행동 언급 없음" 케이스 — 추출도 비어야 한다.
    """

    model_config = ConfigDict(extra="forbid")

    fixture_id: str = Field(min_length=1)
    device_id: str = Field(min_length=1)
    messages: list[FixtureMessage] = Field(min_length=1)
    plausible_emotions: list[str] = Field(min_length=1)
    gold_behaviors: list[GoldBehavior] = Field(default_factory=list)
    note: str | None = None


def load_coaching_fixtures(path: Path) -> tuple[list[CoachingSessionFixture], list[str]]:
    errors: list[str] = []
    rows: list[CoachingSessionFixture] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [], [f"{path}: 파일을 읽을 수 없습니다: {exc}"]
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            errors.append(f"{path}:{line_number}: 빈 JSONL 행은 허용되지 않습니다")
            continue
        try:
            rows.append(CoachingSessionFixture.model_validate(json.loads(line)))
        except json.JSONDecodeError as exc:
            errors.append(f"{path}:{line_number}: JSON 파싱 실패: {exc.msg}")
        except ValidationError as exc:
            errors.append(f"{path}:{line_number}: 스키마 오류: {exc}")
    return rows, errors


def validate_coaching_fixtures(
    rows: Sequence[CoachingSessionFixture], fixtures: FixtureSet, path: Path
) -> list[str]:
    errors: list[str] = []
    known_devices = set(fixtures.device_ids)
    seen_ids: set[str] = set()
    for row in rows:
        if row.fixture_id in seen_ids:
            errors.append(f"{path}: fixture_id 중복: {row.fixture_id}")
        seen_ids.add(row.fixture_id)
        if row.device_id not in known_devices:
            errors.append(f"{path}: {row.fixture_id}: 미등록 device_id: {row.device_id}")
        if not any(message.role == "user" for message in row.messages):
            errors.append(f"{path}: {row.fixture_id}: user 메시지가 최소 1개 필요합니다")
        unknown = sorted(set(row.plausible_emotions) - set(DIARY_EMOTIONS))
        if unknown:
            errors.append(
                f"{path}: {row.fixture_id}: 허용 어휘에 없는 감정: {', '.join(unknown)}"
            )
        seen_behaviors: set[str] = set()
        for behavior in row.gold_behaviors:
            if behavior.behavior_id in seen_behaviors:
                errors.append(
                    f"{path}: {row.fixture_id}: behavior_id 중복: {behavior.behavior_id}"
                )
            seen_behaviors.add(behavior.behavior_id)
            if any(not form.strip() for form in behavior.surface_forms):
                errors.append(
                    f"{path}: {row.fixture_id}: {behavior.behavior_id}: 빈 surface_form"
                )
    return errors


def default_coaching_path(fixture_dir: Path = FIXTURE_DIR) -> Path:
    return fixture_dir / COACHING_FIXTURES_FILENAME
