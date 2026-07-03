"""정성신호 CLOVA 추출 클라이언트 — extract_event_chunks 패턴 재사용.

mock 모드(CLOVA_MOCK_MODE=true)는 None을 반환해 신호 추출을 건너뛴다(대화 흐름 보호).
real 모드는 단일 JSON 객체를 요구하는 프롬프트로 호출하고, 코드펜스 제거 → 객체 슬라이스
→ json.loads → 구조 검증의 방어적 경로로 파싱한다. 파싱 실패는 None으로 흡수한다.
"""

import json

from openai import AsyncOpenAI

from app.application.service.signal_extraction_service import SignalExtractionService
from app.domain.model.chat_message import ChatMessage
from app.infrastructure.config.settings import settings

SIGNAL_EXTRACT_SYSTEM_PROMPT = """너는 대화에서 사용자의 정성신호를 추출하는 엔진이야.

절대 규칙:
- 반드시 JSON 객체 하나만 출력해.
- JSON 외의 설명, 코드블록, 텍스트는 절대 출력하지 마.
- 대화에서 명시적으로 드러난 내용만 기록해. 추측하거나 꾸며내지 마.
- 진단·처방 같은 의료 판단은 절대 하지 마.
"""

SIGNAL_EXTRACT_USER_REQUEST = """위 대화에서 사용자의 정성신호를 JSON 객체 하나로 추출해줘.

반드시 아래 형식의 JSON만 출력해:

{
  "emotion": "happy/sad/angry/anxious/calm/excited/tired/grateful 중 가장 지배적인 하나",
  "behavior_mentions": [
    {"behavior": "건강행동 키워드(예: 수면/식사/운동/복약/산책)", "polarity": 1 또는 -1}
  ]
}

규칙:
- emotion은 위 8개 중 하나만 선택.
- behavior_mentions의 polarity는 긍정적 실천이면 1, 부정적/거름이면 -1.
- 건강행동 언급이 없으면 behavior_mentions는 빈 배열.
"""


class SignalExtractionClovaClient(SignalExtractionService):
    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            api_key=settings.clova_api_key,
            base_url=settings.clova_base_url,
        )
        self._mock = settings.clova_mock_mode

    async def extract_signal(self, messages: list[ChatMessage]) -> dict | None:
        if self._mock:
            return None  # 모의 응답 모드: 신호 추출 스킵 (대화 흐름 보호)

        api_messages = [{"role": "system", "content": SIGNAL_EXTRACT_SYSTEM_PROMPT}]
        for m in messages:
            if m.role != "system":
                api_messages.append({"role": m.role, "content": m.content})
        api_messages.append({"role": "user", "content": SIGNAL_EXTRACT_USER_REQUEST})

        response = await self._client.chat.completions.create(
            model=settings.clova_model,
            messages=api_messages,
            temperature=0.2,
            max_tokens=300,
        )

        content = response.choices[0].message.content.strip()
        return self._parse_signal_response(content)

    def _parse_signal_response(self, content: str) -> dict | None:
        # 코드펜스 제거
        if content.startswith("```"):
            content = content.split("```")[1]
            content = content.replace("json", "").strip()

        # JSON 객체 블록 추출 보강
        first = content.find("{")
        last = content.rfind("}")
        if first != -1 and last != -1:
            content = content[first : last + 1]

        try:
            raw = json.loads(content)
        except json.JSONDecodeError:
            return None
        if not isinstance(raw, dict):
            return None

        emotion = raw.get("emotion")
        if not isinstance(emotion, str) or not emotion.strip():
            return None

        return {
            "emotion": emotion,
            "behavior_mentions": self._normalize_mentions(raw.get("behavior_mentions")),
        }

    @staticmethod
    def _normalize_mentions(mentions: object) -> list[dict]:
        """behavior/polarity 구조가 온전한 항목만 남기고 polarity를 ±1로 정규화한다."""
        if not isinstance(mentions, list):
            return []
        normalized: list[dict] = []
        for item in mentions:
            if not isinstance(item, dict):
                continue
            behavior = item.get("behavior")
            if not isinstance(behavior, str) or not behavior.strip():
                continue
            raw_polarity = item.get("polarity")
            if isinstance(raw_polarity, bool):
                continue  # bool은 int 하위 클래스 — True/False가 ±1로 둔갑하는 것을 차단
            try:
                polarity = int(raw_polarity)
            except (TypeError, ValueError):
                continue
            polarity = max(-1, min(1, polarity))
            if polarity == 0:
                continue  # ±1 계약 외(중립) 값은 신호로 보지 않고 폐기
            normalized.append({"behavior": behavior, "polarity": polarity})
        return normalized
