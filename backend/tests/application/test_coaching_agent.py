"""LangGraph 코칭 에이전트 — guardrail-first + tripwire (G001-3, TDD).

위험 입력은 coach 호출 없이 면책으로 단락되고, 안전 입력만 코칭 생성으로 흐른다.
coach 응답에 처방성 내용이 섞이면 tripwire가 면책으로 치환한다(이중 안전망).
"""

from uuid import uuid4

from app.application.service.coaching_ai_service import CoachingAiService
from app.application.usecase.coaching_agent import CoachingAgent
from app.domain.model.chat_message import ChatMessage


class _FakeCoachAi(CoachingAiService):
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.called = False

    async def coach(self, messages: list[ChatMessage], persona: str | None = None) -> str:
        self.called = True
        return self.reply


async def test_risky_input_short_circuits_to_disclaimer():
    ai = _FakeCoachAi("아무 코칭 멘트")
    agent = CoachingAgent(ai)
    response = await agent.run(
        session_id=uuid4(), messages=[], current_user_message="이 약 먹어도 돼?"
    )
    assert ai.called is False, "위험 입력인데 coach가 호출됨"
    assert "전문가" in response


async def test_safe_input_uses_coach():
    ai = _FakeCoachAi("오늘은 푹 쉬어")
    agent = CoachingAgent(ai)
    response = await agent.run(
        session_id=uuid4(), messages=[], current_user_message="오늘 너무 지쳤어"
    )
    assert ai.called is True
    assert response == "오늘은 푹 쉬어"


async def test_tripwire_replaces_prescriptive_coach_response():
    ai = _FakeCoachAi("하루 500mg씩 드세요")  # coach가 실수로 처방성 응답
    agent = CoachingAgent(ai)
    response = await agent.run(session_id=uuid4(), messages=[], current_user_message="피곤해")
    assert "mg" not in response, "처방성 토큰이 응답에 남음"
    assert "전문가" in response
