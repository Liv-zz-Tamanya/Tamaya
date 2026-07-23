"""일기 생성 품질 지표 — 계약 검사(결정론)와 문장 단위 grounding 분석.

핵심 사건 반영(gold chunk ↔ 본문 문장), 원문에 없는 사건(ungrounded 문장),
사용자/assistant 발화 혼동(assistant 발화에만 근거한 문장)을 임베딩 유사도로
분류한다. threshold는 chunk 평가와 동일한 보정값을 쓴다.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from app.application.service.diary_generation_prompt import DIARY_EMOTIONS
from evals.chunk_metrics import cosine_similarity
from evals.diary_generation_results import (
    DiaryCaseResult,
    DiarySummary,
    EventCoverage,
    SentenceGrounding,
)
from evals.fixture_schemas import DiaryDayFixture

GENERIC_KEYWORDS = frozenset({"오늘", "기분", "생각", "하루"})
MIN_SENTENCES = 4
MAX_SENTENCES = 5
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?…])\s+")


def split_sentences(text: str) -> list[str]:
    return [sentence.strip() for sentence in _SENTENCE_BOUNDARY.split(text.strip()) if sentence.strip()]


def parse_diary_output(raw: object) -> tuple[dict, list[str]]:
    """생성 JSON을 계약 대비 검사한다. (정규화된 필드, 위반 목록) 반환."""
    errors: list[str] = []
    if not isinstance(raw, dict):
        return {}, ["출력이 JSON 객체가 아닙니다"]
    fields: dict = {}
    title = raw.get("title")
    if isinstance(title, str) and title.strip():
        fields["title"] = title.strip()
    else:
        errors.append("title 누락 또는 빈 값")
    content = raw.get("content")
    if isinstance(content, str) and content.strip():
        fields["content"] = content.strip()
    else:
        errors.append("content 누락 또는 빈 값")
    emotion = raw.get("emotion")
    if isinstance(emotion, str) and emotion in DIARY_EMOTIONS:
        fields["emotion"] = emotion
    else:
        errors.append(f"emotion이 허용 어휘가 아님: {emotion!r}")
    satisfaction = raw.get("satisfaction")
    if isinstance(satisfaction, int) and not isinstance(satisfaction, bool) and 0 <= satisfaction <= 100:
        fields["satisfaction"] = satisfaction
    else:
        errors.append(f"satisfaction이 0~100 정수가 아님: {satisfaction!r}")
    keywords = raw.get("keywords")
    if isinstance(keywords, list) and keywords and all(isinstance(k, str) and k.strip() for k in keywords):
        fields["keywords"] = [k.strip() for k in keywords]
        if not 2 <= len(keywords) <= 3:
            errors.append(f"keywords 개수 위반(2~3개): {len(keywords)}개")
    else:
        errors.append("keywords 누락 또는 형식 위반")
    return fields, errors


def _normalize(text: str) -> str:
    return "".join(text.split()).lower()


def analyze_diary_case(
    day: DiaryDayFixture,
    fields: dict,
    schema_errors: Sequence[str],
    sentence_embeddings: Sequence[Sequence[float]],
    gold_embeddings: Sequence[Sequence[float]],
    user_embeddings: Sequence[Sequence[float]],
    assistant_embeddings: Sequence[Sequence[float]],
    sentences: Sequence[str],
    threshold: float,
    run_number: int = 1,
) -> DiaryCaseResult:
    coverage: list[EventCoverage] = []
    for gold_index, gold in enumerate(day.gold_chunks):
        sims = [
            cosine_similarity(gold_embeddings[gold_index], sentence_embedding)
            for sentence_embedding in sentence_embeddings
        ]
        best = round(max(sims), 3) if sims else None
        coverage.append(
            EventCoverage(
                chunk_id=gold.chunk_id,
                best_similarity=best,
                covered=best is not None and best >= threshold,
            )
        )

    groundings: list[SentenceGrounding] = []
    for sentence_index, sentence in enumerate(sentences):
        embedding = sentence_embeddings[sentence_index]
        best_by_source = {
            "gold_chunk": max(
                (cosine_similarity(embedding, gold) for gold in gold_embeddings), default=None
            ),
            "user_message": max(
                (cosine_similarity(embedding, user) for user in user_embeddings), default=None
            ),
            "assistant_message": max(
                (cosine_similarity(embedding, item) for item in assistant_embeddings), default=None
            ),
        }
        known = {source: sim for source, sim in best_by_source.items() if sim is not None}
        best_source = max(known, key=known.get) if known else None
        best_sim = round(known[best_source], 3) if best_source else None
        user_side = max(
            (sim for source, sim in known.items() if source != "assistant_message"),
            default=0.0,
        )
        if best_sim is None or best_sim < threshold:
            status = "ungrounded"
        elif best_source == "assistant_message" and user_side < threshold:
            status = "assistant_only"
        else:
            status = "grounded"
        groundings.append(
            SentenceGrounding(
                sentence=sentence, status=status, best_source=best_source, best_similarity=best_sim
            )
        )

    keywords = fields.get("keywords", [])
    source_text = _normalize(
        " ".join(
            [message.content for message in day.messages if message.role == "user"]
            + [chunk.text for chunk in day.gold_chunks]
        )
    )
    generic = [keyword for keyword in keywords if keyword in GENERIC_KEYWORDS]
    # 키워드는 명사구로 합성되는 경우가 많아("항공권 예매" ← "항공권도 예매했어")
    # 전체 문구가 아니라 토큰 단위로 근거를 찾는다 — 토큰이 하나도 없으면 미근거.
    ungrounded_keywords = [
        keyword
        for keyword in keywords
        if keyword not in GENERIC_KEYWORDS
        and not any(
            _normalize(token) in source_text for token in keyword.split() if len(token) >= 2
        )
        and _normalize(keyword) not in source_text
    ]

    emotion = fields.get("emotion")
    emotion_plausible = (
        emotion in day.plausible_emotions if emotion and day.plausible_emotions else None
    )
    covered_count = sum(item.covered for item in coverage)
    return DiaryCaseResult(
        fixture_id=day.fixture_id,
        device_id=day.device_id,
        run_number=run_number,
        title=fields.get("title"),
        content=fields.get("content"),
        emotion=emotion,
        satisfaction=fields.get("satisfaction"),
        keywords=keywords,
        schema_errors=list(schema_errors),
        sentence_count=len(sentences),
        sentence_count_ok=MIN_SENTENCES <= len(sentences) <= MAX_SENTENCES,
        event_coverage=coverage,
        event_recall=round(covered_count / len(coverage), 3) if coverage else None,
        sentences=groundings,
        ungrounded_sentences=sum(item.status == "ungrounded" for item in groundings),
        assistant_confusion_sentences=sum(item.status == "assistant_only" for item in groundings),
        generic_keywords=generic,
        ungrounded_keywords=ungrounded_keywords,
        emotion_plausible=emotion_plausible,
    )


def summarize_diary_results(results: Sequence[DiaryCaseResult]) -> DiarySummary:
    completed = [r for r in results if r.execution_error is None and not r.invalid_json]
    recalls = [r.event_recall for r in completed if r.event_recall is not None]
    sentence_ok = [r.sentence_count_ok for r in completed if r.sentence_count_ok is not None]
    emotion_known = [r.emotion_plausible for r in completed if r.emotion_plausible is not None]
    return DiarySummary(
        case_runs=len(results),
        completed_runs=len(completed),
        execution_error_runs=sum(r.execution_error is not None for r in results),
        invalid_json_runs=sum(r.invalid_json for r in results),
        schema_violation_runs=sum(bool(r.schema_errors) for r in completed),
        mean_event_recall=round(sum(recalls) / len(recalls), 3) if recalls else None,
        missed_event_total=sum(
            sum(not item.covered for item in r.event_coverage) for r in completed
        ),
        ungrounded_sentence_runs=sum(r.ungrounded_sentences > 0 for r in completed),
        ungrounded_sentence_total=sum(r.ungrounded_sentences for r in completed),
        assistant_confusion_runs=sum(r.assistant_confusion_sentences > 0 for r in completed),
        assistant_confusion_total=sum(r.assistant_confusion_sentences for r in completed),
        sentence_count_ok_rate=(
            round(sum(sentence_ok) / len(sentence_ok) * 100, 1) if sentence_ok else None
        ),
        emotion_plausible_rate=(
            round(sum(emotion_known) / len(emotion_known) * 100, 1) if emotion_known else None
        ),
        generic_keyword_runs=sum(bool(r.generic_keywords) for r in completed),
        ungrounded_keyword_runs=sum(bool(r.ungrounded_keywords) for r in completed),
    )
