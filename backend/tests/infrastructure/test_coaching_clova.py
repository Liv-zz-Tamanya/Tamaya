"""코칭 CLOVA 클라이언트 — mock 동작 + BYOK 속성 (G004-1, TDD).

mock 모드는 네트워크 없이 건강냥 밤 코칭 톤의 canned 응답을 돌려준다(대화 흐름 보호).
per-request api_key/mock override가 settings를 건드리지 않고 반영되는지 확인한다.
"""

from app.application.service.coaching_ai_service import CoachingAiService
from app.application.service.coaching_prompt import build_coaching_system_prompt
from app.infrastructure.config.settings import settings
from app.infrastructure.external.coaching_clova import CoachingClovaClient


async def test_mock_returns_nonempty_coaching_reply():
    client = CoachingClovaClient(mock=True)
    reply = await client.coach([])
    assert isinstance(reply, str)
    assert reply.strip() != ""


def test_is_coaching_ai_service():
    assert isinstance(CoachingClovaClient(), CoachingAiService)


def test_per_request_key_without_touching_settings():
    original_key = settings.clova_api_key
    client = CoachingClovaClient(api_key="user-key", mock=False)
    assert client._mock is False
    assert client._client.api_key == "user-key"
    assert settings.clova_api_key == original_key


def test_coaching_prompt_builder_adds_persona_without_changing_base_policy():
    base = build_coaching_system_prompt()
    with_persona = build_coaching_system_prompt("부모님")

    assert "건강냥" in base
    assert "진단·처방·약 권유는 절대 하지 않아" in base
    assert "부모님" not in base
    assert "부모님" in with_persona
    assert base in with_persona
