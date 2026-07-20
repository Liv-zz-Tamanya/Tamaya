from __future__ import annotations

import json
from pathlib import Path

from evals.validate_dataset import registered_tools_by_mode, validate_dataset_files


def _write_jsonl(path: Path, *rows: dict) -> Path:
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    return path


def _case(**overrides) -> dict:
    case = {
        "id": "case-1",
        "mode": "diary",
        "input": "지난 기록을 찾아줘",
        "history": [],
        "expected_tools": ["search_diary_memories"],
        "forbidden_tools": ["search_health_records"],
        "expected_guardrail": "PASS",
        "expected_document_ids": [],
        "category": "test",
        "note": None,
    }
    case.update(overrides)
    return case


def test_registered_tools_match_current_mode_policy():
    assert registered_tools_by_mode() == {
        "diary": {"search_diary_memories", "search_health_records"},
        "health": {"search_health_records"},
        "coaching": set(),
    }


def test_validator_accepts_a_valid_dataset(tmp_path: Path):
    path = _write_jsonl(tmp_path / "valid.jsonl", _case())

    assert validate_dataset_files([path]) == []


def test_validator_reports_parsing_schema_and_empty_input_errors(tmp_path: Path):
    path = tmp_path / "invalid.jsonl"
    path.write_text(
        "not-json\n"
        + json.dumps(_case(id="bad-mode", mode="unknown"))
        + "\n"
        + json.dumps(_case(id="blank-input", input="   ")),
        encoding="utf-8",
    )

    errors = validate_dataset_files([path])

    assert any("JSON 파싱 실패" in error for error in errors)
    assert any("스키마 오류" in error for error in errors)
    assert any("input은 비어 있을 수 없습니다" in error for error in errors)


def test_validator_reports_duplicate_overlap_unknown_and_mode_scope(tmp_path: Path):
    path = _write_jsonl(
        tmp_path / "invalid-tools.jsonl",
        _case(),
        _case(
            expected_tools=["search_health_records", "invented_tool"],
            forbidden_tools=["search_health_records"],
        ),
        _case(
            id="health-diary-tool",
            mode="health",
            expected_tools=["search_diary_memories"],
            forbidden_tools=[],
        ),
    )

    errors = validate_dataset_files([path])

    assert any("id 중복" in error for error in errors)
    assert any("expected/forbidden tool 중복" in error for error in errors)
    assert any("등록되지 않은 tool: invented_tool" in error for error in errors)
    assert any("health mode에서 사용할 수 없는 expected tool" in error for error in errors)
