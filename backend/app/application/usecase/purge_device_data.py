"""완전 삭제 — device_id에 귀속된 모든 서버 데이터를 영구 삭제(liv-zz Private-First 증명).

자식→부모 순서로 삭제해 FK 위반을 피한다. 단일 트랜잭션. 삭제 행수를 표 형태로 반환.
주의: health_daily_summaries / health_chunks / health_sessions 는 device_id 귀속이 아니라(레코드 날짜 키잉)
대상에서 제외한다(공용 건강 데이터, 개인 식별 아님).
"""

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models import (
    ChatMessageModel,
    ChatSessionModel,
    ClovaSettingModel,
    DiaryModel,
    EventChunkModel,
    GameProgressModel,
    QualitativeSignalModel,
    RewardInventoryModel,
    UserSessionModel,
)


class PurgeDeviceDataUseCase:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def execute(self, device_id: str) -> dict[str, int]:
        if not device_id or not device_id.strip():
            raise ValueError("device_id가 비어 있습니다.")

        # device의 chat_session id 집합 (자식 삭제용 서브쿼리)
        sessions_subq = sa.select(ChatSessionModel.id).where(
            ChatSessionModel.device_id == device_id
        )

        removed: dict[str, int] = {}

        # 1) 자식: event_chunks, chat_messages (세션 FK, ondelete 미설정 → 명시 선삭제)
        removed["event_chunks"] = (
            await self._db.execute(
                sa.delete(EventChunkModel).where(
                    EventChunkModel.chat_session_id.in_(sessions_subq)
                )
            )
        ).rowcount or 0
        removed["chat_messages"] = (
            await self._db.execute(
                sa.delete(ChatMessageModel).where(ChatMessageModel.session_id.in_(sessions_subq))
            )
        ).rowcount or 0

        # 2) diaries (chat_session_id FK 보유 → 세션보다 먼저)
        removed["diaries"] = (
            await self._db.execute(
                sa.delete(DiaryModel).where(DiaryModel.device_id == device_id)
            )
        ).rowcount or 0

        # 3) 부모: chat_sessions
        removed["chat_sessions"] = (
            await self._db.execute(
                sa.delete(ChatSessionModel).where(ChatSessionModel.device_id == device_id)
            )
        ).rowcount or 0

        # 4) 기타 device-keyed 독립 테이블
        for label, model in (
            ("qualitative_signals", QualitativeSignalModel),
            ("clova_settings", ClovaSettingModel),
            ("game_progress", GameProgressModel),
            ("reward_inventory", RewardInventoryModel),
            ("user_sessions", UserSessionModel),
        ):
            removed[label] = (
                await self._db.execute(
                    sa.delete(model).where(model.device_id == device_id)
                )
            ).rowcount or 0

        await self._db.commit()
        return removed
