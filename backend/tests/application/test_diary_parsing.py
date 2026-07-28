"""parse_satisfaction 헬퍼 — '모름'과 '중립 50'의 구분을 검증한다 (PR-A2)."""

from pathlib import Path

from app.application.service.diary_parsing import parse_satisfaction

APP_ROOT = Path(__file__).resolve().parents[2] / "app"


def test_parse_valid_int():
    assert parse_satisfaction(72) == (72, False)


def test_parse_null():
    assert parse_satisfaction(None) == (50, True)


def test_parse_missing_key():
    # 호출부 계약: 기본값 인자 없는 .get("satisfaction") → None → estimated
    assert parse_satisfaction({}.get("satisfaction")) == (50, True)


def test_parse_invalid_type():
    assert parse_satisfaction("높음") == (50, True)


def test_parse_bool_is_estimated():
    # int(True) == 1 로 오염되지 않아야 한다
    assert parse_satisfaction(True) == (50, True)


def test_parse_numeric_string():
    # LLM이 "72"처럼 문자열 숫자를 내는 경우는 유효 값으로 본다
    assert parse_satisfaction("72") == (72, False)


def test_parse_out_of_range():
    assert parse_satisfaction(150) == (100, False)
    assert parse_satisfaction(-10) == (0, False)


def test_no_default_arg_pattern():
    """`.get("satisfaction", 50)` 패턴이 남아 있으면 키 누락이 은폐된다."""
    offenders = [
        str(path)
        for path in APP_ROOT.rglob("*.py")
        if '.get("satisfaction",' in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_both_usecases_use_helper():
    for name in ("send_message.py", "finalize_diary.py"):
        source = (APP_ROOT / "application" / "usecase" / name).read_text(encoding="utf-8")
        assert "parse_satisfaction" in source, f"{name}이 공통 헬퍼를 쓰지 않습니다"
