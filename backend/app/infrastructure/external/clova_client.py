import json
import random

from openai import AsyncOpenAI

from app.application.service.ai_chat_service import AiChatService
from app.application.service.chunk_extraction_prompt import (
    CHUNK_EXTRACT_SYSTEM_PROMPT,
    CHUNK_EXTRACT_USER_REQUEST,
)
from app.application.service.diary_chat_prompt import build_diary_chat_system_prompt
from app.application.service.health_ai_service import HealthAiService
from app.application.service.health_chat_prompt import build_health_chat_system_prompt
from app.domain.model.chat_message import ChatMessage
from app.domain.model.health_message import HealthMessage
from app.infrastructure.config.settings import settings


def _resolve_client_api_key(api_key: str | None, mock: bool) -> str | None:
    resolved = api_key if api_key is not None else settings.clova_api_key
    if not resolved and mock:
        return "mock-clova-api-key"
    return resolved


# ─── Mock 응답 풀 (이음이 V3 톤, CLOVA_MOCK_MODE=true 전용) ─────────────────────
# NCP API 키 수령 전 FE 연동·흐름 검증용. 7개 랜덤 선택.
_MOCK_CHAT_RESPONSES = [
    "그랬구나. 오늘 하루 어땠어?",
    "그 말 들으니까 나도 조금 마음이 무거워지네.",
    "힘들었겠다. 그래도 여기 와서 얘기해줘서 다행이야.",
    "응, 계속 얘기해봐. 다 들을게.",
    "오늘 그런 일이 있었구나. 지금은 좀 어때?",
    "작은 일인 것 같아도 네가 신경 쓰이면 큰 거야.",
    "어떤 기분이었는지 더 얘기해줄 수 있어?",
]

_MOCK_DIARY_RESPONSES = [
    {
        "title": "오늘 하루를 돌아보며",
        "content": "오늘은 여러 가지 일이 있었다. 생각보다 피곤한 하루였지만, 이음이와 얘기하면서 조금은 가벼워진 것 같다. 감정을 꺼내놓는 게 이렇게 도움이 될 줄 몰랐다. 내일은 조금 더 나에게 친절하게 대해야겠다. 오늘도 수고했다.",
        "emotion": "calm",
        "satisfaction": 60,
        "keywords": ["피곤", "회고", "휴식"],
    },
    {
        "title": "소소한 하루",
        "content": "특별한 일은 없었지만 나름대로 하루를 버텼다. 피곤한 건 어쩔 수 없지만 그래도 이렇게 기록하는 시간이 생겼다. 자잘한 감정들이 쌓이면 결국 무너지는 것 같아서 조금씩 털어내야겠다고 생각했다. 오늘도 나름 잘 살았다. 내일도 그러면 된다.",
        "emotion": "tired",
        "satisfaction": 50,
        "keywords": ["버팀", "피곤", "기록"],
    },
]


# -------------------------------
#  일기 작성용 시스템 프롬프트 (강화)
# -------------------------------
DIARY_SYSTEM_PROMPT = """너는 대화 내용을 바탕으로 사용자의 일기를 JSON으로 작성하는 엔진이야.

절대 규칙:
- 반드시 JSON만 출력해.
- JSON 외의 설명, 코드블록, 텍스트는 절대 출력하지 마.
- 사용자가 말하지 않은 내용을 꾸며내지 마.
- AI, 이음, 서비스에 대한 감사나 언급을 일기에 넣지 마.
- 과장하거나 교훈적으로 쓰지 마.
- 사용자가 쓸 법한 자연스러운 일기체로 작성해.
"""


