"""데모 라이프로그 시드 — demo 프로파일로 웰빙 화면을 수동 확인한다.

seed_demo_signals.py 선례를 따른다. 전제: Postgres 기동 + 마이그레이션 적용
(make up && make migrate). 실제 repo/모델을 사용하며, 재실행해도 안전하다
(수면·일기는 upsert, 걸음은 source_hash로 중복 스킵).

사용:  uv run python scripts/seed_demo_lifelog.py [device_id]
프런트의 device_id와 일치해야 화면에 표시됨(localStorage 'tamaya.deviceId').
"""

import asyncio
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.domain.model.diary import Diary
from app.domain.model.emotion import Emotion
from app.domain.model.health_record import HealthDailySummary
from app.domain.model.sleep_record import SleepRecord
from app.infrastructure.config.database import async_session_factory, engine
from app.infrastructure.persistence.diary_repository_impl import DiaryRepositoryImpl
from app.infrastructure.persistence.health_record_repository_impl import (
    HealthRecordRepositoryImpl,
)
from app.infrastructure.persistence.sleep_record_repository_impl import (
    SleepRecordRepositoryImpl,
)
from evals.lifelog_generator import PROFILES, generate_lifelog

DEVICE = sys.argv[1] if len(sys.argv) > 1 else "dev-demo-real"


async def main() -> None:
    fixture = generate_lifelog(PROFILES["demo"], DEVICE, end_date=date.today())

    async with async_session_factory() as session:
        sleep_repo = SleepRecordRepositoryImpl(session)
        await sleep_repo.upsert_all(
            [
                SleepRecord(
                    device_id=DEVICE,
                    record_date=date.fromisoformat(row["record_date"]),
                    duration_minutes=row["duration_minutes"],
                )
                for row in fixture.sleep_records
            ]
        )

        health_repo = HealthRecordRepositoryImpl(session)
        inserted_steps = 0
        for row in fixture.health_summaries:
            if await health_repo.source_hash_exists(DEVICE, row["source_hash"]):
                continue
            await health_repo.save(
                HealthDailySummary(
                    device_id=DEVICE,
                    record_date=date.fromisoformat(row["record_date"]),
                    **{k: v for k, v in row.items() if k != "record_date"},
                )
            )
            inserted_steps += 1

        diary_repo = DiaryRepositoryImpl(session)
        for row in fixture.diaries:
            await diary_repo.save(
                Diary(
                    device_id=DEVICE,
                    diary_date=date.fromisoformat(row["diary_date"]),
                    title=row["title"],
                    content=row["content"],
                    emotion=Emotion(row["emotion"]),
                    satisfaction=row["satisfaction"],
                    satisfaction_estimated=row["satisfaction_estimated"],
                    keywords=row["keywords"],
                )
            )

    await engine.dispose()
    print(
        f"seeded demo lifelog · device={DEVICE} · "
        f"sleep={len(fixture.sleep_records)} steps={inserted_steps}(new) "
        f"diaries={len(fixture.diaries)} · {fixture.meta['start_date']}~{fixture.meta['end_date']}"
    )


if __name__ == "__main__":
    asyncio.run(main())
