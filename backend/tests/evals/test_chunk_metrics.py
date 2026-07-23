"""chunk 매칭·지표 테스트 — 손으로 만든 임베딩으로 경계를 검증한다."""

from evals.chunk_metrics import (
    analyze_case,
    cosine_similarity,
    greedy_match,
    metadata_text_match,
    summarize_chunk_results,
)
from evals.chunk_results import ChunkCaseResult, ExtractedChunk
from evals.fixture_schemas import GoldChunk


def _gold(chunk_id: str, text: str, **overrides) -> GoldChunk:
    defaults = dict(chunk_id=chunk_id, text=text, tags=["태그"], event_type="social")
    defaults.update(overrides)
    return GoldChunk(**defaults)


def _extracted(text: str, **overrides) -> ExtractedChunk:
    return ExtractedChunk(text=text, **overrides)


def test_cosine_similarity_bounds():
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0
    assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_greedy_match_prefers_higher_similarity_one_to_one():
    #        e0    e1
    # g0   0.9   0.8
    # g1   0.85  0.2
    similarity = [[0.9, 0.8], [0.85, 0.2]]
    matches = greedy_match(similarity, threshold=0.65)
    # g0은 e0(0.9)을 가져가고, g1은 e0이 이미 매칭돼 e1(0.2<threshold)과 매칭 불가
    assert matches == [(0, 0, 0.9), (1, 0, 0.85)] or matches == [(0, 0, 0.9)]
    # 1:1 제약: e0이 두 gold에 동시에 매칭될 수 없다
    assert len({e for _, e, _ in matches}) == len(matches)


def test_greedy_match_threshold_cutoff():
    assert greedy_match([[0.5]], threshold=0.65) == []
    assert greedy_match([[0.65]], threshold=0.65) == [(0, 0, 0.65)]


def test_metadata_text_match_rules():
    assert metadata_text_match(None, None) is True  # 언급 없음을 지킴
    assert metadata_text_match("지민", None) is False
    assert metadata_text_match(None, "지민") is False  # 없는 정보를 지어냄
    assert metadata_text_match("지민", "지민이") is True  # 표기 차이는 포함으로 흡수
    assert metadata_text_match("성수동 카페", "성수동") is True
    assert metadata_text_match("지민", "준호") is False


def test_analyze_case_detects_over_split_and_hallucination():
    gold = [_gold("g0", "지민이와 카페에 갔다.", who="지민", where="카페")]
    extracted = [
        _extracted("지민이랑 카페에 다녀왔다.", event_type="social", who="지민이", where="카페"),
        _extracted("카페에서 지민이와 시간을 보냈다.", event_type="social"),
        _extracted("회사에서 야근했다.", event_type="work"),
    ]
    # g0 ≈ e0(0.95) ≈ e1(0.9), e2는 무관(0.1)
    gold_embeddings = [[1.0, 0.0, 0.0]]
    extracted_embeddings = [[0.95, 0.05, 0.0], [0.9, 0.1, 0.0], [0.0, 0.1, 1.0]]
    result = analyze_case("fx", "dev", gold, extracted, gold_embeddings, extracted_embeddings, 0.65)
    assert len(result.matches) == 1 and result.matches[0].extracted_index == 0
    assert result.matches[0].who_match and result.matches[0].where_match
    over_split = [item for item in result.unmatched if item.over_split]
    hallucinated = [item for item in result.unmatched if not item.over_split]
    assert [item.index for item in over_split] == [1]  # 같은 사건의 중복 추출
    assert [item.index for item in hallucinated] == [2]  # 근거 없는 추출
    assert result.recall == 1.0
    assert result.precision == 0.333


def test_analyze_case_detects_merge():
    # gold 2개가 하나의 추출문에 흡수된 경우: g1은 누락이면서 merged 표시
    gold = [_gold("g0", "카페에 갔다."), _gold("g1", "야근을 했다.")]
    extracted = [_extracted("카페에 갔고 야근도 했다.")]
    gold_embeddings = [[1.0, 0.2], [0.9, 0.3]]
    extracted_embeddings = [[1.0, 0.25]]
    result = analyze_case("fx", "dev", gold, extracted, gold_embeddings, extracted_embeddings, 0.65)
    assert len(result.matches) == 1
    assert len(result.missed) == 1
    assert result.missed[0].chunk_id == "g1"
    assert result.missed[0].merged is True


def test_analyze_case_counts_missed_without_extraction():
    gold = [_gold("g0", "카페에 갔다.")]
    result = analyze_case("fx", "dev", gold, [], [[1.0, 0.0]], [], 0.65)
    assert result.recall == 0.0
    assert result.precision is None
    assert result.missed[0].merged is False


def test_summarize_aggregates_and_counts_errors():
    ok = analyze_case(
        "fx1", "dev",
        [_gold("g0", "카페")], [_extracted("카페", event_type="social")],
        [[1.0]], [[1.0]], 0.65,
    )
    error = ChunkCaseResult(fixture_id="fx2", device_id="dev", execution_error="boom", gold_count=2)
    summary = summarize_chunk_results([ok, error])
    assert summary.case_runs == 2
    assert summary.execution_error_runs == 1
    assert summary.gold_total == 1  # 오류 실행은 집계에서 제외
    assert summary.matched_total == 1
    assert summary.event_type_accuracy == 100.0
    assert summary.mean_recall == 1.0
