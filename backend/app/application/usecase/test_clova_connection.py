"""CLOVA 연결 테스트 usecase — 테스터 호출 오케스트레이션."""

from app.application.service.clova_connection_tester import ClovaConnectionTester


class TestClovaConnectionUseCase:
    def __init__(self, tester: ClovaConnectionTester) -> None:
        self._tester = tester

    async def execute(self, api_key: str) -> bool:
        return await self._tester.test_connection(api_key)
