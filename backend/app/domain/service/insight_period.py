"""기간 경계 helper — 순수 함수(외부 의존 0).

ISO 주차(YYYY-Www)·월(YYYY-MM) 문자열을 (year, week|month) 튜플로 파싱하고,
[start, end] 양끝 포함 날짜 범위로 변환한다. 스코어러처럼 결정론·단위테스트 가능.
"""

import re
from datetime import date, timedelta

_ISO_WEEK_RE = re.compile(r"^(\d{4})-W(\d{2})$")
_MONTH_RE = re.compile(r"^(\d{4})-(\d{2})$")


def parse_iso_week(value: str) -> tuple[int, int]:
    """'YYYY-Www' → (year, week). 형식·범위 위반 시 ValueError."""
    match = _ISO_WEEK_RE.match(value)
    if not match:
        raise ValueError(f"잘못된 ISO 주차 형식: {value!r} (예: 2026-W23)")
    year, week = int(match.group(1)), int(match.group(2))
    if not 1 <= week <= 53:
        raise ValueError(f"주차는 1~53 범위여야 함: {week}")
    # 52주만 있는 해의 W53처럼 실제 달력에 없는 주차를 여기서 걸러야
    # 라우터의 try/except가 받아 400으로 응답한다(usecase에서 터지면 500).
    try:
        date.fromisocalendar(year, week, 1)
    except ValueError as exc:
        raise ValueError(f"{year}년에 존재하지 않는 ISO 주차: {week}") from exc
    return year, week


def parse_month(value: str) -> tuple[int, int]:
    """'YYYY-MM' → (year, month). 형식·범위 위반 시 ValueError."""
    match = _MONTH_RE.match(value)
    if not match:
        raise ValueError(f"잘못된 월 형식: {value!r} (예: 2026-06)")
    year, month = int(match.group(1)), int(match.group(2))
    if not 1 <= month <= 12:
        raise ValueError(f"월은 1~12 범위여야 함: {month}")
    return year, month


def week_bounds(year: int, week: int) -> tuple[date, date]:
    """ISO 주차의 월요일~일요일 [start, end]."""
    start = date.fromisocalendar(year, week, 1)  # 월요일
    end = date.fromisocalendar(year, week, 7)  # 일요일
    return start, end


def month_bounds(year: int, month: int) -> tuple[date, date]:
    """해당 월의 1일~말일 [start, end]."""
    start = date(year, month, 1)
    if month == 12:
        end = date(year, 12, 31)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    return start, end
