"""CoachingSession 도메인 어그리거트 — 격리 불변식 (G001-2, TDD).

diary의 ChatSession과 분리된 코칭 전용 어그리거트. device_id 키잉,
동적 RoutineSuggestion emit, finalize 강제 없음.
"""

import pytest

from app.domain.model.coaching_session import CoachingSession
from app.domain.model.routine import RoutineKind, RoutineSuggestion


def test_requires_device_id():
    with pytest.raises(TypeError):
        CoachingSession()  # device_id 필수


def test_created_with_device_id():
    session = CoachingSession(device_id="dev-123")
    assert session.device_id == "dev-123"
    assert session.id is not None
    assert session.messages == []
    assert session.routine_suggestions == []


def test_add_message_returns_chat_message():
    session = CoachingSession(device_id="d")
    message = session.add_message("user", "요즘 잠을 잘 못 자")
    assert message.role == "user"
    assert message.content == "요즘 잠을 잘 못 자"
    assert len(session.messages) == 1


def test_add_routine_suggestion():
    session = CoachingSession(device_id="d")
    suggestion = session.add_routine_suggestion(RoutineKind.SLEEP, "11시 전에 불 끄고 눕기")
    assert isinstance(suggestion, RoutineSuggestion)
    assert suggestion.kind == RoutineKind.SLEEP
    assert suggestion.nudge_text == "11시 전에 불 끄고 눕기"
    assert len(session.routine_suggestions) == 1


def test_routine_kind_has_four_kinds():
    assert set(RoutineKind) == {
        RoutineKind.SLEEP,
        RoutineKind.MEAL,
        RoutineKind.EXERCISE,
        RoutineKind.MEDICATION,
    }


def test_no_diary_finalize_coupling():
    # 코칭 어그리거트는 diary의 정리-강제 불변식을 상속하지 않는다
    session = CoachingSession(device_id="d")
    assert not hasattr(session, "finalize")
    assert not hasattr(session, "should_suggest_finalize")
