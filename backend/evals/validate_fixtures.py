"""평가 fixture(가상 사용자·Diary·Health) 검증기.

DB 접근 없이 파일 계약만 검사한다. seed 전에 반드시 통과해야 하며,
seed_fixtures도 같은 로더를 사용해 검증 실패 시 시드를 거부한다.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from evals.fixture_schemas import (
    EVAL_DEVICE_PREFIX,
    DiaryDayFixture,
    HealthDayFixture,
    VirtualUser,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures"
VIRTUAL_USERS_FILENAME = "virtual_users.json"
DIARY_FIXTURES_FILENAME = "diary_fixtures.jsonl"
HEALTH_FIXTURES_FILENAME = "health_fixtures.jsonl"


@dataclass
class FixtureSet:
    users: list[VirtualUser] = field(default_factory=list)
    diary_days: list[DiaryDayFixture] = field(default_factory=list)
    health_days: list[HealthDayFixture] = field(default_factory=list)

    @property
    def device_ids(self) -> list[str]:
        return [user.device_id for user in self.users]


def validate_fixture_dir(fixture_dir: Path) -> tuple[FixtureSet, list[str]]:
    """fixture 디렉토리 전체를 읽어 (파싱 결과, 오류 목록)을 반환한다."""
    errors: list[str] = []
    fixtures = FixtureSet()

    users_path = fixture_dir / VIRTUAL_USERS_FILENAME
    fixtures.users = _load_users(users_path, errors)
    known_devices = {user.device_id for user in fixtures.users}

    diary_path = fixture_dir / DIARY_FIXTURES_FILENAME
    fixtures.diary_days = _load_jsonl(diary_path, DiaryDayFixture, errors)
    health_path = fixture_dir / HEALTH_FIXTURES_FILENAME
    fixtures.health_days = _load_jsonl(health_path, HealthDayFixture, errors)

    _check_unique(
        errors, "fixture_id",
        [(day.fixture_id, diary_path) for day in fixtures.diary_days]
        + [(day.fixture_id, health_path) for day in fixtures.health_days],
    )
    _check_unique(
        errors, "chunk_id",
        [(chunk.chunk_id, diary_path) for day in fixtures.diary_days for chunk in day.gold_chunks],
    )
    _check_unique(
        errors, "(device_id, session_date)",
        [(f"{day.device_id}:{day.session_date}", diary_path) for day in fixtures.diary_days],
    )
    _check_unique(
        errors, "(device_id, record_date)",
        [(f"{day.device_id}:{day.record_date}", health_path) for day in fixtures.health_days],
    )

    for day in fixtures.diary_days:
        if day.device_id not in known_devices:
            errors.append(f"{diary_path}: {day.fixture_id}: 미등록 device_id: {day.device_id}")
        if not any(message.role == "user" for message in day.messages):
            errors.append(f"{diary_path}: {day.fixture_id}: user 메시지가 최소 1개 필요합니다")
    for day in fixtures.health_days:
        if day.device_id not in known_devices:
            errors.append(f"{health_path}: {day.fixture_id}: 미등록 device_id: {day.device_id}")
    return fixtures, errors


def load_fixture_set(fixture_dir: Path = FIXTURE_DIR) -> FixtureSet:
    """검증을 통과한 FixtureSet을 반환한다. 오류가 있으면 ValueError."""
    fixtures, errors = validate_fixture_dir(fixture_dir)
    if errors:
        raise ValueError("fixture 검증 실패:\n" + "\n".join(f"- {error}" for error in errors))
    return fixtures


def _load_users(path: Path, errors: list[str]) -> list[VirtualUser]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        errors.append(f"{path}: 파일을 읽을 수 없습니다: {exc}")
        return []
    except json.JSONDecodeError as exc:
        errors.append(f"{path}: JSON 파싱 실패: {exc.msg}")
        return []
    if not isinstance(raw, list):
        errors.append(f"{path}: 최상위는 JSON 배열이어야 합니다")
        return []
    users: list[VirtualUser] = []
    seen: set[str] = set()
    for index, item in enumerate(raw, start=1):
        try:
            user = VirtualUser.model_validate(item)
        except ValidationError as exc:
            errors.append(f"{path}: {index}번째 사용자 스키마 오류: {exc}")
            continue
        if not user.device_id.startswith(EVAL_DEVICE_PREFIX):
            errors.append(
                f"{path}: {user.device_id}: device_id는 '{EVAL_DEVICE_PREFIX}' 접두사가 필요합니다"
            )
        if user.device_id in seen:
            errors.append(f"{path}: device_id 중복: {user.device_id}")
        seen.add(user.device_id)
        users.append(user)
    return users


def _load_jsonl(path: Path, model: type, errors: list[str]) -> list:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        errors.append(f"{path}: 파일을 읽을 수 없습니다: {exc}")
        return []
    rows = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            errors.append(f"{path}:{line_number}: 빈 JSONL 행은 허용되지 않습니다")
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"{path}:{line_number}: JSON 파싱 실패: {exc.msg}")
            continue
        try:
            rows.append(model.model_validate(raw))
        except ValidationError as exc:
            errors.append(f"{path}:{line_number}: 스키마 오류: {exc}")
    return rows


def _check_unique(errors: list[str], label: str, keyed: Sequence[tuple[str, Path]]) -> None:
    seen: set[str] = set()
    for key, path in keyed:
        if key in seen:
            errors.append(f"{path}: {label} 중복: {key}")
        seen.add(key)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="평가 fixture 검증")
    parser.add_argument("--fixture-dir", type=Path, default=FIXTURE_DIR)
    args = parser.parse_args(argv)
    fixtures, errors = validate_fixture_dir(args.fixture_dir)
    if errors:
        print("fixture 검증 실패:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(
        f"fixture 검증 통과: 가상 사용자 {len(fixtures.users)}명, "
        f"diary {len(fixtures.diary_days)}일, health {len(fixtures.health_days)}일, "
        f"gold chunk {sum(len(day.gold_chunks) for day in fixtures.diary_days)}개"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
