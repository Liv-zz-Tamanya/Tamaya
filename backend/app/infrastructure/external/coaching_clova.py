"""코칭 CLOVA 클라이언트 — 건강냥 밤 코칭 톤 (G004-1).

CoachingAiService 구현. mock 모드는 네트워크 없이 canned 밤 코칭 응답을 돌려주고,
real 모드는 코칭 시스템 프롬프트(+선택적 persona)로 CLOVA를 호출한다.
BYOK: 요청별 api_key/mock override(미지정 시 settings 기본값, 비파괴).
"""

import random

from openai import AsyncOpenAI

from app.application.service.coaching_ai_service import CoachingAiService
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

# 코칭 시스템 프롬프트 — 웰니스 코칭(진단·처방 아님), 고정 체크리스트 금지.
COACHING_SYSTEM_PROMPT = """너는 '건강냥'이야. 밤에 깨어나 하루를 함께 돌아보는 따뜻한 웰니스 동반자야.

대화 원칙:
- 반말, 짧고 다정하게. 먼저 공감하고, 판단하지 않아.
- 진단·처방·약 권유는 절대 하지 않아(웰니스 코칭일 뿐).
- 고정된 체크리스트를 들이밀지 않아. 맥락에 맞는 작은 행동 하나만 부드럽게 권해.
- 감정 라벨을 직접 붙이지 않아("힘들었겠다" ✅ / "우울하셨군요" ❌).
"""

_PERSONA_HINT = (
    "\n\n[비서 톤 요청]\n사용자가 원하는 말투/페르소나: {persona}. 이 톤을 자연스럽게 반영해."
)


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

        system_prompt = COACHING_SYSTEM_PROMPT
        if persona:
            system_prompt += _PERSONA_HINT.format(persona=persona)

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
