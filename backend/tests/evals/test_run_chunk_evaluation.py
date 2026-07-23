"""chunk 평가 실행기 테스트 — CLOVA 호출 없이 scripted fake로 검증한다."""

import hashlib

import pytest

from app.infrastructure.config.settings import settings
from evals.run_chunk_evaluation import (
    _real_extraction_client,
    build_chunk_report,
    chunk_prompt_hash,
    main,
    messages_for_day,
    parse_extracted,
    run_chunk_cases,
)
from evals.validate_fixtures import FIXTURE_DIR, load_fixture_set


class SignedFakeEmbedding:
    """부호 있는 해시 벡터 — 같은 텍스트는 1.0, 다른 텍스트는 ≈0 유사도."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            seed = hashlib.sha256(text.encode("utf-8")).digest()
            expanded = (seed * 12)[:384]
            vectors.append([byte / 127.5 - 1 for byte in expanded])
        return vectors


class ScriptedAi:
    """fixture_id별로 정해둔 chunk를 돌려주는 fake. '!'로 시작하면 예외."""

    def __init__(self, script: dict[str, list[dict] | str]) -> None:
        self._script = script
        self.calls = 0

    async def extract_event_chunks(self, messages) -> list[dict]:
        self.calls += 1
        # 대화 첫 user 발화로 어느 fixture인지 식별
        key = messages[0].content
        value = self._script.get(key, [])
        if isinstance(value, str):
            raise RuntimeError(value)
        return value


@pytest.fixture(scope="module")
def fixtures():
    return load_fixture_set(FIXTURE_DIR)


def test_parse_extracted_filters_contract_violations():
    valid, invalid = parse_extracted([
        {"text": "카페에 갔다.", "tags": ["카페", 3], "event_type": "social", "who": None},
        {"text": "   "},
        {"tags": ["없음"]},
        "not-a-dict",
    ])
    assert len(valid) == 1 and invalid == 3
    assert valid[0].tags == ["카페"]  # 문자열 아닌 태그는 제거


def test_messages_for_day_preserves_roles(fixtures):
    day = fixtures.diary_days[0]
    messages = messages_for_day(day)
    assert [m.role for m in messages] == [m.role for m in day.messages]
    assert messages[0].content == day.messages[0].content


async def test_run_chunk_cases_matches_and_errors(fixtures):
    days = fixtures.diary_days[:2]
    first, second = days
    script = {
        # 첫날: gold 첫 chunk와 동일 텍스트 1건 + 무관한 환각 1건
        first.messages[0].content: [
            {"text": first.gold_chunks[0].text, "tags": [], "event_type": first.gold_chunks[0].event_type,
             "who": first.gold_chunks[0].who, "where": first.gold_chunks[0].where, "when": first.gold_chunks[0].when},
            {"text": "우주선을 타고 화성에 다녀왔다.", "event_type": "personal"},
        ],
        second.messages[0].content: "provider down",
    }
    ai = ScriptedAi(script)
    results = await run_chunk_cases(days, ai, SignedFakeEmbedding(), threshold=0.65)
    assert ai.calls == 2
    ok, error = results
    assert ok.fixture_id == first.fixture_id
    assert len(ok.matches) == 1
    assert ok.matches[0].gold_chunk_id == first.gold_chunks[0].chunk_id
    assert ok.matches[0].similarity == 1.0
    assert ok.matches[0].event_type_match and ok.matches[0].who_match
    hallucinated = [item for item in ok.unmatched if not item.over_split]
    assert len(hallucinated) == 1
    assert len(ok.missed) == len(first.gold_chunks) - 1
    assert error.execution_error == "provider down"
    assert error.gold_count == len(second.gold_chunks)


async def test_run_chunk_cases_repeat_runs_each_day(fixtures):
    day = fixtures.diary_days[0]
    ai = ScriptedAi({day.messages[0].content: []})
    results = await run_chunk_cases([day], ai, SignedFakeEmbedding(), repeat=3)
    assert ai.calls == 3
    assert [result.run_number for result in results] == [1, 2, 3]
    assert all(result.recall == 0.0 for result in results)  # 추출 0건 → 전부 누락


async def test_build_report_structure(fixtures):
    day = fixtures.diary_days[0]
    ai = ScriptedAi({day.messages[0].content: []})
    results = await run_chunk_cases([day], ai, SignedFakeEmbedding())
    from datetime import UTC, datetime

    report = build_chunk_report(results, datetime.now(UTC), 0.65, 1, "test-model")
    assert report.prompt_hash == chunk_prompt_hash()
    assert report.prompt_hash.startswith("sha256:")
    assert set(report.by_device) == {day.device_id}
    assert report.summary.case_runs == 1


def test_real_client_refuses_mock_mode(monkeypatch):
    monkeypatch.setattr(settings, "clova_mock_mode", True)
    with pytest.raises(RuntimeError, match="Real CLOVA credentials"):
        _real_extraction_client()


def test_main_rejects_bad_arguments():
    with pytest.raises(SystemExit):
        main(["--repeat", "0"])
    with pytest.raises(SystemExit):
        main(["--threshold", "1.5"])
