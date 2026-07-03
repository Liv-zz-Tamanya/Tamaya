"""CLOVA 연결 테스터 구현 — real 최소 호출 / mock 형식 판정.

real 모드는 후보 키로 토큰 1개짜리 최소 호출을 시도해 성공 여부를 본다.
mock 모드는 네트워크 없이 '비어있지 않으면 ok'로 판정한다. 어떤 경우에도 키를
로그/예외 메시지로 노출하지 않는다(예외는 삼키고 bool만 반환).
"""

import logging

from openai import AsyncOpenAI

from app.application.service.clova_connection_tester import ClovaConnectionTester
from app.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class ClovaConnectionTesterImpl(ClovaConnectionTester):
    def __init__(self, mock: bool | None = None) -> None:
        self._mock = mock if mock is not None else settings.clova_mock_mode

    async def test_connection(self, api_key: str) -> bool:
        key = (api_key or "").strip()
        if not key:
            return False
        if self._mock:
            return True  # mock: 실검증 불가 — 비어있지 않은 키면 통과
        try:
            client = AsyncOpenAI(api_key=key, base_url=settings.clova_base_url)
            await client.chat.completions.create(
                model=settings.clova_model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
            return True
        except Exception:
            # 키가 예외 메시지에 섞일 수 있으므로 메시지를 로깅하지 않는다.
            logger.warning("CLOVA 연결 테스트 실패 (키 미기록)")
            return False
