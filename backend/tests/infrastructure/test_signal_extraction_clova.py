"""정성신호 CLOVA 추출 클라이언트 — 방어적 JSON 파싱 + mock 동작 (G002-2, TDD).

extract_event_chunks 패턴을 본떠 mock 모드는 None을 반환하고, real 응답은
코드펜스 제거 → 객체 슬라이스 → json.loads → 구조 검증의 방어적 경로를 거친다.
파싱 실패는 예외 대신 None으로 안전하게 흡수한다(best-effort).
"""

from app.infrastructure.external.signal_extraction_clova import SignalExtractionClovaClient


def _client() -> SignalExtractionClovaClient:
    return SignalExtractionClovaClient()


def test_parse_valid_signal_object():
    raw = '{"emotion": "happy", "behavior_mentions": [{"behavior": "운동", "polarity": 1}]}'
    parsed = _client()._parse_signal_response(raw)
    assert parsed is not None
    assert parsed["emotion"] == "happy"
    assert parsed["behavior_mentions"] == [{"behavior": "운동", "polarity": 1}]


def test_parse_strips_code_fence():
    raw = '```json\n{"emotion": "calm", "behavior_mentions": []}\n```'
    parsed = _client()._parse_signal_response(raw)
    assert parsed is not None
    assert parsed["emotion"] == "calm"
    assert parsed["behavior_mentions"] == []


def test_parse_malformed_json_returns_none():
    assert _client()._parse_signal_response("이건 JSON이 아니야") is None
    assert _client()._parse_signal_response('{"emotion": ') is None


def test_parse_missing_emotion_returns_none():
    # emotion 키가 없거나 비면 신호로 성립하지 않음
    assert _client()._parse_signal_response('{"behavior_mentions": []}') is None
    assert _client()._parse_signal_response('{"emotion": "", "behavior_mentions": []}') is None


def test_parse_drops_malformed_behavior_mentions():
    # polarity가 정수로 강제 불가하거나 behavior가 없는 항목은 제거, 정상 항목만 유지
    raw = (
        '{"emotion": "tired", "behavior_mentions": ['
        '{"behavior": "수면", "polarity": -1},'
        '{"behavior": "산책"},'
        '{"polarity": 1},'
        '{"behavior": "식사", "polarity": "high"}]}'
    )
    parsed = _client()._parse_signal_response(raw)
    assert parsed is not None
    assert parsed["behavior_mentions"] == [{"behavior": "수면", "polarity": -1}]


def test_parse_clamps_polarity_to_unit():
    raw = '{"emotion": "happy", "behavior_mentions": [{"behavior": "운동", "polarity": 5}]}'
    parsed = _client()._parse_signal_response(raw)
    assert parsed["behavior_mentions"][0]["polarity"] == 1


def test_parse_rejects_bool_and_zero_polarity():
    # bool은 int 하위 클래스라 int(False)=0으로 둔갑할 수 있음 — ±1 계약 위반은 모두 폐기
    raw = (
        '{"emotion": "happy", "behavior_mentions": ['
        '{"behavior": "거짓", "polarity": false},'
        '{"behavior": "참", "polarity": true},'
        '{"behavior": "중립", "polarity": 0},'
        '{"behavior": "운동", "polarity": 1}]}'
    )
    parsed = _client()._parse_signal_response(raw)
    assert parsed["behavior_mentions"] == [{"behavior": "운동", "polarity": 1}]


async def test_mock_mode_returns_none(monkeypatch):
    # mock 모드에서는 추출을 건너뛰고 None (대화 흐름을 막지 않음)
    client = _client()
    assert client._mock is True  # 기본값 CLOVA_MOCK_MODE=true
    result = await client.extract_signal([])
    assert result is None
