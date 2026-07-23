"""E2E 러너 테스트 — 실제 agent 그래프 + scripted 모델·fake 검색으로 검증한다."""

from datetime import datetime

import pytest
from langchain_core.messages import AIMessage

from app.domain.model.event_chunk import EventChunk
from evals.e2e_results import E2EFailureStage
from evals.e2e_schemas import E2EEvalCase, load_e2e_cases, validate_e2e_cases
from evals.generation_judge import JudgeVerdict
from evals.run_e2e_evaluation import (
    DATASET_PATH,
    RecordingDiaryQuery,
    RecordingHealthQuery,
    build_document_text,
    main,
    resolve_retrieval,
    run_e2e_cases,
)
from evals.run_retrieval_evaluation import ChunkCatalog
from evals.seed_fixtures import fixture_uuid
from evals.validate_fixtures import FIXTURE_DIR, load_fixture_set


class ScriptedModel:
    """tool 결과가 없으면 tool_call, 있으면 최종 답변을 돌려주는 fake."""

    def __init__(self, tool_name: str | None, answer: str) -> None:
        self._tool_name = tool_name
        self._answer = answer

    async def ainvoke(self, messages, tools) -> AIMessage:
        has_tool_result = any(message.type == "tool" for message in messages)
        if self._tool_name and not has_tool_result:
            return AIMessage(content="", tool_calls=[
                {"name": self._tool_name, "args": {"query": "검색어"}, "id": "call-1", "type": "tool_call"}
            ])
        return AIMessage(content=self._answer)


class FakeInnerDiary:
    def __init__(self, chunk_ids: list[str], fixtures) -> None:
        chunk_map = {
            chunk.chunk_id: (day, chunk)
            for day in fixtures.diary_days
            for chunk in day.gold_chunks
        }
        self._rows = [
            EventChunk(
                id=fixture_uuid("event-chunk", chunk_id),
                chat_session_id=fixture_uuid("chat-session", "x"),
                diary_date=chunk_map[chunk_id][0].session_date,
                text=chunk_map[chunk_id][1].text,
                embedding=[], tags=chunk_map[chunk_id][1].tags,
                event_type=chunk_map[chunk_id][1].event_type,
                created_at=datetime(2026, 6, 1),
            )
            for chunk_id in chunk_ids
        ]

    async def search_similar(self, device_id, query, exclude_session_id=None, limit=5):
        return self._rows[:limit]


class FakeInnerHealth:
    async def search_similar(self, device_id, query, limit=5):
        return []


class FakeJudge:
    def __init__(self, verdict: JudgeVerdict) -> None:
        self._verdict = verdict
        self.calls: list[tuple[str, str, str]] = []

    async def judge(self, documents, question, answer) -> JudgeVerdict:
        self.calls.append((documents, question, answer))
        return self._verdict


@pytest.fixture(scope="module")
def fixtures():
    return load_fixture_set(FIXTURE_DIR)


def _case(**overrides) -> E2EEvalCase:
    defaults = dict(
        id="e2e-test-001", mode="diary", device_id="eval-user-hana",
        input="지민이랑 카페 갔던 날 기억나?", expected_decision="TOOL_CALL",
        expected_tools=["search_diary_memories"], forbidden_tools=["search_health_records"],
        relevant_chunk_ids=["hana-0602-cafe"], expected_facts=[["케이크"]],
        category="grounded_recall",
    )
    defaults.update(overrides)
    return E2EEvalCase.model_validate(defaults)


def test_shipped_e2e_dataset_is_valid(fixtures):
    cases, load_errors = load_e2e_cases(DATASET_PATH)
    assert load_errors == []
    assert len(cases) >= 12
    assert validate_e2e_cases(cases, fixtures, DATASET_PATH) == []
    decisions = {case.expected_decision.value for case in cases}
    assert decisions == {"TOOL_CALL", "NO_TOOL"}
    assert any(case.category == "empty_retrieval" for case in cases)


def test_validator_rejects_contract_violations(fixtures):
    from pathlib import Path

    path = Path("x.jsonl")
    assert any("expected_tools가 필요" in e for e in validate_e2e_cases(
        [_case(expected_tools=[])], fixtures, path))
    assert any("둘 수 없습니다" in e for e in validate_e2e_cases(
        [_case(expected_decision="NO_TOOL", expected_tools=[])], fixtures, path))
    assert any("소유자" in e for e in validate_e2e_cases(
        [_case(relevant_chunk_ids=["sora-0628-cafe"], expected_facts=[["논문"]])], fixtures, path))
    assert any("호출을 기대해야" in e for e in validate_e2e_cases(
        [_case(relevant_chunk_ids=["health-hana-0620"])], fixtures, path))


