import json

from openai import AsyncOpenAI

from app.application.service.ai_chat_service import AiChatService
from app.application.service.health_ai_service import HealthAiService
from app.domain.model.chat_message import ChatMessage
from app.domain.model.health_message import HealthMessage
from app.infrastructure.config.settings import settings

# -------------------------------
# 대화용 시스템 프롬프트 (개선 버전)
# -------------------------------
CHAT_SYSTEM_PROMPT = """너는 ‘이음’이야. 젠틀하고 깔끔한 말투의 고양이 같은 개인 비서로,
사용자가 하루를 자연스럽게 돌아보도록 돕는 역할이야.

대화 스타일(매우 중요):
- 한국어 반말로만 말해.
- 카톡처럼 짧게: 한 번의 답변은 1~3문장.
- 질문은 항상 딱 1개만.
- 설문처럼 캐묻지 말고, 자연스럽게 이어가.
- 불필요한 정보(스몰토크)도 자연스러운 대화에 필요하지만 실질적으로 사용자의 감정이나 그날의 정보를 얻을 수 있는 대화를 최소 5번 이상 주고 받아야 해.
- 아직 일기에 쓸 정보가 충분치 않다면 아래의 대화 목표를 참고해서 자연스럽게 대화를 더 이어가도록 질문해.
- 이모지는 가끔 1개만 (과하게 쓰지 마).

대화 목표:
- 오늘 있었던 일
- 그때 든 감정
- 컨디션(몸/에너지)
- 기억에 남는 순간 1개
- 작은 긍정/고마웠던 순간 1개 (억지로 만들지 말 것)

대화 규칙:
- 위 목표와 대화스타일로 대화를 나누다가 해당 주제에 대해 목표한 내용들을 어느정도 파악완료시
- 자연스럽게 다른 주제로 전환 (사용자와의 대화에서 나온 행동이나, 장소, 이벤트 등에서 파생)
- 최소 3회 이상 대화 주제를 전환하면서 대화를 충분히 이어가야 해.
- 각 주제에서 충분히 감정이나 정보를 얻기 위해 질문을 해주어야 해.

진행 방식:
- 먼저 1문장 공감.
- 감정이 애매하면 2가지 선택지로 확인.
- 조언은 최소화. 필요하면 5분 이내의 작은 제안만.
- 회복과 변화의 주체는 항상 사용자.

고양이 같은 존재감은 은은하게만:
예: "그건 내가 잘 기억해둘게."
과한 귀여움 금지.

항상 마지막은 질문 1개로 끝내.
"""


CHAT_FINALIZE_HINT = "\n대화가 충분하다면, 마지막에 자연스럽게 '오늘 이야기를 일기로 정리해볼까?' 같은 제안을 해."


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
    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            api_key=settings.clova_api_key,
            base_url=settings.clova_base_url,
        )

    async def chat(
        self,
        messages: list[ChatMessage],
        suggest_finalize: bool = False,
        memories: list[str] | None = None,
    ) -> str:
        system_prompt = CHAT_SYSTEM_PROMPT
        if suggest_finalize:
            system_prompt += CHAT_FINALIZE_HINT
        if memories:
            system_prompt += (
                "\n\n[과거 기억 - 중요 규칙]\n"
                "아래는 사용자의 실제 과거 기록이야. 반드시 이 내용만 근거로 답해.\n"
                "기록에 없는 시간, 장소, 세부 정보는 절대 지어내지 마.\n"
                "모르는 건 '기록에 없어서 잘 모르겠어'라고 솔직하게 말해.\n\n"
                + "\n".join(memories)
            )

        api_messages = [{"role": "system", "content": system_prompt}]
        for m in messages:
            if m.role != "system":
                api_messages.append({"role": m.role, "content": m.content})

        response = await self._client.chat.completions.create(
            model=settings.clova_model,
            messages=api_messages,
            temperature=0.6,   # 안정형 톤
            max_tokens=300,    # 톡 스타일 유지
        )

        return response.choices[0].message.content.strip()

    async def generate_diary(self, messages: list[ChatMessage]) -> dict:
        api_messages = [{"role": "system", "content": DIARY_SYSTEM_PROMPT}]

        for m in messages:
            if m.role != "system":
                api_messages.append({"role": m.role, "content": m.content})

        api_messages.append({"role": "user", "content": DIARY_USER_REQUEST})

        response = await self._client.chat.completions.create(
            model=settings.clova_model,
            messages=api_messages,
            temperature=0.3,   # 구조 안정성
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
            content = content[first:last + 1]

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"일기 JSON 파싱 실패: {content}") from e

    async def detect_finalize_intent(self, user_message: str) -> bool:
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
                "데이터에 없는 내용은 절대 지어내지 마.\n\n"
                + "\n".join(health_context)
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
