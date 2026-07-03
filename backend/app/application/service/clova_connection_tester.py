"""CLOVA 연결 테스터 인터페이스 — 키 유효성 단일 메서드.

설정 화면의 '연결 테스트'용. real 구현은 최소 호출로 키를 검증하고,
mock 구현은 형식상 비어있지 않으면 ok로 본다(실검증 불가).
"""

from abc import ABC, abstractmethod


class ClovaConnectionTester(ABC):
    @abstractmethod
    async def test_connection(self, api_key: str) -> bool:
        """주어진 키로 CLOVA 연결이 가능한지 반환한다. 키는 로깅하지 않는다."""
        ...
