"""코칭 라우터 — 밤 코칭 대화(guardrail-first).

stateless 엔드포인트: 클라이언트가 history를 보관·전송한다. 위험 입력은 면책으로 단락된다.
BYOK 헤더(X-Clova-Api-Key)는 get_coaching_ai_service에서 처리된다.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from app.application.usecase.extract_signals import ExtractSignalsUseCase
from app.application.usecase.personal_assistant_agent_factory import PersonalAssistantAgentFactory
from app.application.usecase.send_coaching_message import SendCoachingMessageUseCase
from app.domain.model.chat_message import ChatMessage
from app.infrastructure.config.dependencies import (
    get_coaching_personal_assistant_agent_factory,
    get_extract_signals_usecase,
)
from app.presentation.auth_deps import get_current_device_id
from app.presentation.router.coaching_schemas import (
    CoachingMessageRequest,
    CoachingMessageResponse,
)

router = APIRouter(prefix="/api/v1/coaching", tags=["coaching"])


@router.post(
    "/messages",
    response_model=CoachingMessageResponse,
    summary="밤 코칭 메시지 전송",
    description="건강냥과의 코칭 대화. 의료 요구는 면책으로 단락되고, 안전 입력만 코칭으로 흐릅니다.",
)
async def send_coaching_message(
    body: CoachingMessageRequest,
    device_id: str = Depends(get_current_device_id),
    personal_assistant_factory: PersonalAssistantAgentFactory = Depends(
        get_coaching_personal_assistant_agent_factory
    ),
    extract_signals: ExtractSignalsUseCase = Depends(get_extract_signals_usecase),
):
    if not body.message or not body.message.strip():
        raise HTTPException(status_code=400, detail="메시지가 비어 있습니다.")

    history = [
        ChatMessage(role=h.role, content=h.content, created_at=datetime.now()) for h in body.history
    ]
    usecase = SendCoachingMessageUseCase(personal_assistant_factory, extract_signals)
    reply = await usecase.execute(
        device_id=device_id,
        message=body.message,
        history=history,
        persona=body.persona,
    )
    return CoachingMessageResponse(reply=reply)
