"""정성신호 추출 지표 — behavior P/R/F1, polarity 정확도, 감정 타당성, 환각."""

from __future__ import annotations

from collections.abc import Sequence

from evals.signal_results import BehaviorMatch, SignalCaseResult, SignalSummary
from evals.signal_schemas import CoachingSessionFixture


def _normalize(text: str) -> str:
    return "".join(text.split()).lower()


def _behavior_matches_form(extracted: str, surface_form: str) -> bool:
    left = _normalize(extracted)
    right = _normalize(surface_form)
    return bool(left) and bool(right) and (left in right or right in left)


def evaluate_signal_case(
    fixture: CoachingSessionFixture,
    extracted: dict | None,
    run_number: int = 1,
) -> SignalCaseResult:
    if extracted is None:
        # 클라이언트가 파싱 실패를 None으로 흡수한 경우 — 모든 gold가 미검출
        return SignalCaseResult(
            fixture_id=fixture.fixture_id,
            device_id=fixture.device_id,
            run_number=run_number,
            extraction_none=True,
            missed_behavior_ids=[b.behavior_id for b in fixture.gold_behaviors],
            false_negatives=len(fixture.gold_behaviors),
        )
    emotion = extracted.get("emotion")
    mentions = extracted.get("behavior_mentions") or []
    matched_gold: set[str] = set()
    matches: list[BehaviorMatch] = []
    hallucinated: list[str] = []
    for mention in mentions:
        behavior = mention.get("behavior", "")
        polarity = mention.get("polarity", 0)
        found = None
        for gold in fixture.gold_behaviors:
            if gold.behavior_id in matched_gold:
                continue
            if any(_behavior_matches_form(behavior, form) for form in gold.surface_forms):
                found = gold
                break
        if found is None:
            hallucinated.append(behavior)
            continue
        matched_gold.add(found.behavior_id)
        matches.append(
            BehaviorMatch(
                behavior_id=found.behavior_id,
                extracted_behavior=behavior,
                gold_polarity=found.polarity,
                extracted_polarity=polarity,
                polarity_match=polarity == found.polarity,
            )
        )
    missed = [b.behavior_id for b in fixture.gold_behaviors if b.behavior_id not in matched_gold]
    return SignalCaseResult(
        fixture_id=fixture.fixture_id,
        device_id=fixture.device_id,
        run_number=run_number,
        extracted_emotion=emotion,
        emotion_plausible=emotion in fixture.plausible_emotions if emotion else False,
        matches=matches,
        missed_behavior_ids=missed,
        hallucinated_behaviors=hallucinated,
        true_positives=len(matches),
        false_positives=len(hallucinated),
        false_negatives=len(missed),
    )


def summarize_signal_results(
    results: Sequence[SignalCaseResult],
    empty_gold_fixture_ids: Sequence[str] = (),
) -> SignalSummary:
    completed = [r for r in results if r.execution_error is None and not r.extraction_none]
    tp = sum(r.true_positives for r in completed)
    fp = sum(r.false_positives for r in completed)
    fn = sum(r.false_negatives for r in completed) + sum(
        r.false_negatives for r in results if r.extraction_none
    )
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall > 0
        else None
    )
    polarity_values = [match.polarity_match for r in completed for match in r.matches]
    emotion_values = [r.emotion_plausible for r in completed if r.emotion_plausible is not None]
    empty_set = set(empty_gold_fixture_ids)
    empty_runs = [r for r in completed if r.fixture_id in empty_set]
    return SignalSummary(
        case_runs=len(results),
        completed_runs=len(completed),
        execution_error_runs=sum(r.execution_error is not None for r in results),
        extraction_none_runs=sum(r.extraction_none for r in results),
        behavior_precision=round(precision, 3) if precision is not None else None,
        behavior_recall=round(recall, 3) if recall is not None else None,
        behavior_f1=round(f1, 3) if f1 is not None else None,
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        polarity_accuracy=(
            round(sum(polarity_values) / len(polarity_values) * 100, 1)
            if polarity_values
            else None
        ),
        emotion_plausible_rate=(
            round(sum(emotion_values) / len(emotion_values) * 100, 1) if emotion_values else None
        ),
        hallucination_runs=sum(bool(r.hallucinated_behaviors) for r in completed),
        empty_contract_cases=len(empty_runs),
        empty_contract_passed=sum(not r.false_positives for r in empty_runs),
    )
