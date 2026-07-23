"""일기 생성 지표 테스트 — 손으로 만든 임베딩으로 grounding 분류를 검증한다."""

from evals.diary_generation_metrics import (
    analyze_diary_case,
    parse_diary_output,
    split_sentences,
    summarize_diary_results,
)
from evals.diary_generation_results import DiaryCaseResult
from evals.fixture_schemas import DiaryDayFixture

DAY = DiaryDayFixture.model_validate({
    "fixture_id": "diary-test-0601",
    "device_id": "eval-user-test",
    "session_date": "2026-06-01",
    "messages": [
        {"role": "user", "content": "오늘 공원에 갔어."},
        {"role": "assistant", "content": "산책하면 마음이 편해지지. 나도 공원을 좋아해."},
    ],
    "gold_chunks": [
        {"chunk_id": "test-park", "text": "공원에 갔다.", "tags": ["공원"], "event_type": "personal"}
    ],
    "plausible_emotions": ["calm", "happy"],
})

VALID_OUTPUT = {
    "title": "공원에 간 날",
    "content": "오늘은 공원에 갔다. 날씨가 좋았다. 기분이 편안했다. 내일도 가고 싶다.",
    "emotion": "calm",
    "satisfaction": 70,
    "keywords": ["공원", "산책"],
}


def test_split_sentences():
    assert split_sentences("첫 문장이다. 둘째다! 셋째인가? 넷째다.") == [
        "첫 문장이다.", "둘째다!", "셋째인가?", "넷째다.",
    ]
    assert split_sentences("") == []


def test_parse_diary_output_accepts_contract():
    fields, errors = parse_diary_output(VALID_OUTPUT)
    assert errors == []
    assert fields["emotion"] == "calm" and fields["satisfaction"] == 70


def test_parse_diary_output_reports_violations():
    _, errors = parse_diary_output({
        "title": " ", "content": "본문.", "emotion": "joyful",
        "satisfaction": True, "keywords": ["a", "b", "c", "d"],
    })
    joined = " ".join(errors)
    assert "title" in joined
    assert "emotion" in joined
    assert "satisfaction" in joined
    assert "keywords 개수" in joined


def _analyze(sentences, sentence_embeddings, **overrides):
    defaults = dict(
        day=DAY,
        fields={"emotion": "calm", "keywords": ["공원", "산책"], "content": " ".join(sentences)},
        schema_errors=[],
        sentence_embeddings=sentence_embeddings,
        gold_embeddings=[[1.0, 0.0, 0.0]],
        user_embeddings=[[0.9, 0.1, 0.0]],
        assistant_embeddings=[[0.0, 1.0, 0.0]],
        sentences=sentences,
        threshold=0.55,
    )
    defaults.update(overrides)
    return analyze_diary_case(**defaults)


def test_analyze_classifies_sentence_grounding():
    sentences = ["공원에 갔다.", "산책하면 마음이 편해진다.", "우주선을 탔다.", "좋은 하루였다."]
    result = _analyze(
        sentences,
        sentence_embeddings=[
            [1.0, 0.0, 0.0],   # gold와 일치 → grounded
            [0.0, 0.95, 0.0],  # assistant 발화에만 근거 → 혼동 의심
            [0.0, 0.0, 1.0],   # 어디에도 근거 없음 → ungrounded
            [0.85, 0.1, 0.0],  # user 발화 근거 → grounded
        ],
    )
    statuses = [item.status for item in result.sentences]
    assert statuses == ["grounded", "assistant_only", "ungrounded", "grounded"]
    assert result.event_recall == 1.0
    assert result.assistant_confusion_sentences == 1
    assert result.ungrounded_sentences == 1
    assert result.sentence_count_ok is True
    assert result.emotion_plausible is True


def test_analyze_detects_missed_event_and_keywords():
    sentences = ["아무 관련 없는 문장이다."]
    result = _analyze(
        sentences,
        sentence_embeddings=[[0.0, 0.0, 1.0]],
        fields={"emotion": "angry", "keywords": ["오늘", "우주여행"], "content": sentences[0]},
    )
    assert result.event_coverage[0].covered is False
    assert result.event_recall == 0.0
    assert result.sentence_count_ok is False  # 1문장
    assert result.emotion_plausible is False
    assert result.generic_keywords == ["오늘"]
    assert result.ungrounded_keywords == ["우주여행"]


def test_summarize_diary_results():
    ok = _analyze(["공원에 갔다."], sentence_embeddings=[[1.0, 0.0, 0.0]])
    invalid = DiaryCaseResult(fixture_id="x", device_id="d", invalid_json=True)
    error = DiaryCaseResult(fixture_id="y", device_id="d", execution_error="boom")
    summary = summarize_diary_results([ok, invalid, error])
    assert summary.case_runs == 3
    assert summary.completed_runs == 1
    assert summary.invalid_json_runs == 1
    assert summary.execution_error_runs == 1
    assert summary.mean_event_recall == 1.0
    assert summary.emotion_plausible_rate == 100.0
