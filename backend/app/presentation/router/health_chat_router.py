from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.application.service.health_ai_service import HealthAiService
from app.application.usecase.get_health_session import GetHealthSessionUseCase
from app.application.usecase.personal_assistant_agent_factory import PersonalAssistantAgentFactory
from app.application.usecase.send_health_message import SendHealthMessageUseCase
from app.application.usecase.start_health_session import StartHealthSessionUseCase
from app.domain.repository.health_session_repository import HealthSessionRepository
from app.infrastructure.config.dependencies import (
    get_health_ai_service,
    get_health_session_repo,
    get_personal_assistant_agent_factory,
)
from app.presentation.auth_deps import get_current_device_id
from app.presentation.router.health_schemas import (
    HealthMessageResponse,
    HealthSessionResponse,
    SendHealthMessageRequest,
    SendHealthMessageResponse,
)

router = APIRouter(prefix="/api/v1/health-chat", tags=["health-chat"])


@router.post("/sessions", response_model=HealthSessionResponse)
async def start_session(
    device_id: str = Depends(get_current_device_id),
    repo: HealthSessionRepository = Depends(get_health_session_repo),
    ai: HealthAiService = Depends(get_health_ai_service),
):
    use_case = StartHealthSessionUseCase(repo=repo, ai=ai)
    session = await use_case.execute(device_id)
    return HealthSessionResponse.from_domain(session)


@router.get("/sessions/{session_id}", response_model=HealthSessionResponse)
async def get_session(
    session_id: UUID,
    device_id: str = Depends(get_current_device_id),
    repo: HealthSessionRepository = Depends(get_health_session_repo),
):
    use_case = GetHealthSessionUseCase(repo=repo)
    try:
        session = await use_case.execute(session_id, device_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return HealthSessionResponse.from_domain(session)


@router.post("/sessions/{session_id}/messages", response_model=SendHealthMessageResponse)
async def send_message(
    session_id: UUID,
    body: SendHealthMessageRequest,
    device_id: str = Depends(get_current_device_id),
    repo: HealthSessionRepository = Depends(get_health_session_repo),
    personal_assistant_factory: PersonalAssistantAgentFactory = Depends(
        get_personal_assistant_agent_factory
    ),
):
    use_case = SendHealthMessageUseCase(
        repo=repo,
        personal_assistant_factory=personal_assistant_factory,
    )
    try:
        user_msg, ai_msg = await use_case.execute(session_id, body.content, device_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return SendHealthMessageResponse(
        user_message=HealthMessageResponse.from_domain(user_msg),
        ai_message=HealthMessageResponse.from_domain(ai_msg),
    )
