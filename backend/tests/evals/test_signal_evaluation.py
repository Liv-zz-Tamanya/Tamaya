"""정성신호 추출 평가 테스트 — CLOVA 없이 scripted fake로 검증한다."""

import pytest

from evals.run_signal_evaluation import (
    build_signal_report,
    main,
    run_signal_cases,
    signal_prompt_hash,
)
from evals.signal_metrics import evaluate_signal_case, summarize_signal_results
from evals.signal_schemas import (
    CoachingSessionFixture,
    default_coaching_path,
    load_coaching_fixtures,
    validate_coaching_fixtures,
)
from evals.validate_fixtures import FIXTURE_DIR, load_fixture_set

FIXTURE = CoachingSessionFixture.model_validate({
    "fixture_id": "coaching-test-01",
    "device_id": "eval-user-hana",
    "messages": [
        {"role": "user", "content": "어제 야식으로 라면 먹고 오늘은 요가 했어."},
        {"role": "assistant", "content": "요가 잘했다냥!"},
    ],
    "plausible_emotions": ["calm", "tired"],
    "gold_behaviors": [
        {"behavior_id": "t-yasik", "surface_forms": ["야식", "라면"], "polarity": -1},
        {"behavior_id": "t-yoga", "surface_forms": ["요가"], "polarity": 1},
    ],
})


class ScriptedSignalService:
    def __init__(self, script: dict[str, dict | None | Exception]) -> None:
        self._script = script
        self.calls = 0

    async def extract_signal(self, messages):
        self.calls += 1
        value = self._script[messages[0].content]
        if isinstance(value, Exception):
            raise value
        return value


def test_shipped_coaching_fixtures_are_valid():
    fixtures = load_fixture_set(FIXTURE_DIR)
    path = default_coaching_path(FIXTURE_DIR)
    sessions, load_errors = load_coaching_fixtures(path)
    assert load_errors == []
    assert len(sessions) >= 10
    assert validate_coaching_fixtures(sessions, fixtures, path) == []
    # 환각 검사용 '행동 없음' 케이스와 상반 polarity 동시 케이스가 존재해야 한다
    assert any(not s.gold_behaviors for s in sessions)
    assert any(
        {b.polarity for b in s.gold_behaviors} == {1, -1} for s in sessions
    )


def test_validator_rejects_violations():
    fixtures = load_fixture_set(FIXTURE_DIR)
    from pathlib import Path

    bad = FIXTURE.model_copy(update={"device_id": "eval-user-ghost"})
    errors = validate_coaching_fixtures([bad], fixtures, Path("x.jsonl"))
    assert any("미등록 device_id" in e for e in errors)
    bad_emotion = FIXTURE.model_copy(update={"plausible_emotions": ["joyful"]})
    errors = validate_coaching_fixtures([bad_emotion], fixtures, Path("x.jsonl"))
    assert any("허용 어휘에 없는 감정" in e for e in errors)
    errors = validate_coaching_fixtures([FIXTURE, FIXTURE], fixtures, Path("x.jsonl"))
    assert any("fixture_id 중복" in e for e in errors)


def test_evaluate_signal_case_matches_and_polarity():
    result = evaluate_signal_case(FIXTURE, {
        "emotion": "calm",
        "behavior_mentions": [
            {"behavior": "야식/라면", "polarity": -1},
            {"behavior": "요가", "polarity": -1},   # polarity 오류
            {"behavior": "등산", "polarity": 1},    # 환각
        ],
    })
    assert result.true_positives == 2
    assert result.false_positives == 1
    assert result.false_negatives == 0
    assert result.hallucinated_behaviors == ["등산"]
    assert [m.polarity_match for m in result.matches] == [True, False]
    assert result.emotion_plausible is True


def test_evaluate_signal_case_missed_and_none():
    missed = evaluate_signal_case(FIXTURE, {"emotion": "angry", "behavior_mentions": []})
    assert missed.false_negatives == 2
    assert missed.emotion_plausible is False
    none_result = evaluate_signal_case(FIXTURE, None)
    assert none_result.extraction_none is True
    assert none_result.false_negatives == 2


def test_summarize_micro_prf():
    perfect = evaluate_signal_case(FIXTURE, {
        "emotion": "calm",
        "behavior_mentions": [
            {"behavior": "야식", "polarity": -1},
            {"behavior": "요가", "polarity": 1},
        ],
    })
    noisy = evaluate_signal_case(FIXTURE, {
        "emotion": "tired",
        "behavior_mentions": [{"behavior": "등산", "polarity": 1}],
    })
    summary = summarize_signal_results([perfect, noisy])
    # TP=2, FP=1, FN=2 → P=2/3, R=2/4
    assert summary.behavior_precision == 0.667
    assert summary.behavior_recall == 0.5
    assert summary.polarity_accuracy == 100.0
    assert summary.hallucination_runs == 1


def test_summarize_empty_contract():
    empty_fixture = FIXTURE.model_copy(update={"fixture_id": "coaching-empty", "gold_behaviors": []})
    passed = evaluate_signal_case(empty_fixture, {"emotion": "calm", "behavior_mentions": []})
    failed = evaluate_signal_case(
        empty_fixture, {"emotion": "calm", "behavior_mentions": [{"behavior": "요가", "polarity": 1}]},
        run_number=2,
    )
    summary = summarize_signal_results([passed, failed], ["coaching-empty"])
    assert summary.empty_contract_cases == 2
    assert summary.empty_contract_passed == 1


async def test_run_signal_cases_full_path():
    ok = FIXTURE
    error_fixture = CoachingSessionFixture.model_validate({
        **FIXTURE.model_dump(),
        "fixture_id": "coaching-test-02",
        "messages": [{"role": "user", "content": "터지는 대화"}],
    })
    service = ScriptedSignalService({
        ok.messages[0].content: {"emotion": "calm", "behavior_mentions": [{"behavior": "요가", "polarity": 1}]},
        "터지는 대화": RuntimeError("provider down"),
    })
    results = await run_signal_cases([ok, error_fixture], service)
    assert results[0].true_positives == 1
    assert results[1].execution_error == "provider down"
    repeated = await run_signal_cases([ok], service, repeat=2)
    assert [r.run_number for r in repeated] == [1, 2]


async def test_build_report_structure():
    service = ScriptedSignalService({
        FIXTURE.messages[0].content: {"emotion": "calm", "behavior_mentions": []},
    })
    results = await run_signal_cases([FIXTURE], service)
    from datetime import UTC, datetime

    report = build_signal_report(results, [FIXTURE], datetime.now(UTC), 1)
    assert report.prompt_hash == signal_prompt_hash()
    assert set(report.by_device) == {"eval-user-hana"}


def test_main_rejects_bad_arguments():
    with pytest.raises(SystemExit):
        main(["--repeat", "0"])
    with pytest.raises(SystemExit):
        main(["--limit", "0"])
