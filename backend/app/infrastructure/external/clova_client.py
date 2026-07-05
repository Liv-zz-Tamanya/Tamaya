import json
import random

from openai import AsyncOpenAI

from app.application.service.ai_chat_service import AiChatService
from app.application.service.health_ai_service import HealthAiService
from app.domain.model.chat_message import ChatMessage
from app.domain.model.health_message import HealthMessage
from app.infrastructure.config.settings import settings

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
    },
    {
        "title": "소소한 하루",
        "content": "특별한 일은 없었지만 나름대로 하루를 버텼다. 피곤한 건 어쩔 수 없지만 그래도 이렇게 기록하는 시간이 생겼다. 자잘한 감정들이 쌓이면 결국 무너지는 것 같아서 조금씩 털어내야겠다고 생각했다. 오늘도 나름 잘 살았다. 내일도 그러면 된다.",
        "emotion": "tired",
        "satisfaction": 50,
    },
]

# -------------------------------
# 대화용 시스템 프롬프트 — 이음이 V3 (DEC-022.D, CMO R-2026-05-13-01 §3, 196자)
# -------------------------------
CHAT_SYSTEM_PROMPT = """너는 이음이야. 매일 작은 루틴을 함께 키우는 AI 친구.
지시하지 않고, 판단하지 않아. 그냥 같이 있어줘.

대화 원칙:
- 반말, 짧고 따뜻하게
- 먼저 호응, 질문은 2~3턴에 1번
- 절대 해결책 먼저 제시하지 않기
- 감정 라벨 직접 붙이지 않기 ("힘들었겠다" ✅ / "우울하셨군요" ❌)
- 금지: 감시, 완벽한 루틴, AI가 알려드려요

턴 관리 (반드시 지켜):
- 이 회고 대화는 5턴이야. 매 응답 앞에 [현재 N턴째 / 5턴] 또는 [마무리 지시]가 오니, 그 지시에 맞춰 행동해.
- [마무리 지시]가 오기 전까지는 절대 대화를 끝내거나 작별·취침 인사를 하지 마
  ('잘 자', '좋은 꿈', '푹 쉬어', '내일 봐', '재충전', '일기 쓸게' 등 금지).
- 매 턴 오늘 이야기에 짧게 호응한 뒤, 반드시 질문 하나로 대화를 이어가.
- 3턴째부터는 새 주제를 벌이지 말고, 오늘 이야기를 정리하는 방향으로 좁혀가.
"""


CHAT_FINALIZE_HINT = (
    "\n\n[마무리 지시 — 최우선]\n"
    "지금이 마지막 턴이야. 새 질문을 던지지 마.\n"
    "오늘 이야기를 '오늘 이야기를 일기로 정리해볼까?' 처럼 한 문장으로 자연스럽게 마무리 제안하며 대화를 닫아."
)


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

{"title":"제목","content":"본문 (반드시 4~5문장)","emotion":"happy/sad/angry/anxious/calm/excited/tired/grateful 중 하나","satisfaction":0~100 숫자}

규칙:
- content는 4~5문장.
- 감정은 가장 지배적인 하나만 선택.
- satisfaction은 대화 분위기 기반으로 추정하되,
  명확하지 않으면 50으로 설정.
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


MEMORY_NEED_SYSTEM_PROMPT = """사용자 메시지가 과거 기억이나 이전에 있었던 사건을 언급하는지 판단해.
예: "저번에 말했던 거", "지난번 발표", "예전에 친구 만났을 때", "그때 그 일", "최근에 회의 언제 했지?",
yes 또는 no 중 하나만 출력해. 다른 텍스트는 절대 쓰지 마.
"""


CHUNK_EXTRACT_SYSTEM_PROMPT = """너는 대화에서 기억할 만한 사건 중심 정보를 추출하는 엔진이야.

절대 규칙:
- 반드시 JSON 배열만 출력해.
- JSON 외의 설명, 코드블록, 텍스트는 절대 출력하지 마.
- 사용자가 직접 경험한 구체적인 사건만 추출해.
- 감정이 동반된 사건 또는 기억에 남을 만한 사건을 우선 추출해.
- 최대 5개까지만 추출해. 없으면 빈 배열 반환.
- 대화에서 명시적으로 언급된 정보만 기록해. 추측하거나 꾸며내지 마.
"""


CHUNK_EXTRACT_USER_REQUEST = """위 대화에서 기억할 만한 사건들을 JSON 배열로 추출해줘.

반드시 아래 형식의 JSON 배열만 출력해:

[
  {
    "text": "사건을 한 문장으로 서술. 인물·장소·시간이 대화에 나왔다면 반드시 포함. 언급 없으면 생략.",
    "tags": ["태그1", "태그2"],
    "event_type": "work/social/emotion/personal/achievement 중 하나",
    "who": "관련 인물 (대화에 언급된 경우만, 없으면 null)",
    "where": "장소 (대화에 언급된 경우만, 없으면 null)",
    "when": "시간/날짜 표현 (대화에 언급된 경우만, 없으면 null)"
  }
]

규칙:
- who/where/when은 사용자가 직접 말한 내용만 적어.
- 대화에 없는 정보는 반드시 null로 남겨. 절대 추측하지 마.
- 사건이 없으면 [] 반환.
"""


