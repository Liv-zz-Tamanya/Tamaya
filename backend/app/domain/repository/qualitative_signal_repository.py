"""정성신호 리포지토리 인터페이스 — device_id 키잉(User 테이블 없음).

저장(추출 슬라이스)과 기간 조회(주/월 인사이트 슬라이스)를 함께 정의한다.
session_id는 coaching_sessions 테이블 부재로 FK 없이 단순 UUID로 다룬다.
"""

from abc import ABC, abstractmethod
from datetime import date
from uuid import UUID

from app.domain.model.qualitative_signal import QualitativeSignal


class QualitativeSignalRepository(ABC):
    @abstractmethod
    async def save(self, device_id: str, session_id: UUID, signal: QualitativeSignal) -> None: ...

    @abstractmethod
    async def find_by_date_range(
        self, device_id: str, start: date, end: date
    ) -> list[QualitativeSignal]: ...