DIARY_USER_REQUEST = """위 대화를 바탕으로 일기를 JSON 형식으로 작성해줘.

반드시 아래 형식의 JSON만 출력해:

{"title":"제목","content":"본문 (반드시 4~5문장)","emotion":"happy/sad/angry/anxious/calm/excited/tired/grateful 중 하나","satisfaction":0~100 숫자,"keywords":["키워드1","키워드2","키워드3"]}

규칙:
- content는 4~5문장.
- 감정은 가장 지배적인 하나만 선택.
- satisfaction은 대화 분위기 기반으로 추정하되,
  명확하지 않으면 50으로 설정.
- keywords는 사용자의 하루를 대표하는 짧은 명사/명사구 2~3개.
- keywords에는 조사, 어미, 부사보다 핵심 사건·활동·감정 단어를 넣어.
- 너무 일반적인 단어(오늘, 기분, 생각, 하루)는 피하고, 사용자가 말하지 않은 내용은 넣지 마.
- 현실 사건 중심으로 작성.
"""


FINALIZE_INTENT_SYSTEM_PROMPT = """사용자의 메시지가 일기 정리에 동의하는지 판단해.
반드시 yes 또는 no 중 하나만 출력해.
다른 텍스트는 절대 쓰지 마.
"""


CLOSING_MESSAGE_SYSTEM_PROMPT = """너는 젠틀한 고양이 같은 개인 비서야.
사용자가 일기 작성에 동의했어.
일기 작성 중임을 알리는 한 문장만 출력해.
반드시 한 문장.
반말.
따뜻하지만 과하지 않게.
"""


