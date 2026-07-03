"""CLOVA 연결 테스터 — mock 동작 (G003-2, TDD).

mock 모드에서는 실제 호출 없이 '비어있지 않은 키면 ok'로 판정한다(실검증 불가).
빈 키는 어떤 모드에서도 False.
"""

from app.infrastructure.external.clova_connection_tester_impl import ClovaConnectionTesterImpl


async def test_mock_mode_nonempty_key_ok():
    tester = ClovaConnectionTesterImpl(mock=True)
    assert await tester.test_connection("user-supplied-key") is True


async def test_empty_key_is_not_ok():
    tester = ClovaConnectionTesterImpl(mock=True)
    assert await tester.test_connection("") is False
    assert await tester.test_connection("   ") is False
