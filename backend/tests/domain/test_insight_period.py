"""기간 경계 helper — 순수 함수 (G002-3, TDD).

ISO 주차(YYYY-Www)·월(YYYY-MM)을 [start, end] 날짜 범위로 변환하고,
문자열 파서가 잘못된 입력에 ValueError를 던지는지 검증한다.
"""

from datetime import date

import pytest

from app.domain.service.insight_period import (
    month_bounds,
    parse_iso_week,
    parse_month,
    week_bounds,
)


def test_week_bounds_is_monday_to_sunday():
    start, end = week_bounds(2026, 23)
    assert start.weekday() == 0  # 월요일
    assert end.weekday() == 6  # 일요일
    assert (end - start).days == 6


def test_week_bounds_contains_its_own_iso_date():
    # 2026-06-08의 ISO 주차로 경계를 구하면 그 날짜를 포함해야 함
    iso = date(2026, 6, 8).isocalendar()
    start, end = week_bounds(iso.year, iso.week)
    assert start <= date(2026, 6, 8) <= end


def test_month_bounds_full_month():
    assert month_bounds(2026, 6) == (date(2026, 6, 1), date(2026, 6, 30))


def test_month_bounds_december_year_boundary():
    assert month_bounds(2026, 12) == (date(2026, 12, 1), date(2026, 12, 31))


def test_month_bounds_february_non_leap():
    assert month_bounds(2026, 2) == (date(2026, 2, 1), date(2026, 2, 28))


def test_parse_iso_week_valid():
    assert parse_iso_week("2026-W23") == (2026, 23)


def test_parse_iso_week_invalid_raises():
    for bad in ["2026-23", "2026W23", "abcd-W01", "2026-W", ""]:
        with pytest.raises(ValueError):
            parse_iso_week(bad)


def test_parse_iso_week_nonexistent_week53_raises():
    # 2025는 52주만 있어 W53이 달력에 없음 → ValueError(라우터에서 400 변환)
    with pytest.raises(ValueError):
        parse_iso_week("2025-W53")
    # 2026은 53주가 존재하므로 통과해야 함(과잉 거부 방지)
    assert parse_iso_week("2026-W53") == (2026, 53)


def test_parse_month_valid():
    assert parse_month("2026-06") == (2026, 6)


def test_parse_month_invalid_raises():
    for bad in ["2026-13", "2026/06", "2026-6-1", "abcd-06", ""]:
        with pytest.raises(ValueError):
            parse_month(bad)
