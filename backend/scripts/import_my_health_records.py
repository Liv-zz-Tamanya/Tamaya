"""나의건강기록 내보내기 수입 CLI — 수면·걸음수·진료이력을 로컬 DB에 upsert한다.

    uv run python -m scripts.import_my_health_records scripts/sample_my_health_records.json \
        --device-id nick-테스트

입력은 나의건강기록 화면의 한국어 컬럼명을 그대로 쓰는 JSON이다(샘플 파일 참고):

    {
      "sleep":  [{"측정일자": "2026-07-01", "측정값": "7시간44분"}, ...],
      "steps":  [{"측정일자": "2026-06-27", "측정값": "6,764걸음"}, ...],
      "medical_visits": [
        {"진료일자": "2026-05-04", "진료구분": "처방 조제", "진료기관": "강변그랜드약국",
         "방문위치": "광진구 광나루로56길", "방문일수": 1, "처방횟수": 1, "투약일수": 2}
      ]
    }

- 재실행 멱등: 수면 (device, 날짜), 진료 (device, 날짜, 기관, 구분), 걸음 (device, 날짜)
  UNIQUE 기준 upsert라 같은 파일을 여러 번 넣어도 중복이 생기지 않는다.
- 걸음수는 기존 health_daily_summaries에 upsert된다(걸음 외 필드는 기본값 유지).
- 검증 오류가 하나라도 있으면 아무것도 쓰지 않고 전체 목록을 출력한 뒤 종료한다.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.domain.model.medical_visit import MedicalVisit, MedicalVisitType
from app.domain.model.sleep_record import MAX_SLEEP_MINUTES, SleepRecord
from app.infrastructure.config.settings import settings
from app.infrastructure.persistence.medical_visit_repository_impl import (
    MedicalVisitRepositoryImpl,
)
from app.infrastructure.persistence.models import HealthDailySummaryModel
from app.infrastructure.persistence.sleep_record_repository_impl import (
    SleepRecordRepositoryImpl,
)

_DURATION_PATTERN = re.compile(r"^\s*(?:(\d+)\s*시간)?\s*(?:(\d+)\s*분)?\s*$")


def parse_sleep_duration(text: str) -> int:
    """'7시간44분' / '6시간 48분' / '44분' / '7시간' → 분. 계약 밖 입력은 ValueError."""
    match = _DURATION_PATTERN.match(text)
    if not match or (match.group(1) is None and match.group(2) is None):
        raise ValueError(f"수면 측정값 형식이 아님: {text!r}")
    minutes = int(match.group(1) or 0) * 60 + int(match.group(2) or 0)
    if not 0 < minutes <= MAX_SLEEP_MINUTES:
        raise ValueError(f"수면 시간이 범위 밖: {text!r}")
    return minutes


def parse_step_count(text: str | int) -> int:
    """'6,764걸음' / '6764' / 6764 → 정수 걸음수."""
    if isinstance(text, int) and not isinstance(text, bool):
        value = text
    else:
        normalized = str(text).replace(",", "").replace("걸음", "").strip()
        if not normalized.isdigit():
            raise ValueError(f"걸음수 형식이 아님: {text!r}")
        value = int(normalized)
    if value < 0:
        raise ValueError(f"걸음수는 음수일 수 없음: {text!r}")
    return value


def _parse_date(text: str) -> date:
    try:
        return date.fromisoformat(str(text).strip())
    except ValueError as exc:
        raise ValueError(f"날짜 형식이 아님(YYYY-MM-DD): {text!r}") from exc


@dataclass
class ImportPayload:
    sleep: list[SleepRecord] = field(default_factory=list)
    steps: list[tuple[date, int]] = field(default_factory=list)
    visits: list[MedicalVisit] = field(default_factory=list)


def convert_payload(raw: dict, device_id: str) -> tuple[ImportPayload, list[str]]:
    """한국어 키 JSON을 도메인 객체로 변환한다. (payload, 오류 목록) 반환."""
    errors: list[str] = []
    payload = ImportPayload()

    for index, row in enumerate(raw.get("sleep") or [], start=1):
        try:
            payload.sleep.append(
                SleepRecord(
                    device_id=device_id,
                    record_date=_parse_date(row["측정일자"]),
                    duration_minutes=parse_sleep_duration(row["측정값"]),
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"sleep[{index}]: {exc}")

    for index, row in enumerate(raw.get("steps") or [], start=1):
        try:
            payload.steps.append(
                (_parse_date(row["측정일자"]), parse_step_count(row["측정값"]))
            )
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"steps[{index}]: {exc}")

    for index, row in enumerate(raw.get("medical_visits") or [], start=1):
        try:
            payload.visits.append(
                MedicalVisit(
                    device_id=device_id,
                    visit_date=_parse_date(row["진료일자"]),
                    visit_type=MedicalVisitType(str(row["진료구분"]).strip()),
                    institution=str(row["진료기관"]).strip(),
                    location=str(row["방문위치"]).strip() if row.get("방문위치") else None,
                    visit_days=int(row.get("방문일수", 1)),
                    prescription_count=int(row.get("처방횟수", 0)),
                    medication_days=int(row.get("투약일수", row.get("투약(요양)일수", 0))),
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"medical_visits[{index}]: {exc}")

    _check_duplicates(payload, errors)
    return payload, errors


def _check_duplicates(payload: ImportPayload, errors: list[str]) -> None:
    seen_sleep: set[date] = set()
    for record in payload.sleep:
        if record.record_date in seen_sleep:
            errors.append(f"sleep: 측정일자 중복 {record.record_date}")
        seen_sleep.add(record.record_date)
    seen_steps: set[date] = set()
    for record_date, _ in payload.steps:
        if record_date in seen_steps:
            errors.append(f"steps: 측정일자 중복 {record_date}")
        seen_steps.add(record_date)
    seen_visits: set[tuple] = set()
    for visit in payload.visits:
        key = (visit.visit_date, visit.institution, visit.visit_type)
        if key in seen_visits:
            errors.append(f"medical_visits: 중복 행 {key}")
        seen_visits.add(key)


async def upsert_steps(session, device_id: str, steps: list[tuple[date, int]]) -> int:
    """걸음수를 health_daily_summaries에 upsert. 걸음 외 필드는 기본값/기존값 유지."""
    if not steps:
        return 0
    statement = insert(HealthDailySummaryModel).values(
        [
            {
                "device_id": device_id,
                "record_date": record_date,
                "step_count": count,
                # 배치 dedupe용 해시 — 날짜당 결정론 값이라 재수입 시 같은 행으로 수렴
                "source_hash": f"myhr-{record_date.isoformat()}",
                "created_at": datetime.now(),
            }
            for record_date, count in steps
        ]
    )
    statement = statement.on_conflict_do_update(
        constraint="uq_health_daily_device_record_date",
        set_={
            "step_count": statement.excluded.step_count,
            "source_hash": statement.excluded.source_hash,
        },
    )
    await session.execute(statement)
    await session.commit()
    return len(steps)


async def run_import(database_url: str, device_id: str, raw: dict) -> dict[str, int]:
    payload, errors = convert_payload(raw, device_id)
    if errors:
        raise ValueError("입력 검증 실패:\n" + "\n".join(f"- {error}" for error in errors))
    engine = create_async_engine(database_url)
    try:
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            sleep_count = await SleepRecordRepositoryImpl(session).upsert_all(payload.sleep)
            visit_count = await MedicalVisitRepositoryImpl(session).upsert_all(payload.visits)
            step_count = await upsert_steps(session, device_id, payload.steps)
        return {"sleep": sleep_count, "steps": step_count, "medical_visits": visit_count}
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="나의건강기록 JSON 수입")
    parser.add_argument("file", type=Path, help="수입할 JSON 파일")
    parser.add_argument("--device-id", required=True, help="데이터를 귀속시킬 device_id")
    parser.add_argument("--database-url", default=None)
    args = parser.parse_args(argv)
    database_url = args.database_url or settings.database_url
    try:
        raw = json.loads(args.file.read_text(encoding="utf-8"))
        counts = asyncio.run(run_import(database_url, args.device_id, raw))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"수입할 수 없습니다: {exc}", file=sys.stderr)
        return 2
    print(
        f"수입 완료 (device={args.device_id}): "
        f"수면 {counts['sleep']}행, 걸음 {counts['steps']}행, 진료 {counts['medical_visits']}행 (upsert)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
