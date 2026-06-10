"""CLOVA 설정 SQLAlchemy 리포지토리 — device_id upsert(원문 키 미보관).

저장 값은 마스킹된 프리뷰뿐이다. 동일 device_id 재저장 시 갱신한다.
"""

import uuid

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.model.clova_setting import ClovaSetting
from app.domain.repository.clova_setting_repository import ClovaSettingRepository
from app.infrastructure.persistence.models import ClovaSettingModel


class ClovaSettingRepositoryImpl(ClovaSettingRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get(self, device_id: str) -> ClovaSetting | None:
        stmt = sa.select(ClovaSettingModel).where(ClovaSettingModel.device_id == device_id)
        result = await self._db.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return ClovaSetting(
            device_id=model.device_id,
            masked_key=model.masked_key,
            has_key=model.has_key,
        )

    async def upsert(self, setting: ClovaSetting) -> None:
        try:
            stmt = sa.select(ClovaSettingModel).where(
                ClovaSettingModel.device_id == setting.device_id
            )
            result = await self._db.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                model = ClovaSettingModel(id=uuid.uuid4(), device_id=setting.device_id)
                self._db.add(model)
            model.masked_key = setting.masked_key
            model.has_key = setting.has_key
            await self._db.commit()
        except Exception:
            await self._db.rollback()
            raise
