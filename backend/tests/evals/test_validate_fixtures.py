"""평가 fixture 검증기 테스트."""

import json
from pathlib import Path

from evals.validate_fixtures import FIXTURE_DIR, validate_fixture_dir

VALID_USER = {
    "device_id": "eval-user-test",
    "name": "테스트",
    "persona": "테스트용 가상 사용자",
}
VALID_DIARY = {
    "fixture_id": "diary-test-0601",
    "device_id": "eval-user-test",
    "session_date": "2026-06-01",
    "messages": [
        {"role": "user", "content": "오늘 공원에 갔어."},
        {"role": "assistant", "content": "공원 산책 좋았겠다!"},
    ],
    "gold_chunks": [
        {
            "chunk_id": "test-0601-park",
            "text": "공원에 갔다.",
            "tags": ["공원"],
            "event_type": "personal",
            "who": None,
            "where": "공원",
            "when": "오늘",
        }
    ],
}
VALID_HEALTH = {
    "fixture_id": "health-test-0601",
    "device_id": "eval-user-test",
    "record_date": "2026-06-01",
    "text": "2026-06-01에 5,000걸음을 걸었어.",
    "data_types": ["steps"],
}


def _write_fixture_dir(
    tmp_path: Path,
    users: list[dict] | None = None,
    diary: list[dict] | None = None,
    health: list[dict] | None = None,
) -> Path:
    (tmp_path / "virtual_users.json").write_text(
        json.dumps(users if users is not None else [VALID_USER], ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "diary_fixtures.jsonl").write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in (diary if diary is not None else [VALID_DIARY])),
        encoding="utf-8",
    )
    (tmp_path / "health_fixtures.jsonl").write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in (health if health is not None else [VALID_HEALTH])),
        encoding="utf-8",
    )
    return tmp_path


def test_shipped_fixtures_are_valid():
    # 저장소에 커밋된 실제 fixture가 항상 유효해야 CI가 회귀를 잡는다
    fixtures, errors = validate_fixture_dir(FIXTURE_DIR)
    assert errors == []
    assert len(fixtures.users) >= 2
    assert len(fixtures.diary_days) >= 8
    assert len(fixtures.health_days) >= 4
    assert sum(len(day.gold_chunks) for day in fixtures.diary_days) >= 15


def test_shipped_fixtures_cover_empty_health_user():
    # 건강 데이터가 전혀 없는 가상 사용자가 최소 1명 있어야 빈 검색 케이스를 만들 수 있다
    fixtures, _ = validate_fixture_dir(FIXTURE_DIR)
    devices_with_health = {day.device_id for day in fixtures.health_days}
    assert any(user.device_id not in devices_with_health for user in fixtures.users)


def test_valid_minimal_fixture_dir_passes(tmp_path):
    _, errors = validate_fixture_dir(_write_fixture_dir(tmp_path))
    assert errors == []


def test_unknown_device_id_is_reported(tmp_path):
    diary = [dict(VALID_DIARY, device_id="eval-user-ghost")]
    _, errors = validate_fixture_dir(_write_fixture_dir(tmp_path, diary=diary))
    assert any("미등록 device_id" in error for error in errors)


def test_non_eval_device_prefix_is_reported(tmp_path):
    users = [dict(VALID_USER, device_id="real-user-1")]
    diary = [dict(VALID_DIARY, device_id="real-user-1")]
    health = [dict(VALID_HEALTH, device_id="real-user-1")]
    _, errors = validate_fixture_dir(_write_fixture_dir(tmp_path, users=users, diary=diary, health=health))
    assert any("접두사" in error for error in errors)


def test_duplicate_chunk_id_is_reported(tmp_path):
    second = dict(VALID_DIARY, fixture_id="diary-test-0602", session_date="2026-06-02")
    _, errors = validate_fixture_dir(_write_fixture_dir(tmp_path, diary=[VALID_DIARY, second]))
    assert any("chunk_id 중복" in error for error in errors)


def test_duplicate_device_session_date_is_reported(tmp_path):
    second = dict(VALID_DIARY, fixture_id="diary-test-dup", gold_chunks=[])
    _, errors = validate_fixture_dir(_write_fixture_dir(tmp_path, diary=[VALID_DIARY, second]))
    assert any("(device_id, session_date) 중복" in error for error in errors)


def test_duplicate_fixture_id_across_files_is_reported(tmp_path):
    health = [dict(VALID_HEALTH, fixture_id=VALID_DIARY["fixture_id"])]
    _, errors = validate_fixture_dir(_write_fixture_dir(tmp_path, health=health))
    assert any("fixture_id 중복" in error for error in errors)


def test_diary_without_user_message_is_reported(tmp_path):
    diary = [dict(VALID_DIARY, messages=[{"role": "assistant", "content": "안녕!"}], gold_chunks=[])]
    _, errors = validate_fixture_dir(_write_fixture_dir(tmp_path, diary=diary))
    assert any("user 메시지" in error for error in errors)


def test_invalid_event_type_is_schema_error(tmp_path):
    chunk = dict(VALID_DIARY["gold_chunks"][0], event_type="unknown_type")
    diary = [dict(VALID_DIARY, gold_chunks=[chunk])]
    _, errors = validate_fixture_dir(_write_fixture_dir(tmp_path, diary=diary))
    assert any("스키마 오류" in error for error in errors)


def test_invalid_health_data_type_is_schema_error(tmp_path):
    health = [dict(VALID_HEALTH, data_types=["sleep"])]
    _, errors = validate_fixture_dir(_write_fixture_dir(tmp_path, health=health))
    assert any("스키마 오류" in error for error in errors)


def test_empty_jsonl_row_is_reported(tmp_path):
    path = _write_fixture_dir(tmp_path)
    diary_path = path / "diary_fixtures.jsonl"
    diary_path.write_text(diary_path.read_text(encoding="utf-8") + "\n\n", encoding="utf-8")
    _, errors = validate_fixture_dir(path)
    assert any("빈 JSONL 행" in error for error in errors)
