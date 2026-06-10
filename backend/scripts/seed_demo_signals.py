"""데모 정성신호 시드 — insights 화면에 데이터가 보이도록 현재 ISO 주차에 신호를 넣는다.

전제: Postgres 기동 + 마이그레이션 적용(make up && make migrate). 실제 repo/모델을 사용한다.
사용:  uv run python scripts/seed_demo_signals.py [device_id]
프런트의 device_id와 일치해야 insights에 표시됨(브라우저 localStorage 'tamaya.deviceId' 참고).
"""

import asyncio
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

# scripts/ 에서 직접 실행해도 app 패키지를 찾도록 backend 루트를 경로에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.domain.model.emotion import Emotion
from app.domain.model.qualitative_signal import BehaviorMention, QualitativeSignal
from app.infrastructure.config.database import async_session_factory, engine
from app.infrastructure.persistence.qualitative_signal_repository_impl import (
    QualitativeSignalRepositoryImpl,
)

DEVICE = sys.argv[1] if len(sys.argv) > 1 else "dev-demo-real"


async def main() -> None:
    today = date.today()
    monday = today - timedelta(days=today.weekday())  # 이번 주 월요일
    seeds = [
        (Emotion.HAPPY, [("운동", 1), ("수면", 1)], monday),
        (Emotion.GRATEFUL, [("산책", 1)], monday + timedelta(days=1)),
        (Emotion.CALM, [("식사", 1)], monday + timedelta(days=2)),
        (Emotion.TIRED, [("식사거름", -1)], monday + timedelta(days=3)),
        (Emotion.HAPPY, [("운동", 1)], monday + timedelta(days=4)),
    ]
    async with async_session_factory() as session:
        repo = QualitativeSignalRepositoryImpl(session)
        for emotion, mentions, recorded in seeds:
            signal = QualitativeSignal(
                emotion=emotion,
                behavior_mentions=tuple(BehaviorMention(b, p) for b, p in mentions),
                recorded_date=recorded,
            )
            await repo.save(DEVICE, uuid.uuid4(), signal)
    await engine.dispose()
    print(f"seeded {len(seeds)} signals · device={DEVICE} · week of {monday.isoformat()}")


if __name__ == "__main__":
    asyncio.run(main())