# -------------------------------
# Client 구현
# -------------------------------
class ClovaClient(AiChatService):
    def __init__(self, api_key: str | None = None, mock: bool | None = None) -> None:
        self._mock = mock if mock is not None else settings.clova_mock_mode
        # BYOK: 요청별 키/모드 override. 미지정 시 settings 기본값(비파괴).
        self._client = AsyncOpenAI(
            api_key=_resolve_client_api_key(api_key, self._mock),
            base_url=settings.clova_base_url,
        )

    async def chat(
        self,
        messages: list[ChatMessage],
        suggest_finalize: bool = False,
        max_turns: int = 5,
    ) -> str:
        # CLOVA_MOCK_MODE=true — API 키 없이 FE 연동 가능
        if self._mock:
            if suggest_finalize:
                return "오늘 이야기를 일기로 정리해볼까?"
            return random.choice(_MOCK_CHAT_RESPONSES)
        # 현재 턴 번호를 명시해 모델이 스스로 판단해 조기 종료하는 것을 막는다.
        # (messages 에는 방금 추가된 사용자 발화가 포함되어 있어 현재 턴 수와 같다.)
        user_turn = max(1, sum(1 for m in messages if m.role == "user"))
        system_prompt = build_diary_chat_system_prompt(
            max_turns=max_turns,
            current_user_turn=user_turn,
            suggest_finalize=suggest_finalize,
            tool_calling_enabled=False,
        )

        api_messages = [{"role": "system", "content": system_prompt}]
        for m in messages:
            if m.role != "system":
                api_messages.append({"role": m.role, "content": m.content})

        response = await self._client.chat.completions.create(
            model=settings.clova_model,
            messages=api_messages,
            temperature=0.6,  # 안정형 톤
            max_tokens=300,  # 톡 스타일 유지
        )

        return response.choices[0].message.content.strip()

    async def generate_diary(self, messages: list[ChatMessage]) -> dict:
        if self._mock:
            return random.choice(_MOCK_DIARY_RESPONSES)

        api_messages = [{"role": "system", "content": DIARY_SYSTEM_PROMPT}]

        for m in messages:
            if m.role != "system":
                api_messages.append({"role": m.role, "content": m.content})

        api_messages.append({"role": "user", "content": DIARY_USER_REQUEST})

        response = await self._client.chat.completions.create(
            model=settings.clova_model,
            messages=api_messages,
            temperature=0.3,  # 구조 안정성
            max_tokens=800,
        )

        content = response.choices[0].message.content.strip()
        return self._parse_diary_response(content)

    def _parse_diary_response(self, content: str) -> dict:
        # 코드블록 제거
        if content.startswith("```"):
            content = content.split("```")[1]
            content = content.replace("json", "").strip()

        # JSON 블록 추출 보강
        first = content.find("{")
        last = content.rfind("}")
        if first != -1 and last != -1:
            content = content[first : last + 1]

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"일기 JSON 파싱 실패: {content}") from e

    async def detect_finalize_intent(self, user_message: str) -> bool:
        if self._mock:
            # 긍정 키워드 간단 휴리스틱
            pos = ("응", "좋아", "그래", "ㅇㅇ", "맞아", "해줘", "써줘")
            return any(k in user_message for k in pos)

        response = await self._client.chat.completions.create(
            model=settings.clova_model,
            messages=[
                {"role": "system", "content": FINALIZE_INTENT_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.1,
            max_tokens=5,
        )

        answer = response.choices[0].message.content.strip().lower()
        return answer == "yes"

    async def generate_closing_message(self, messages: list[ChatMessage]) -> str:
        if self._mock:
            return "오늘 하루 고마워. 일기 쓰는 중이야 잠깐만."

        api_messages = [{"role": "system", "content": CLOSING_MESSAGE_SYSTEM_PROMPT}]
        for m in messages:
            if m.role != "system":
                api_messages.append({"role": m.role, "content": m.content})

        response = await self._client.chat.completions.create(
            model=settings.clova_model,
            messages=api_messages,
            temperature=0.5,
            max_tokens=80,
        )

        return response.choices[0].message.content.strip()

    async def extract_event_chunks(self, messages: list[ChatMessage]) -> list[dict]:
        if self._mock:
            return []  # 모의 응답 모드: 청크 추출 스킵

        api_messages = [{"role": "system", "content": CHUNK_EXTRACT_SYSTEM_PROMPT}]
        for m in messages:
            if m.role != "system":
                api_messages.append({"role": m.role, "content": m.content})
        api_messages.append({"role": "user", "content": CHUNK_EXTRACT_USER_REQUEST})

        response = await self._client.chat.completions.create(
            model=settings.clova_model,
            messages=api_messages,
            temperature=0.2,
            max_tokens=800,
        )

        content = response.choices[0].message.content.strip()
        return self._parse_chunks_response(content)

    def _parse_chunks_response(self, content: str) -> list[dict]:
        if content.startswith("```"):
            content = content.split("```")[1]
            content = content.replace("json", "").strip()

        first = content.find("[")
        last = content.rfind("]")
        if first != -1 and last != -1:
            content = content[first : last + 1]

        try:
            result = json.loads(content)
            return result if isinstance(result, list) else []
        except json.JSONDecodeError:
            return []


HEALTH_CHAT_GREETING = """안녕! 나는 헬시야. 네 삼성 헬스 데이터 기반으로 건강 정보를 알려줄 수 있어.
걸음수, 심박수, 운동 기록 같은 거 궁금한 거 물어봐! 💪"""

HEALTH_CHAT_MOCK_RESPONSE = (
    "건강 데이터 확인 기능을 테스트하고 있어. 실제 수치는 CLOVA 연결 후 데이터에 근거해서 알려줄게."
)


# -------------------------------
# 헬스 챗봇 클라이언트
# -------------------------------
class HealthClovaClient(HealthAiService):
    def __init__(self, api_key: str | None = None, mock: bool | None = None) -> None:
        self._mock = mock if mock is not None else settings.clova_mock_mode
        self._client = AsyncOpenAI(
            api_key=_resolve_client_api_key(api_key, self._mock),
            base_url=settings.clova_base_url,
        )

    async def chat(
        self,
        messages: list[HealthMessage],
        health_context: list[str] | None = None,
    ) -> str:
        if not messages:
            return HEALTH_CHAT_GREETING

        if self._mock:
            return HEALTH_CHAT_MOCK_RESPONSE

        system_prompt = build_health_chat_system_prompt(
            tool_calling_enabled=False,
            health_context=health_context,
        )

        api_messages = [{"role": "system", "content": system_prompt}]
        for m in messages:
            if m.role != "system":
                api_messages.append({"role": m.role, "content": m.content})

        response = await self._client.chat.completions.create(
            model=settings.clova_model,
            messages=api_messages,
            temperature=0.4,
            max_tokens=300,
        )

        return response.choices[0].message.content.strip()
