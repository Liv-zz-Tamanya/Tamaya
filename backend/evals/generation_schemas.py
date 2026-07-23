"""RAG 답변 생성 평가 데이터셋의 스키마와 검증.

검색을 우회하고 정답 문서(fixture chunk)를 LLM 컨텍스트에 직접 주입해
"문서가 주어졌을 때 제대로 답하는가"만 격리 측정한다.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from evals.validate_fixtures import FixtureSet


class GenerationMode(StrEnum):
    DIARY = "diary"
    HEALTH = "health"


class GenerationCategory(StrEnum):
    GROUNDED_RECALL = "grounded_recall"
    MULTI_DOC_SUMMARY = "multi_doc_summary"
    UNSUPPORTED_BAIT = "unsupported_bait"
    NO_RECORD_ABSTENTION = "no_record_abstention"
    HEALTH_BOUNDARY = "health_boundary"


# 문서가 있어야 하는 category (abstention만 빈 컨텍스트)
GROUNDED_CATEGORIES = frozenset(
    {
        GenerationCategory.GROUNDED_RECALL,
        GenerationCategory.MULTI_DOC_SUMMARY,
        GenerationCategory.UNSUPPORTED_BAIT,
        GenerationCategory.HEALTH_BOUNDARY,
    }
)
# expected_facts(완전성 채점)가 필수인 category
FACT_CHECKED_CATEGORIES = frozenset(
    {GenerationCategory.GROUNDED_RECALL, GenerationCategory.MULTI_DOC_SUMMARY}
)


class GenerationEvalCase(BaseModel):
    """생성 평가 케이스 1건.

    expected_facts는 완전한 답변이 담아야 할 사실 그룹 목록 — 안쪽 리스트는
    동의 표현 대안이며 하나라도 답변에 포함되면 그 그룹은 충족이다.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    mode: GenerationMode
    device_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    context_chunk_ids: list[str] = Field(default_factory=list)
    category: GenerationCategory
    expected_facts: list[list[str]] = Field(default_factory=list)
    note: str | None = None


def load_generation_cases(path: Path) -> tuple[list[GenerationEvalCase], list[str]]:
    errors: list[str] = []
    cases: list[GenerationEvalCase] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [], [f"{path}: 파일을 읽을 수 없습니다: {exc}"]
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            errors.append(f"{path}:{line_number}: 빈 JSONL 행은 허용되지 않습니다")
            continue
        try:
            cases.append(GenerationEvalCase.model_validate(json.loads(line)))
        except json.JSONDecodeError as exc:
            errors.append(f"{path}:{line_number}: JSON 파싱 실패: {exc.msg}")
        except ValidationError as exc:
            errors.append(f"{path}:{line_number}: 스키마 오류: {exc}")
    return cases, errors


def validate_generation_cases(
    cases: Sequence[GenerationEvalCase], fixtures: FixtureSet, path: Path
) -> list[str]:
    errors: list[str] = []
    known_devices = set(fixtures.device_ids)
    diary_owner = {
        chunk.chunk_id: day.device_id
        for day in fixtures.diary_days
        for chunk in day.gold_chunks
    }
    health_owner = {day.fixture_id: day.device_id for day in fixtures.health_days}

    seen_ids: set[str] = set()
    for case in cases:
        if case.id in seen_ids:
            errors.append(f"{path}: id 중복: {case.id}")
        seen_ids.add(case.id)
        if case.device_id not in known_devices:
            errors.append(f"{path}: {case.id}: 미등록 device_id: {case.device_id}")
            continue
        owner = diary_owner if case.mode == GenerationMode.DIARY else health_owner
        for chunk_id in case.context_chunk_ids:
            if chunk_id not in owner:
                errors.append(
                    f"{path}: {case.id}: fixture에 없는 {case.mode.value} 문서: {chunk_id}"
                )
            elif owner[chunk_id] != case.device_id:
                errors.append(
                    f"{path}: {case.id}: 문서 {chunk_id}의 소유자({owner[chunk_id]})가 "
                    f"case device({case.device_id})와 다릅니다"
                )
        if case.category in GROUNDED_CATEGORIES and not case.context_chunk_ids:
            errors.append(f"{path}: {case.id}: {case.category.value}는 컨텍스트 문서가 필요합니다")
        if case.category == GenerationCategory.NO_RECORD_ABSTENTION and case.context_chunk_ids:
            errors.append(f"{path}: {case.id}: no_record_abstention은 컨텍스트가 비어야 합니다")
        if case.category in FACT_CHECKED_CATEGORIES and not case.expected_facts:
            errors.append(f"{path}: {case.id}: {case.category.value}는 expected_facts가 필요합니다")
        for group in case.expected_facts:
            if not group or any(not alternative.strip() for alternative in group):
                errors.append(f"{path}: {case.id}: expected_facts에 빈 항목이 있습니다")
    return errors
