"""생성 평가 실행기 테스트 — CLOVA 없이 fake 모델·judge로 검증한다."""

import json
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage

from evals.generation_judge import JudgeVerdict
from evals.generation_schemas import (
    GenerationEvalCase,
    load_generation_cases,
    validate_generation_cases,
)
from evals.run_generation_evaluation import (
    DATASET_PATH,
    build_generation_messages,
    build_tool_result,
    main,
    run_generation_cases,
)
from evals.validate_fixtures import FIXTURE_DIR, load_fixture_set


class ScriptedModel:
    """case 질문별로 정해둔 AIMessage를 돌려주는 fake ToolCallingChatModel."""

    def __init__(self, script: dict[str, AIMessage | str]) -> None:
        self._script = script
        self.tool_bindings: list[int] = []

    async def ainvoke(self, messages, tools) -> AIMessage:
        self.tool_bindings.append(len(tools))
        question = messages[1].content
        value = self._script[question]
        if isinstance(value, str):
            raise RuntimeError(value)
        return value


class ScriptedJudge:
    def __init__(self, verdict: JudgeVerdict | str = JudgeVerdict()) -> None:
        self._verdict = verdict
        self.calls: list[tuple[str, str, str]] = []

    async def judge(self, documents, question, answer) -> JudgeVerdict:
        self.calls.append((documents, question, answer))
        if isinstance(self._verdict, str):
            raise RuntimeError(self._verdict)
        return self._verdict


@pytest.fixture(scope="module")
def fixtures():
    return load_fixture_set(FIXTURE_DIR)


def _case(**overrides) -> GenerationEvalCase:
    defaults = dict(
        id="gen-test-001", mode="diary", device_id="eval-user-hana",
        question="카페에서 뭐 먹었지?", context_chunk_ids=["hana-0602-cafe"],
        category="grounded_recall", expected_facts=[["케이크"]],
    )
    defaults.update(overrides)
    return GenerationEvalCase.model_validate(defaults)


def test_shipped_generation_dataset_is_valid(fixtures):
    cases, load_errors = load_generation_cases(DATASET_PATH)
    assert load_errors == []
    assert len(cases) >= 15
    assert validate_generation_cases(cases, fixtures, DATASET_PATH) == []
    categories = {case.category.value for case in cases}
    assert {"grounded_recall", "multi_doc_summary", "unsupported_bait",
            "no_record_abstention", "health_boundary"} <= categories


def test_validator_rejects_bad_references(fixtures):
    path = Path("x.jsonl")
    assert any("fixture에 없는" in e for e in validate_generation_cases(
        [_case(context_chunk_ids=["ghost"])], fixtures, path))
    assert any("소유자" in e for e in validate_generation_cases(
        [_case(context_chunk_ids=["sora-0628-cafe"])], fixtures, path))
    assert any("컨텍스트 문서가 필요" in e for e in validate_generation_cases(
        [_case(context_chunk_ids=[])], fixtures, path))
    assert any("비어야" in e for e in validate_generation_cases(
        [_case(category="no_record_abstention", context_chunk_ids=["hana-0602-cafe"],
               expected_facts=[])], fixtures, path))
    assert any("expected_facts가 필요" in e for e in validate_generation_cases(
        [_case(expected_facts=[])], fixtures, path))


def test_build_tool_result_uses_production_wire_format(fixtures):
    result, documents = build_tool_result(_case(), fixtures)
    assert result["count"] == 1
    item = result["items"][0]
    assert item["text"] == "지민이와 성수동에 새로 생긴 카페에 가서 딸기 케이크를 먹었다."
    assert item["diary_date"] == "2026-06-02"
    assert item["who"] == "지민"
    assert "딸기 케이크" in documents


def test_build_tool_result_health(fixtures):
    case = _case(mode="health", context_chunk_ids=["health-hana-0620"],
                 category="grounded_recall", expected_facts=[["3412"]])
    result, documents = build_tool_result(case, fixtures)
    assert result["items"][0]["record_date"] == "2026-06-20"
    assert result["items"][0]["data_types"] == ["steps"]
    assert "3,412걸음" in documents


def test_build_generation_messages_shape(fixtures):
    tool_result, _ = build_tool_result(_case(), fixtures)
    messages = build_generation_messages(_case(), tool_result)
    system, human, ai, tool = messages
    assert "이음이" in system.content or "일기" in system.content
    assert ai.tool_calls[0]["name"] == "search_diary_memories"
    assert ai.tool_calls[0]["id"] == tool.tool_call_id
    assert json.loads(tool.content)["count"] == 1


async def test_run_generation_cases_full_path(fixtures):
    answer_case = _case()
    research_case = _case(id="gen-test-002", question="다른 질문?")
    error_case = _case(id="gen-test-003", question="터지는 질문?")
    model = ScriptedModel({
        answer_case.question: AIMessage(content="지민이랑 딸기 케이크 먹었잖아!"),
        research_case.question: AIMessage(content="", tool_calls=[
            {"name": "search_diary_memories", "args": {"query": "재검색"}, "id": "x", "type": "tool_call"}
        ]),
        error_case.question: "provider down",
    })
    judge = ScriptedJudge()
    results = await run_generation_cases(
        [answer_case, research_case, error_case], fixtures, model, judge)
    answered, re_search, error = results
    assert answered.answered and answered.completeness == 1.0
    assert answered.judge is not None
    assert re_search.re_search and not re_search.answered
    assert error.execution_error == "provider down"
    # 문서가 judge에 전달됐는지
    assert "딸기 케이크" in judge.calls[0][0]
    # diary mode는 tool 2개가 바인딩됨
    assert model.tool_bindings[0] == 2


async def test_run_generation_cases_records_judge_error(fixtures):
    case = _case()
    model = ScriptedModel({case.question: AIMessage(content="케이크 먹었어")})
    results = await run_generation_cases([case], fixtures, model, ScriptedJudge("judge down"))
    assert results[0].judge is None
    assert results[0].judge_error == "judge down"
    assert results[0].completeness == 1.0  # 결정론 지표는 judge와 독립


def test_main_rejects_bad_arguments():
    with pytest.raises(SystemExit):
        main(["--repeat", "0"])
    with pytest.raises(SystemExit):
        main(["--limit", "0"])