def test_resolve_retrieval_maps_leaks_and_unknowns(fixtures):
    catalog = ChunkCatalog(fixtures)
    calls = [{
        "tool": "search_diary_memories", "query": "카페",
        "ids": [
            fixture_uuid("event-chunk", "hana-0602-cafe"),
            fixture_uuid("event-chunk", "sora-0628-cafe"),
            fixture_uuid("event-chunk", "ghost"),
        ],
    }]
    traces, labels, leaked, unknown = resolve_retrieval(calls, catalog, "eval-user-hana")
    assert traces[0].result_count == 3 and traces[0].query == "카페"
    assert labels == ["hana-0602-cafe", "sora-0628-cafe"]
    assert leaked == ["sora-0628-cafe"]
    assert len(unknown) == 1


async def test_run_e2e_pass_path(fixtures):
    diary = RecordingDiaryQuery(FakeInnerDiary(["hana-0602-cafe"], fixtures))
    health = RecordingHealthQuery(FakeInnerHealth())
    judge = FakeJudge(JudgeVerdict())
    results = await run_e2e_cases(
        [_case()], fixtures,
        ScriptedModel("search_diary_memories", "그날 딸기 케이크 먹었잖아!"),
        judge, diary, health,
    )
    result = results[0]
    assert result.stage == E2EFailureStage.PASS and result.passed
    assert result.actual_tools == ["search_diary_memories"]
    assert result.tool_queries[0].query == "검색어"
    assert result.retrieved_labels == ["hana-0602-cafe"]
    assert result.completeness == 1.0
    assert "딸기 케이크" in judge.calls[0][0]  # 검색된 문서가 judge에 전달됨


async def test_run_e2e_retrieval_miss(fixtures):
    diary = RecordingDiaryQuery(FakeInnerDiary(["hana-0625-jeju"], fixtures))
    health = RecordingHealthQuery(FakeInnerHealth())
    results = await run_e2e_cases(
        [_case()], fixtures,
        ScriptedModel("search_diary_memories", "지민이랑 제주도 여행 가기로 했었네!"),
        FakeJudge(JudgeVerdict()), diary, health,
    )
    assert results[0].stage == E2EFailureStage.RETRIEVAL_MISS
    assert results[0].missing_relevant == ["hana-0602-cafe"]


async def test_run_e2e_no_tool_paths(fixtures):
    no_tool_case = _case(
        id="e2e-test-002", input="오늘 좀 피곤했어.", expected_decision="NO_TOOL",
        expected_tools=[], relevant_chunk_ids=[], expected_facts=[],
        category="present_reflection",
    )
    diary = RecordingDiaryQuery(FakeInnerDiary([], fixtures))
    health = RecordingHealthQuery(FakeInnerHealth())
    ok = await run_e2e_cases(
        [no_tool_case], fixtures, ScriptedModel(None, "그랬구나, 오늘 푹 쉬어."),
        FakeJudge(JudgeVerdict()), diary, health,
    )
    assert ok[0].stage == E2EFailureStage.PASS
    over = await run_e2e_cases(
        [no_tool_case], fixtures,
        ScriptedModel("search_diary_memories", "찾아봤어!"),
        FakeJudge(JudgeVerdict()), diary, health,
    )
    assert over[0].stage == E2EFailureStage.TOOL_OVER_CALL


async def test_run_e2e_abstention_fail(fixtures):
    case = _case(
        id="e2e-test-003", mode="health", device_id="eval-user-sora",
        input="지난주 걸음수 알려줘", expected_tools=["search_health_records"],
        forbidden_tools=[], relevant_chunk_ids=[], expected_facts=[],
        category="empty_retrieval",
    )
    diary = RecordingDiaryQuery(FakeInnerDiary([], fixtures))
    health = RecordingHealthQuery(FakeInnerHealth())
    results = await run_e2e_cases(
        [case], fixtures,
        ScriptedModel("search_health_records", "지난주에 8,000걸음 걸었어!"),
        FakeJudge(JudgeVerdict(abstained=False, unsupported_claims=["8,000걸음"])),
        diary, health,
    )
    assert results[0].stage == E2EFailureStage.ABSTENTION_FAIL


def test_build_document_text_covers_both_kinds(fixtures):
    text = build_document_text(fixtures, ["hana-0602-cafe", "health-hana-0620"])
    assert "딸기 케이크" in text and "3,412걸음" in text


def test_main_rejects_bad_arguments():
    with pytest.raises(SystemExit):
        main(["--repeat", "0"])
    with pytest.raises(SystemExit):
        main(["--limit", "0"])
