"""judge provider 선택 검증 — GEMINI_API_KEY 유무에 따른 Gemini/CLOVA 전환."""

import pytest

from app.infrastructure.config.settings import settings
from evals.conversation_judge import ConversationJudge
from evals.generation_judge import GenerationJudge
from evals.judge_provider import resolve_judge_provider


@pytest.fixture
def gemini_key_set(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "test-gemini-key")


@pytest.fixture
def gemini_key_unset(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")


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
