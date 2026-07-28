"""INSIGHT Agent 출력 파서 — LLM JSON을 검증해 InsightCard로 변환한다.

파싱 실패·계약 위반은 InsightOutputError로 명시적으로 실패시킨다.
잘못된 payload를 캐시에 저장하거나 LLM repair 재호출을 하지 않는다
(모델 retry는 provider retry 정책만 사용).
"""

import json
from collections.abc import Collection
from datetime import date

from app.domain.model.insight_report import InsightCard

MAX_CARD_TITLE_LENGTH = 60
MAX_CARD_MESSAGE_LENGTH = 500


class InsightOutputError(ValueError):
    """LLM 출력이 인사이트 카드 계약을 위반했다."""


def parse_insight_cards(
    raw_text: str,
    *,
    selected_hypothesis_keys: Collection[str],
    allowed_evidence_dates: Collection[date],
    period_start: date,
    period_end: date,
    max_cards: int,
) -> tuple[InsightCard, ...]:
    data = _parse_json_object(raw_text)

    cards_raw = data.get("cards")
    if not isinstance(cards_raw, list):
        raise InsightOutputError("cards는 list여야 합니다")
    if len(cards_raw) > max_cards:
        raise InsightOutputError(f"카드는 최대 {max_cards}개입니다: {len(cards_raw)}개")
    if len(cards_raw) > len(set(selected_hypothesis_keys)):
        raise InsightOutputError("카드 수가 선정 후보 수를 초과했습니다")

    selected = set(selected_hypothesis_keys)
    allowed_dates = set(allowed_evidence_dates)
    cards: list[InsightCard] = []
    seen_keys: set[str] = set()
    for card_raw in cards_raw:
        if not isinstance(card_raw, dict):
            raise InsightOutputError("card는 object여야 합니다")
        key = card_raw.get("hypothesis_key")
        if not isinstance(key, str) or key not in selected:
            raise InsightOutputError(f"선정되지 않은 hypothesis_key입니다: {key!r}")
        if key in seen_keys:
            raise InsightOutputError(f"같은 hypothesis의 중복 카드: {key}")
        seen_keys.add(key)

        title = _required_text(card_raw, "title", MAX_CARD_TITLE_LENGTH)
        message = _required_text(card_raw, "message", MAX_CARD_MESSAGE_LENGTH)
        evidence_dates = _parse_evidence_dates(
            card_raw.get("evidence_dates", []), allowed_dates, period_start, period_end
        )
        cards.append(
            InsightCard(
                hypothesis_key=key,
                title=title,
                message=message,
                evidence_dates=evidence_dates,
            )
        )
    return tuple(cards)


def _parse_json_object(raw_text: str) -> dict:
    text = raw_text.strip()
    # 프롬프트는 code fence를 금지하지만 방어적으로 제거한다(clova_client 패턴)
    if text.startswith("```"):
        text = text.split("```")[1].replace("json", "", 1).strip()
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last != -1:
        text = text[first : last + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InsightOutputError(f"인사이트 출력 JSON 파싱 실패: {raw_text[:200]}") from exc
    if not isinstance(data, dict):
        raise InsightOutputError("인사이트 출력은 JSON object여야 합니다")
    return data


def _required_text(card_raw: dict, field: str, max_length: int) -> str:
    value = card_raw.get(field)
    if not isinstance(value, str) or not value.strip():
        raise InsightOutputError(f"{field}은(는) 비어 있을 수 없습니다")
    value = value.strip()
    if len(value) > max_length:
        raise InsightOutputError(f"{field}이(가) {max_length}자를 초과했습니다")
    return value


def _parse_evidence_dates(
    raw_dates: object,
    allowed_dates: set[date],
    period_start: date,
    period_end: date,
) -> tuple[date, ...]:
    if not isinstance(raw_dates, list):
        raise InsightOutputError("evidence_dates는 list여야 합니다")
    parsed: list[date] = []
    for raw in raw_dates:
        if not isinstance(raw, str):
            raise InsightOutputError("evidence_dates 항목은 YYYY-MM-DD 문자열이어야 합니다")
        try:
            day = date.fromisoformat(raw)
        except ValueError as exc:
            raise InsightOutputError(f"잘못된 evidence date: {raw!r}") from exc
        if not period_start <= day <= period_end:
            raise InsightOutputError(f"기간 밖 evidence date: {raw}")
        if day not in allowed_dates:
            raise InsightOutputError(f"허용되지 않은 evidence date: {raw}")
        parsed.append(day)
    return tuple(parsed)
