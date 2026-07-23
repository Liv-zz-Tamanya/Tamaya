"""일기 생성 평가 실행기 테스트 — CLOVA 없이 scripted fake로 검증한다."""

import pytest

from evals.run_diary_generation_evaluation import (
    build_diary_report,
    diary_prompt_hash,
    main,
    run_diary_generation_cases,
)
from evals.validate_fixtures import FIXTURE_DIR, load_fixture_set
from tests.evals.test_run_chunk_evaluation import SignedFakeEmbedding


class ScriptedDiaryAi:
    """첫 user 발화로 fixture를 식별해 정해둔 일기를 돌려주는 fake."""

    def __init__(self, script: dict[str, dict | Exception]) -> None:
        self._script = script
        self.calls = 0

    async def generate_diary(self, messages) -> dict:
        self.calls += 1
        value = self._script[messages[0].content]
        if isinstance(value, Exception):
            raise value
        return value


@pytest.fixture(scope="module")
def fixtures():
    return load_fixture_set(FIXTURE_DIR)


def test_shipped_diary_fixtures_have_emotion_labels(fixtures):
    assert all(day.plausible_emotions for day in fixtures.diary_days)


def _good_diary_for(day) -> dict:
    # gold chunk 텍스트를 그대로 문장으로 사용(부족하면 순환) → 사건 반영 1.0, 전 문장 grounded.
    # fake embedding은 동일 텍스트만 유사도 1.0이므로 user 발화(복수 문장)로 채우면 안 된다.
    gold_texts = [chunk.text for chunk in day.gold_chunks]
    sentences = [gold_texts[i % len(gold_texts)] for i in range(4)]
    return {
        "title": "오늘의 일기",
        "content": " ".join(sentences),
        "emotion": day.plausible_emotions[0],
        "satisfaction": 70,
        "keywords": [day.gold_chunks[0].tags[0], day.gold_chunks[-1].tags[0]],
    }


async def test_run_diary_cases_full_path(fixtures):
    days = fixtures.diary_days[:3]
    first, second, third = days
    ai = ScriptedDiaryAi({
        first.messages[0].content: _good_diary_for(first),
        second.messages[0].content: ValueError("일기 JSON 파싱 실패: garbage"),
        third.messages[0].content: RuntimeError("provider down"),
    })
    results = await run_diary_generation_cases(days, ai, SignedFakeEmbedding())
    ok, invalid, error = results
    assert ok.event_recall == 1.0
    assert ok.schema_errors == []
    assert ok.sentence_count_ok is True
    assert ok.emotion_plausible is True
    assert ok.ungrounded_sentences == 0
    assert ok.ungrounded_keywords == []
    assert invalid.invalid_json is True
    assert error.execution_error == "provider down"


async def test_run_diary_cases_flags_hallucinated_sentence(fixtures):
    day = fixtures.diary_days[0]
    diary = _good_diary_for(day)
    diary["content"] = diary["content"] + " 저녁에는 우주선을 타고 화성에 다녀왔다."
    ai = ScriptedDiaryAi({day.messages[0].content: diary})
    results = await run_diary_generation_cases([day], ai, SignedFakeEmbedding())
    assert results[0].ungrounded_sentences == 1
    flagged = [s for s in results[0].sentences if s.status == "ungrounded"]
    assert "화성" in flagged[0].sentence


async def test_repeat_runs_each_day(fixtures):
    day = fixtures.diary_days[0]
    ai = ScriptedDiaryAi({day.messages[0].content: _good_diary_for(day)})
    results = await run_diary_generation_cases([day], ai, SignedFakeEmbedding(), repeat=3)
    assert ai.calls == 3
    assert [r.run_number for r in results] == [1, 2, 3]


async def test_build_report_structure(fixtures):
    from datetime import UTC, datetime

    day = fixtures.diary_days[0]
    ai = ScriptedDiaryAi({day.messages[0].content: _good_diary_for(day)})
    results = await run_diary_generation_cases([day], ai, SignedFakeEmbedding())
    report = build_diary_report(results, datetime.now(UTC), 0.55, 1, "test-model")
    assert report.prompt_hash == diary_prompt_hash()
    assert report.prompt_hash.startswith("sha256:")
    assert set(report.by_device) == {day.device_id}


def test_main_rejects_bad_arguments():
    with pytest.raises(SystemExit):
        main(["--repeat", "0"])
    with pytest.raises(SystemExit):
        main(["--threshold", "0"])
