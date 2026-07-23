"""Retrieval 데이터셋 검증기 테스트."""

from pathlib import Path

from evals.retrieval_schemas import RetrievalEvalCase
from evals.validate_fixtures import FIXTURE_DIR, load_fixture_set
from evals.validate_retrieval_dataset import (
    DATASET_DIR,
    RETRIEVAL_DATASET_FILENAME,
    load_retrieval_cases,
    validate_retrieval_cases,
)

DATASET_PATH = DATASET_DIR / RETRIEVAL_DATASET_FILENAME


def _case(**overrides) -> RetrievalEvalCase:
    defaults = dict(
        id="ret-test-001",
        kind="diary",
        device_id="eval-user-hana",
        query="테스트 질의",
        relevant_chunk_ids=["hana-0602-cafe"],
        category="direct_recall",
    )
    defaults.update(overrides)
    return RetrievalEvalCase.model_validate(defaults)


def test_shipped_retrieval_dataset_is_valid():
    fixtures = load_fixture_set(FIXTURE_DIR)
    cases, load_errors = load_retrieval_cases(DATASET_PATH)
    assert load_errors == []
    assert len(cases) >= 25
    assert validate_retrieval_cases(cases, fixtures, DATASET_PATH) == []
    # 로드맵 요구 시나리오가 데이터셋에 실제로 존재하는지 고정
    categories = {case.category for case in cases}
    assert {"direct_recall", "paraphrase_recall", "multi_relevant", "hard_negative",
            "cross_user_probe", "empty_retrieval"} <= categories
    assert any(case.kind.value == "health" for case in cases)


def test_unknown_chunk_reference_is_reported():
    fixtures = load_fixture_set(FIXTURE_DIR)
    errors = validate_retrieval_cases(
        [_case(relevant_chunk_ids=["no-such-chunk"])], fixtures, Path("x.jsonl")
    )
    assert any("fixture에 없는" in error for error in errors)


def test_cross_device_answer_is_reported():
    # 하나의 케이스가 소라 소유 chunk를 정답으로 참조하면 오류
    fixtures = load_fixture_set(FIXTURE_DIR)
    errors = validate_retrieval_cases(
        [_case(relevant_chunk_ids=["sora-0628-cafe"])], fixtures, Path("x.jsonl")
    )
    assert any("소유자" in error for error in errors)


def test_health_answer_in_diary_case_is_reported():
    fixtures = load_fixture_set(FIXTURE_DIR)
    errors = validate_retrieval_cases(
        [_case(relevant_chunk_ids=["health-hana-0620"])], fixtures, Path("x.jsonl")
    )
    assert any("fixture에 없는 diary 정답" in error for error in errors)


def test_empty_answers_require_user_without_data():
    fixtures = load_fixture_set(FIXTURE_DIR)
    # 하나는 diary 데이터가 있으므로 빈 정답 케이스가 될 수 없다
    errors = validate_retrieval_cases([_case(relevant_chunk_ids=[])], fixtures, Path("x.jsonl"))
    assert any("빈 정답" in error for error in errors)
    # 소라는 health 데이터가 없으므로 빈 정답이 성립한다
    ok = validate_retrieval_cases(
        [_case(kind="health", device_id="eval-user-sora", relevant_chunk_ids=[],
               category="empty_retrieval")],
        fixtures,
        Path("x.jsonl"),
    )
    assert ok == []


def test_duplicate_case_id_is_reported():
    fixtures = load_fixture_set(FIXTURE_DIR)
    errors = validate_retrieval_cases([_case(), _case()], fixtures, Path("x.jsonl"))
    assert any("id 중복" in error for error in errors)


def test_unknown_device_is_reported():
    fixtures = load_fixture_set(FIXTURE_DIR)
    errors = validate_retrieval_cases(
        [_case(device_id="eval-user-ghost")], fixtures, Path("x.jsonl")
    )
    assert any("미등록 device_id" in error for error in errors)
