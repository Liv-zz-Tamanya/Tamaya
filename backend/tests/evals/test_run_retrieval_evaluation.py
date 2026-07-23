"""Retrieval 평가 실행기 테스트 — DB 없이 fake 검색 service로 검증한다."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from evals.retrieval_schemas import RetrievalEvalCase
from evals.run_retrieval_evaluation import (
    ChunkCatalog,
    build_retrieval_report,
    load_retrieval_baseline,
    main,
    run_retrieval_cases,
    score_case,
)
from evals.seed_fixtures import fixture_uuid
from evals.validate_fixtures import FIXTURE_DIR, load_fixture_set


@dataclass
class _Row:
    id: UUID


class _FakeQuery:
    """호출 인자를 기록하고 미리 정한 row를 돌려주는 fake 검색 service."""

    def __init__(self, rows_by_device: dict[str, list[_Row]]) -> None:
        self._rows = rows_by_device
        self.calls: list[tuple[str, str, int]] = []

    async def search_similar(self, device_id: str, query: str, limit: int = 5, **_) -> list[_Row]:
        self.calls.append((device_id, query, limit))
        return self._rows.get(device_id, [])[:limit]


@pytest.fixture(scope="module")
def fixtures():
    return load_fixture_set(FIXTURE_DIR)


@pytest.fixture(scope="module")
def catalog(fixtures):
    return ChunkCatalog(fixtures)


def _diary_case(**overrides) -> RetrievalEvalCase:
    defaults = dict(
        id="ret-test-001", kind="diary", device_id="eval-user-hana",
        query="지민이랑 카페", relevant_chunk_ids=["hana-0602-cafe"], category="direct_recall",
    )
    defaults.update(overrides)
    return RetrievalEvalCase.model_validate(defaults)


def test_score_case_ranks_and_labels(catalog):
    retrieved = [
        fixture_uuid("event-chunk", "hana-0625-jeju"),
        fixture_uuid("event-chunk", "hana-0602-cafe"),
    ]
    result = score_case(_diary_case(), retrieved, catalog, top_k=5)
    assert [doc.label for doc in result.retrieved] == ["hana-0625-jeju", "hana-0602-cafe"]
    assert result.first_relevant_rank == 2
    assert result.hit_at_1 is False and result.hit_at_3 is True
    assert result.reciprocal_rank == 0.5
    assert result.leaked_labels == [] and result.unknown_ids == []


def test_score_case_detects_cross_user_leak(catalog):
    retrieved = [fixture_uuid("event-chunk", "sora-0628-cafe")]
    result = score_case(_diary_case(), retrieved, catalog, top_k=5)
    assert result.leaked_labels == ["sora-0628-cafe"]
    assert result.retrieved[0].leaked_from == "eval-user-sora"


def test_score_case_flags_unknown_rows(catalog):
    stranger = uuid4()
    result = score_case(_diary_case(), [stranger], catalog, top_k=5)
    assert result.unknown_ids == [str(stranger)]
    assert result.retrieved[0].label.startswith("unknown:")


def test_score_case_empty_expected(catalog):
    case = _diary_case(kind="health", device_id="eval-user-sora",
                       relevant_chunk_ids=[], category="empty_retrieval")
    assert score_case(case, [], catalog, top_k=5).empty_check_passed is True
    failed = score_case(case, [fixture_uuid("health-chunk", "health-doyun-0603")], catalog, top_k=5)
    assert failed.empty_check_passed is False
    assert failed.rank_metrics_evaluable is False


async def test_run_retrieval_cases_routes_by_kind(fixtures):
    diary = _FakeQuery({"eval-user-hana": [_Row(fixture_uuid("event-chunk", "hana-0602-cafe"))]})
    health = _FakeQuery({"eval-user-doyun": [_Row(fixture_uuid("health-chunk", "health-doyun-0603"))]})
    cases = [
        _diary_case(),
        _diary_case(id="ret-test-002", kind="health", device_id="eval-user-doyun",
                    query="심박수", relevant_chunk_ids=["health-doyun-0603"]),
    ]
    results = await run_retrieval_cases(cases, diary, health, fixtures, top_k=5)
    assert diary.calls == [("eval-user-hana", "지민이랑 카페", 5)]
    assert health.calls == [("eval-user-doyun", "심박수", 5)]
    assert all(result.hit_at_1 for result in results)


def test_build_report_groups_by_kind_and_category(fixtures, catalog):
    results = [
        score_case(_diary_case(), [fixture_uuid("event-chunk", "hana-0602-cafe")], catalog, 5),
        score_case(
            _diary_case(id="ret-test-002", kind="health", device_id="eval-user-sora",
                        relevant_chunk_ids=[], category="empty_retrieval"),
            [], catalog, 5,
        ),
    ]
    report = build_retrieval_report(results, datetime.now(UTC), 5, "test-embedding-model")
    assert set(report.by_kind) == {"diary", "health"}
    assert set(report.by_category) == {"direct_recall", "empty_retrieval"}
    assert report.summary.case_count == 2
    assert report.embedding_model == "test-embedding-model"


def test_load_retrieval_baseline_rejects_incompatible_file(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="incompatible"):
        load_retrieval_baseline(path)


def test_main_rejects_small_top_k(capsys):
    with pytest.raises(SystemExit):
        main(["--top-k", "3"])


def test_main_requires_baseline_for_fail_on_regression(capsys):
    with pytest.raises(SystemExit):
        main(["--fail-on-regression"])
