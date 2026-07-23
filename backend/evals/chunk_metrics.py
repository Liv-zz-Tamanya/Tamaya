"""Event Chunk 생성 평가 — 임베딩 유사도 매칭과 누락·환각·과분할·metadata 지표.

gold chunk와 추출 chunk는 표현이 달라도 같은 사건이면 매칭되어야 하므로
문자열 비교가 아니라 임베딩 cosine 유사도 기반 greedy 1:1 매칭을 쓴다.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from evals.chunk_results import (
    ChunkCaseResult,
    ChunkMatch,
    ChunkSummary,
    ExtractedChunk,
    MissedGold,
    UnmatchedExtracted,
)
from evals.fixture_schemas import GoldChunk

# MiniLM 임베딩 보정 결과: 명백한 동일 사건 패러프레이즈가 0.56~0.63에 몰려 있어
# 0.65는 과반을 환각으로 오판했다. 0.55가 현재 임베딩에서 최선의 절충.
# 임베딩 모델을 바꾸면 이 값도 재보정해야 한다.
DEFAULT_SIMILARITY_THRESHOLD = 0.55


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def greedy_match(
    similarity: list[list[float]], threshold: float
) -> list[tuple[int, int, float]]:
    """(gold_index, extracted_index, sim) 목록 — 유사도 내림차순 greedy 1:1 매칭."""
    pairs = sorted(
        (
            (sim, gold_index, extracted_index)
            for gold_index, row in enumerate(similarity)
            for extracted_index, sim in enumerate(row)
            if sim >= threshold
        ),
        reverse=True,
    )
    matched_gold: set[int] = set()
    matched_extracted: set[int] = set()
    matches: list[tuple[int, int, float]] = []
    for sim, gold_index, extracted_index in pairs:
        if gold_index in matched_gold or extracted_index in matched_extracted:
            continue
        matched_gold.add(gold_index)
        matched_extracted.add(extracted_index)
        matches.append((gold_index, extracted_index, round(sim, 3)))
    return matches


def metadata_text_match(gold: str | None, extracted: str | None) -> bool:
    """둘 다 null이면 '언급 없음' 계약을 지킨 것으로 정답. 표기 차이는 포함 관계로 흡수."""
    if gold is None and extracted is None:
        return True
    if gold is None or extracted is None:
        return False
    gold_normalized = gold.strip().lower()
    extracted_normalized = extracted.strip().lower()
    return gold_normalized in extracted_normalized or extracted_normalized in gold_normalized


def analyze_case(
    fixture_id: str,
    device_id: str,
    gold_chunks: Sequence[GoldChunk],
    extracted: Sequence[ExtractedChunk],
    gold_embeddings: Sequence[Sequence[float]],
    extracted_embeddings: Sequence[Sequence[float]],
    threshold: float,
    invalid_rows: int = 0,
    run_number: int = 1,
) -> ChunkCaseResult:
    similarity = [
        [cosine_similarity(gold_embedding, extracted_embedding) for extracted_embedding in extracted_embeddings]
        for gold_embedding in gold_embeddings
    ]
    matches = greedy_match(similarity, threshold)
    matched_gold = {gold_index for gold_index, _, _ in matches}
    matched_extracted = {extracted_index for _, extracted_index, _ in matches}

    match_models = [
        ChunkMatch(
            gold_chunk_id=gold_chunks[gold_index].chunk_id,
            extracted_index=extracted_index,
            extracted_text=extracted[extracted_index].text,
            similarity=sim,
            event_type_match=gold_chunks[gold_index].event_type == extracted[extracted_index].event_type,
            who_match=metadata_text_match(gold_chunks[gold_index].who, extracted[extracted_index].who),
            where_match=metadata_text_match(gold_chunks[gold_index].where, extracted[extracted_index].where),
            when_match=metadata_text_match(gold_chunks[gold_index].when, extracted[extracted_index].when),
        )
        for gold_index, extracted_index, sim in matches
    ]

    missed: list[MissedGold] = []
    for gold_index, gold in enumerate(gold_chunks):
        if gold_index in matched_gold:
            continue
        row = similarity[gold_index]
        best_extracted = max(range(len(row)), key=row.__getitem__, default=None)
        best = round(row[best_extracted], 3) if best_extracted is not None else None
        # 최고 유사 추출문이 이미 다른 정답에 매칭되어 있으면 그쪽에 흡수된 병합 의심
        merged = (
            best_extracted is not None
            and best is not None
            and best >= threshold
            and best_extracted in matched_extracted
        )
        missed.append(MissedGold(chunk_id=gold.chunk_id, text=gold.text, best_similarity=best, merged=merged))

    unmatched: list[UnmatchedExtracted] = []
    for extracted_index, chunk in enumerate(extracted):
        if extracted_index in matched_extracted:
            continue
        column = [similarity[gold_index][extracted_index] for gold_index in range(len(gold_chunks))]
        best_gold = max(range(len(column)), key=column.__getitem__, default=None)
        best = round(column[best_gold], 3) if best_gold is not None else None
        # 이미 매칭된 정답과 임계 이상 유사하면 같은 사건의 중복 추출(과분할)
        over_split = (
            best_gold is not None and best is not None and best >= threshold and best_gold in matched_gold
        )
        unmatched.append(
            UnmatchedExtracted(
                index=extracted_index,
                text=chunk.text,
                best_gold_id=gold_chunks[best_gold].chunk_id if best_gold is not None else None,
                best_similarity=best,
                over_split=over_split,
            )
        )

    return ChunkCaseResult(
        fixture_id=fixture_id,
        device_id=device_id,
        run_number=run_number,
        gold_count=len(gold_chunks),
        extracted_count=len(extracted),
        invalid_rows=invalid_rows,
        matches=match_models,
        missed=missed,
        unmatched=unmatched,
        recall=round(len(matches) / len(gold_chunks), 3) if gold_chunks else None,
        precision=round(len(matches) / len(extracted), 3) if extracted else None,
    )


def summarize_chunk_results(results: Sequence[ChunkCaseResult]) -> ChunkSummary:
    completed = [result for result in results if result.execution_error is None]
    matches = [match for result in completed for match in result.matches]
    return ChunkSummary(
        case_runs=len(results),
        completed_runs=len(completed),
        execution_error_runs=len(results) - len(completed),
        gold_total=sum(result.gold_count for result in completed),
        extracted_total=sum(result.extracted_count for result in completed),
        matched_total=len(matches),
        mean_recall=_mean([result.recall for result in completed]),
        mean_precision=_mean([result.precision for result in completed]),
        missed_total=sum(len(result.missed) for result in completed),
        merged_total=sum(sum(item.merged for item in result.missed) for result in completed),
        over_split_total=sum(sum(item.over_split for item in result.unmatched) for result in completed),
        hallucinated_total=sum(
            sum(not item.over_split for item in result.unmatched) for result in completed
        ),
        invalid_row_total=sum(result.invalid_rows for result in completed),
        mean_similarity=_mean([match.similarity for match in matches]),
        event_type_accuracy=_accuracy([match.event_type_match for match in matches]),
        who_accuracy=_accuracy([match.who_match for match in matches]),
        where_accuracy=_accuracy([match.where_match for match in matches]),
        when_accuracy=_accuracy([match.when_match for match in matches]),
    )


def _mean(values: Sequence[float | None]) -> float | None:
    known = [value for value in values if value is not None]
    return round(sum(known) / len(known), 3) if known else None


def _accuracy(values: Sequence[bool]) -> float | None:
    return round(sum(values) / len(values) * 100, 1) if values else None
