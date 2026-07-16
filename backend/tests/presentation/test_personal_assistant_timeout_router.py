from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.application.service.model_provider_error import (
    ModelProviderError,
    ModelProviderErrorCategory,
)
from app.application.service.personal_assistant_timeout import PersonalAssistantTimeoutError
from app.application.usecase.personal_assistant_agent import PersonalAssistantMode
from app.domain.model.chat_session import ChatSession
from app.domain.model.health_session import HealthSession
from app.infrastructure.config.dependencies import (
    get_ai_chat_service,
    get_chat_session_repo,
    get_coaching_personal_assistant_agent_factory,
    get_diary_repo,
    get_extract_chunks_usecase,
    get_extract_signals_usecase,
    get_health_session_repo,
    get_personal_assistant_agent_factory,
)
from app.main import (
    MODEL_PROVIDER_FAILURE_DETAIL,
    MODEL_PROVIDER_RETRY_EXHAUSTED_DETAIL,
    PERSONAL_ASSISTANT_TIMEOUT_DETAIL,
    app,
)
from app.presentation.auth_deps import get_current_device_id


class _TimeoutAgent:
    async def run(self, **kwargs):
        raise PersonalAssistantTimeoutError("execution")


class _TimeoutFactory:
    def create(self, *, device_id: str, session_id: UUID, mode: PersonalAssistantMode):
        return _TimeoutAgent()


class _ProviderErrorAgent:
    def __init__(self, error: ModelProviderError) -> None:
        self._error = error

    async def run(self, **kwargs):
        raise self._error


class _ProviderErrorFactory:
    def __init__(self, error: ModelProviderError) -> None:
        self._error = error

    def create(self, *, device_id: str, session_id: UUID, mode: PersonalAssistantMode):
        return _ProviderErrorAgent(self._error)


class _ChatRepo:
    def __init__(self, session: ChatSession) -> None:
        self.session = session
        self.save_calls = 0

    async def find_by_id(self, session_id: UUID) -> ChatSession | None:
        return self.session if session_id == self.session.id else None

    async def save(self, session: ChatSession) -> ChatSession:
        self.save_calls += 1
        return session


class _HealthRepo:
    def __init__(self, session: HealthSession) -> None:
        self.session = session
        self.save_calls = 0

    async def find_by_id(self, session_id: UUID, device_id: str) -> HealthSession | None:
        if session_id == self.session.id and device_id == self.session.device_id:
            return self.session
        return None

    async def save(self, session: HealthSession) -> HealthSession:
        self.save_calls += 1
        return session


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_diary_message_timeout_returns_generic_504_without_saving():
    session = ChatSession(device_id="dev-a")
    session.add_message("assistant", "시작해볼까?")
    repo = _ChatRepo(session)
    app.dependency_overrides[get_current_device_id] = lambda: "dev-a"
    app.dependency_overrides[get_chat_session_repo] = lambda: repo
    app.dependency_overrides[get_ai_chat_service] = object
    app.dependency_overrides[get_diary_repo] = object
    app.dependency_overrides[get_personal_assistant_agent_factory] = _TimeoutFactory
    app.dependency_overrides[get_extract_chunks_usecase] = object

    response = TestClient(app).post(
        f"/api/v1/chat/sessions/{session.id}/messages",
        json={"content": "오늘 힘들었어"},
    )

    assert response.status_code == 504
    assert response.json() == {"detail": PERSONAL_ASSISTANT_TIMEOUT_DETAIL}
    assert "execution" not in response.text
    assert repo.save_calls == 0


def test_health_message_timeout_returns_same_generic_504_without_saving():
    session = HealthSession(device_id="dev-a")
    session.add_message("assistant", "건강 인사")
    repo = _HealthRepo(session)
    app.dependency_overrides[get_current_device_id] = lambda: "dev-a"
    app.dependency_overrides[get_health_session_repo] = lambda: repo
    app.dependency_overrides[get_personal_assistant_agent_factory] = _TimeoutFactory

    response = TestClient(app).post(
        f"/api/v1/health-chat/sessions/{session.id}/messages",
        json={"content": "오늘 걸음 수 알려줘"},
    )

    assert response.status_code == 504
    assert response.json() == {"detail": PERSONAL_ASSISTANT_TIMEOUT_DETAIL}
    assert "execution" not in response.text
    assert repo.save_calls == 0


