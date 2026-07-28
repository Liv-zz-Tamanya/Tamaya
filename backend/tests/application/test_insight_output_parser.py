"""INSIGHT 출력 파서 — LLM JSON 계약 검증."""

from __future__ import annotations

import json
from datetime import date

import pytest

from app.application.service.insight_output_parser import InsightOutputError, parse_insight_cards

START = date(2026, 7, 27)
END = date(2026, 8, 2)
ALLOWED = (date(2026, 7, 27), date(2026, 7, 29))
SELECTED = ("sleep_satisfaction", "steps_satisfaction")


def _card(key: str = "sleep_satisfaction", **overrides) -> dict:
    base = {
        "hypothesis_key": key,
        "title": "잠과 만족도의 패턴",
        "message": "함께 나타나는 경향이 있었어요.",
        "evidence_dates": ["2026-07-27"],
    }
    base.update(overrides)
    return base


def _parse(payload, selected=SELECTED, max_cards=2):
    text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    return parse_insight_cards(
        text,
        selected_hypothesis_keys=selected,
        allowed_evidence_dates=ALLOWED,
        period_start=START,
        period_end=END,
        max_cards=max_cards,
    )


def test_valid_output_parsed():
    cards = _parse({"cards": [_card()]})
    assert cards[0].hypothesis_key == "sleep_satisfaction"
    assert cards[0].evidence_dates == (date(2026, 7, 27),)


def test_code_fence_tolerated():
    text = "```json\n" + json.dumps({"cards": [_card()]}, ensure_ascii=False) + "\n```"
    assert len(_parse(text)) == 1


def test_unknown_hypothesis_rejected():
    with pytest.raises(InsightOutputError):
        _parse({"cards": [_card("weekend_mood")]})


def test_unselected_hypothesis_rejected():
    # 쿨다운 등으로 선정에서 제외된 가설은 카드가 될 수 없다
    with pytest.raises(InsightOutputError):
        _parse({"cards": [_card("steps_satisfaction")]}, selected=("sleep_satisfaction",))


def test_duplicate_hypothesis_rejected():
    with pytest.raises(InsightOutputError):
        _parse({"cards": [_card(), _card()]})


def test_card_count_over_limit_rejected():
    with pytest.raises(InsightOutputError):
        _parse(
            {"cards": [_card("sleep_satisfaction"), _card("steps_satisfaction")]},
            selected=SELECTED,
            max_cards=1,
        )


def test_disallowed_evidence_date_rejected():
    with pytest.raises(InsightOutputError):
        _parse({"cards": [_card(evidence_dates=["2026-07-28"])]})  # 기간 안이지만 허용 밖


def test_out_of_period_evidence_date_rejected():
    with pytest.raises(InsightOutputError):
        _parse({"cards": [_card(evidence_dates=["2026-09-01"])]})


def test_blank_title_or_message_rejected():
    with pytest.raises(InsightOutputError):
        _parse({"cards": [_card(title="  ")]})
    with pytest.raises(InsightOutputError):
        _parse({"cards": [_card(message="")]})


def test_over_length_rejected():
    with pytest.raises(InsightOutputError):
        _parse({"cards": [_card(title="가" * 61)]})
    with pytest.raises(InsightOutputError):
        _parse({"cards": [_card(message="가" * 501)]})


def test_malformed_json_rejected():
    with pytest.raises(InsightOutputError):
        _parse("이번 주 인사이트를 알려드릴게요!")


def test_empty_evidence_dates_allowed():
    cards = _parse({"cards": [_card(evidence_dates=[])]})
    assert cards[0].evidence_dates == ()
