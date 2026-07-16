"""코칭 CLOVA 클라이언트 — 건강냥 밤 코칭 톤 (G004-1).

CoachingAiService 구현. mock 모드는 네트워크 없이 canned 밤 코칭 응답을 돌려주고,
real 모드는 코칭 시스템 프롬프트(+선택적 persona)로 CLOVA를 호출한다.
BYOK: 요청별 api_key/mock override(미지정 시 settings 기본값, 비파괴).
"""

import random

from openai import AsyncOpenAI

from app.application.service.coaching_ai_service import CoachingAiService
from app.application.service.coaching_prompt import build_coaching_system_prompt
from app.domain.model.chat_message import ChatMessage
from app.infrastructure.config.settings import settings
from app.infrastructure.external.clova_client import _resolve_client_api_key

# 건강냥 밤 코칭 mock 응답 — 공감 우선, 지시·진단 없음, 작은 넛지.
_MOCK_COACHING_RESPONSES = [
    "오늘 하루도 버텨줘서 고마워요. 지금 마음은 좀 어때요?",
    "그런 날도 있죠. 너무 자책하지 말고, 오늘 밤은 조금 일찍 쉬어볼까요?",
    "이야기 들려줘서 고마워요. 내일은 아주 작은 것 하나만 같이 해봐요.",
    "괜찮아요, 천천히 가도 돼요. 오늘 잘한 일 하나만 떠올려볼래요?",
    "고단했겠다. 따뜻한 물 한 잔 마시고 잠깐 숨 돌려요.",
]


class CoachingClovaClient(CoachingAiService):
    def __init__(self, api_key: str | None = None, mock: bool | None = None) -> None:
        self._mock = mock if mock is not None else settings.clova_mock_mode
        self._client = AsyncOpenAI(
            api_key=_resolve_client_api_key(api_key, self._mock),
            base_url=settings.clova_base_url,
        )

    async def coach(self, messages: list[ChatMessage], persona: str | None = None) -> str:
        if self._mock:
            return random.choice(_MOCK_COACHING_RESPONSES)

        system_prompt = build_coaching_system_prompt(persona=persona)

        api_messages = [{"role": "system", "content": system_prompt}]
        for m in messages:
            if m.role != "system":
                api_messages.append({"role": m.role, "content": m.content})

        response = await self._client.chat.completions.create(
            model=settings.clova_model,
            messages=api_messages,
            temperature=0.6,
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