def test_coaching_message_timeout_returns_same_generic_504_without_signal_extraction():
    app.dependency_overrides[get_current_device_id] = lambda: "dev-a"
    app.dependency_overrides[get_coaching_personal_assistant_agent_factory] = _TimeoutFactory
    app.dependency_overrides[get_extract_signals_usecase] = object

    response = TestClient(app).post(
        "/api/v1/coaching/messages",
        json={"message": "오늘 너무 지쳤어", "history": []},
    )

    assert response.status_code == 504
    assert response.json() == {"detail": PERSONAL_ASSISTANT_TIMEOUT_DETAIL}
    assert "execution" not in response.text


@pytest.mark.parametrize(
    ("error", "status_code", "detail"),
    [
        (
            ModelProviderError(
                category=ModelProviderErrorCategory.UNAVAILABLE,
                retryable=True,
                status_code=503,
            ),
            503,
            MODEL_PROVIDER_RETRY_EXHAUSTED_DETAIL,
        ),
        (
            ModelProviderError(
                category=ModelProviderErrorCategory.AUTHENTICATION,
                retryable=False,
                status_code=401,
            ),
            502,
            MODEL_PROVIDER_FAILURE_DETAIL,
        ),
    ],
)
def test_diary_provider_errors_return_stable_status_without_internal_details(
    error, status_code, detail
):
    session = ChatSession(device_id="dev-a")
    session.add_message("assistant", "시작해볼까?")
    repo = _ChatRepo(session)
    app.dependency_overrides[get_current_device_id] = lambda: "dev-a"
    app.dependency_overrides[get_chat_session_repo] = lambda: repo
    app.dependency_overrides[get_ai_chat_service] = object
    app.dependency_overrides[get_diary_repo] = object
    app.dependency_overrides[get_personal_assistant_agent_factory] = lambda: _ProviderErrorFactory(
        error
    )
    app.dependency_overrides[get_extract_chunks_usecase] = object

    response = TestClient(app).post(
        f"/api/v1/chat/sessions/{session.id}/messages",
        json={"content": "오늘 힘들었어"},
    )

    assert response.status_code == status_code
    assert response.json() == {"detail": detail}
    assert "authentication" not in response.text
    assert "503" not in response.text
    assert repo.save_calls == 0


@pytest.mark.parametrize(
    ("error", "status_code", "detail"),
    [
        (
            ModelProviderError(
                category=ModelProviderErrorCategory.UNAVAILABLE,
                retryable=True,
            ),
            503,
            MODEL_PROVIDER_RETRY_EXHAUSTED_DETAIL,
        ),
        (
            ModelProviderError(
                category=ModelProviderErrorCategory.INVALID_REQUEST,
                retryable=False,
            ),
            502,
            MODEL_PROVIDER_FAILURE_DETAIL,
        ),
    ],
)
def test_health_provider_errors_return_stable_status_without_internal_details(
    error, status_code, detail
):
    session = HealthSession(device_id="dev-a")
    session.add_message("assistant", "건강 인사")
    repo = _HealthRepo(session)
    app.dependency_overrides[get_current_device_id] = lambda: "dev-a"
    app.dependency_overrides[get_health_session_repo] = lambda: repo
    app.dependency_overrides[get_personal_assistant_agent_factory] = lambda: _ProviderErrorFactory(
        error
    )

    response = TestClient(app).post(
        f"/api/v1/health-chat/sessions/{session.id}/messages",
        json={"content": "오늘 걸음 수 알려줘"},
    )

    assert response.status_code == status_code
    assert response.json() == {"detail": detail}
    assert "invalid_request" not in response.text
    assert repo.save_calls == 0


@pytest.mark.parametrize(
    ("error", "status_code", "detail"),
    [
        (
            ModelProviderError(
                category=ModelProviderErrorCategory.NETWORK,
                retryable=True,
            ),
            503,
            MODEL_PROVIDER_RETRY_EXHAUSTED_DETAIL,
        ),
        (
            ModelProviderError(
                category=ModelProviderErrorCategory.UNKNOWN,
                retryable=False,
            ),
            502,
            MODEL_PROVIDER_FAILURE_DETAIL,
        ),
    ],
)
def test_coaching_provider_errors_return_stable_status_without_internal_details(
    error,
    status_code,
    detail,
):
    app.dependency_overrides[get_current_device_id] = lambda: "dev-a"
    app.dependency_overrides[get_coaching_personal_assistant_agent_factory] = lambda: (
        _ProviderErrorFactory(error)
    )
    app.dependency_overrides[get_extract_signals_usecase] = object

    response = TestClient(app).post(
        "/api/v1/coaching/messages",
        json={"message": "오늘 너무 지쳤어", "history": []},
    )

    assert response.status_code == status_code
    assert response.json() == {"detail": detail}
    assert "network" not in response.text
    assert "unknown" not in response.text
