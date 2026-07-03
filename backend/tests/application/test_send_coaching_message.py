"""코칭 메시지 usecase — guardrail-first 합성 + history 전달 (G004-1, TDD).

usecase는 history에 현재 사용자 메시지를 덧붙여 CoachingAgent로 흘려보낸다.
안전 입력은 coach 응답을, 위험 입력은 면책을 반환한다(guardrail 단락).
"""

from datetime import datetime

from app.application.service.coaching_ai_service import CoachingAiService
from app.application.usecase.coaching_agent import CoachingAgent
from app.application.usecase.send_coaching_message import SendCoachingMessageUseCase
from app.domain.model.chat_message import ChatMessage


class _FakeCoachAi(CoachingAiService):
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.seen_messages: list[ChatMessage] | None = None
        self.seen_persona: str | None = None
        self.called = False

    async def coach(self, messages: list[ChatMessage], persona: str | None = None) -> str:
        self.called = True
        self.seen_messages = messages
        self.seen_persona = persona
        return self.reply


class _FailingExtract:
    async def execute(self, **_):
        raise RuntimeError("db down")


def _uc(ai: _FakeCoachAi) -> SendCoachingMessageUseCase:
    return SendCoachingMessageUseCase(CoachingAgent(ai))


async def test_safe_message_returns_coach_reply():
    ai = _FakeCoachAi("오늘은 푹 쉬어요")
    reply = await _uc(ai).execute(device_id="dev-1", message="오늘 너무 지쳤어", history=[])
    assert reply == "오늘은 푹 쉬어요"
    assert ai.called is True


async def test_risky_message_short_circuits_to_disclaimer():
    ai = _FakeCoachAi("아무 코칭")
    reply = await _uc(ai).execute(device_id="dev-1", message="이 약 먹어도 돼?", history=[])
    assert ai.called is False
    assert "전문가" in reply


async def test_current_message_appended_to_history_for_coach():
    ai = _FakeCoachAi("응 알겠어요")
    history = [
        ChatMessage(role="user", content="안녕", created_at=datetime.now()),
        ChatMessage(role="assistant", content="안녕!", created_at=datetime.now()),
    ]
    await _uc(ai).execute(device_id="dev-1", message="오늘 힘들었어", history=history)
    assert ai.seen_messages is not None
    assert len(ai.seen_messages) == 3  # history 2 + 현재 사용자 메시지
    assert ai.seen_messages[-1].role == "user"
    assert ai.seen_messages[-1].content == "오늘 힘들었어"


async def test_persona_is_threaded_to_coach():
    ai = _FakeCoachAi("부모님 톤 응답")
    await _uc(ai).execute(device_id="dev-1", message="오늘 지쳤어", history=[], persona="부모님")
    assert ai.seen_persona == "부모님"


async def test_signal_extraction_failure_does_not_break_reply():
    # best-effort: 정성신호 추출이 터져도 코칭 응답은 정상 반환
    ai = _FakeCoachAi("괜찮아요")
    uc = SendCoachingMessageUseCase(CoachingAgent(ai), _FailingExtract())
    reply = await uc.execute(device_id="dev-1", message="오늘 힘들었어", history=[])
    assert reply == "괜찮아요"