# -------------------------------
# Client 구현
# -------------------------------
class ClovaClient(AiChatService):
    def __init__(self, api_key: str | None = None, mock: bool | None = None) -> None:
        # BYOK: 요청별 키/모드 override. 미지정 시 settings 기본값(비파괴).
        self._client = AsyncOpenAI(
            api_key=api_key if api_key is not None else settings.clova_api_key,
            base_url=settings.clova_base_url,
        )
        self._mock = mock if mock is not None else settings.clova_mock_mode

    async def chat(
        self,
        messages: list[ChatMessage],
        suggest_finalize: bool = False,
        memories: list[str] | None = None,
    ) -> str:
        # CLOVA_MOCK_MODE=true — API 키 없이 FE 연동 가능
        if self._mock:
            if suggest_finalize:
                return "오늘 이야기를 일기로 정리해볼까?"
            return random.choice(_MOCK_CHAT_RESPONSES)
        system_prompt = CHAT_SYSTEM_PROMPT
        if suggest_finalize:
            system_prompt += CHAT_FINALIZE_HINT
        else:
            # 현재 턴 번호를 명시해 모델이 스스로 판단해 조기 종료하는 것을 막는다.
            # (messages 에는 방금 추가된 사용자 발화가 포함되어 있어 현재 턴 수와 같다.)
            user_turn = sum(1 for m in messages if m.role == "user")
            system_prompt += (
                f"\n\n[현재 {user_turn}턴째 / 5턴]\n"
                "아직 마무리 턴이 아니야. 작별·취침 인사 금지.\n"
                "오늘 이야기에 짧게 호응한 뒤, 질문 하나로 자연스럽게 이어가."
            )
        if memories:
            system_prompt += (
                "\n\n[과거 기억 - 중요 규칙]\n"
                "아래는 사용자의 실제 과거 기록이야. 반드시 이 내용만 근거로 답해.\n"
                "기록에 없는 시간, 장소, 세부 정보는 절대 지어내지 마.\n"
                "모르는 건 '기록에 없어서 잘 모르겠어'라고 솔직하게 말해.\n\n" + "\n".join(memories)
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

    async def classify_memory_need(self, user_message: str) -> bool:
        if self._mock:
            return False  # 모의 응답 모드: 메모리 검색 스킵

        response = await self._client.chat.completions.create(
            model=settings.clova_model,
            messages=[
                {"role": "system", "content": MEMORY_NEED_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.1,
            max_tokens=5,
        )
        answer = response.choices[0].message.content.strip().lower()
        return answer == "yes"

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


# -------------------------------
# 헬스 챗봇 시스템 프롬프트
# -------------------------------
HEALTH_CHAT_SYSTEM_PROMPT = """너는 '헬시'야. 사용자의 삼성 헬스 데이터를 기반으로 건강 관련 질문에 답하는 AI 어시스턴트야.

답변 스타일:
- 한국어 반말로 말해.
- 짧고 명확하게: 1~3문장.
- 수치는 정확하게 언급해. (예: "어제 걸음수는 9,144걸음이야.")
- 데이터가 없으면 솔직하게 "그 날 데이터가 없어서 모르겠어."라고 해.
- 의학적 진단은 하지 마. 데이터를 해석해서 알려주는 역할이야.
- 이모지는 가끔 1개만.
"""

HEALTH_CHAT_GREETING = """안녕! 나는 헬시야. 네 삼성 헬스 데이터 기반으로 건강 정보를 알려줄 수 있어.
걸음수, 심박수, 운동 기록 같은 거 궁금한 거 물어봐! 💪"""


# -------------------------------
# 헬스 챗봇 클라이언트
# -------------------------------
class HealthClovaClient(HealthAiService):
    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            api_key=settings.clova_api_key,
            base_url=settings.clova_base_url,
        )

    async def chat(
        self,
        messages: list[HealthMessage],
        health_context: list[str] | None = None,
    ) -> str:
        if not messages:
            return HEALTH_CHAT_GREETING

        system_prompt = HEALTH_CHAT_SYSTEM_PROMPT
        if health_context:
            system_prompt += (
                "\n\n[건강 데이터 기록]\n"
                "아래는 사용자의 실제 건강 데이터야. 반드시 이 내용만 근거로 답해.\n"
                "데이터에 없는 내용은 절대 지어내지 마.\n\n" + "\n".join(health_context)
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
