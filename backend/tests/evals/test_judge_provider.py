"""judge provider 선택 검증 — Vertex > Gemini API 키 > CLOVA 우선순위 전환."""

import pytest

from app.infrastructure.config.settings import settings
from evals.conversation_judge import ConversationJudge
from evals.generation_judge import GenerationJudge
from evals.judge_provider import resolve_judge_provider


@pytest.fixture(autouse=True)
def vertex_off(monkeypatch):
    # 로컬 .env에 Vertex 설정이 있어도 테스트 기본값은 비활성으로 고정한다
    monkeypatch.setattr(settings, "google_genai_use_vertexai", False)
    monkeypatch.setattr(settings, "google_cloud_project", "")


@pytest.fixture
def vertex_set(monkeypatch):
    monkeypatch.setattr(settings, "google_genai_use_vertexai", True)
    monkeypatch.setattr(settings, "google_cloud_project", "test-project")
    monkeypatch.setattr(settings, "google_cloud_location", "global")
    # gcloud 호출 없이 토큰을 고정한다
    monkeypatch.setattr("evals.judge_provider._vertex_access_token", lambda: "test-token")


@pytest.fixture
def gemini_key_set(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "test-gemini-key")


@pytest.fixture
def gemini_key_unset(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")
    # CI에는 CLOVA 키가 없고, AsyncOpenAI는 빈 api_key로 생성을 거부한다
    monkeypatch.setattr(settings, "clova_api_key", "test-clova-key")


def test_resolves_vertex_when_configured(vertex_set):
    provider = resolve_judge_provider()
    assert provider.name == "vertex"
    assert provider.api_key == "test-token"
    assert provider.base_url == (
        "https://aiplatform.googleapis.com/v1/projects/test-project"
        "/locations/global/endpoints/openapi"
    )
    assert provider.model == f"google/{settings.gemini_model}"


def test_vertex_regional_location_uses_regional_host(vertex_set, monkeypatch):
    monkeypatch.setattr(settings, "google_cloud_location", "us-central1")
    provider = resolve_judge_provider()
    assert provider.base_url.startswith("https://us-central1-aiplatform.googleapis.com/")


def test_vertex_wins_over_gemini_key(vertex_set, gemini_key_set):
    assert resolve_judge_provider().name == "vertex"


def test_vertex_requires_project(vertex_set, gemini_key_unset, monkeypatch):
    monkeypatch.setattr(settings, "google_cloud_project", "")
    assert resolve_judge_provider().name == "clova"


def test_resolves_gemini_when_key_set(gemini_key_set):
    provider = resolve_judge_provider()
    assert provider.name == "gemini"
    assert provider.api_key == "test-gemini-key"
    assert provider.base_url == settings.gemini_base_url
    assert provider.model == settings.gemini_model


def test_falls_back_to_clova_without_key(gemini_key_unset):
    provider = resolve_judge_provider()
    assert provider.name == "clova"
    assert provider.base_url == settings.clova_base_url
    assert provider.model == settings.clova_model


@pytest.mark.parametrize("judge_cls", [GenerationJudge, ConversationJudge])
def test_judges_use_vertex_when_configured(vertex_set, judge_cls):
    judge = judge_cls()
    assert judge.model == f"google/{settings.gemini_model}"
    assert "aiplatform.googleapis.com" in str(judge._client.base_url)


@pytest.mark.parametrize("judge_cls", [GenerationJudge, ConversationJudge])
def test_judges_use_gemini_when_key_set(gemini_key_set, judge_cls):
    judge = judge_cls()
    assert judge.model == settings.gemini_model
    assert str(judge._client.base_url).startswith(settings.gemini_base_url)


@pytest.mark.parametrize("judge_cls", [GenerationJudge, ConversationJudge])
def test_judges_fall_back_to_clova_without_key(gemini_key_unset, judge_cls):
    judge = judge_cls()
    assert judge.model == settings.clova_model
    assert str(judge._client.base_url).startswith(settings.clova_base_url)


@pytest.mark.parametrize("judge_cls", [GenerationJudge, ConversationJudge])
def test_explicit_model_override_wins(gemini_key_set, judge_cls):
    judge = judge_cls(model="custom-judge-model")
    assert judge.model == "custom-judge-model"
