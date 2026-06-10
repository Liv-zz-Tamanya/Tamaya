"""CLOVA 설정 리포지토리 인터페이스 — device_id 키잉(원문 키 미보관)."""

from abc import ABC, abstractmethod

from app.domain.model.clova_setting import ClovaSetting


class ClovaSettingRepository(ABC):
    @abstractmethod
    async def get(self, device_id: str) -> ClovaSetting | None: ...

    @abstractmethod
    async def upsert(self, setting: ClovaSetting) -> None: ...
