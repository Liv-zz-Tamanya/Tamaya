"""일반 대화 품질·Output Safety 평가 데이터셋의 스키마와 검증.

검색·DB 없이 agent 대화 경로만 실행한다. 케이스 category가 채점 기준을 정한다.
DIARY_CRISIS의 기대 동작은 제품 결정(2026-07-23)에 따라 "차단하지 않고
공감 + 전문 상담 안내"다 — 현재 diary는 guardrail을 건너뛰므로 이 평가가
개선 전 현재 동작의 baseline을 만든다.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.application.usecase.personal_assistant_agent import PersonalAssistantMode
from evals.schemas import EvalHistoryMessage


class ConversationCategory(StrEnum):
    HISTORY_REFERENCE = "history_reference"  # history의 정보를 반영하는가
    RELEVANCE = "relevance"  # 관련 있고 구체적인가
    REPETITION_PROBE = "repetition_probe"  # 이미 했던 질문을 반복하지 않는가
    OVERCLAIM_PROBE = "overclaim_probe"  # 과도한 단정을 하지 않는가
    MEDICAL_BOUNDARY = "medical_boundary"  # 진단·처방을 생성하지 않는가
    DIARY_CRISIS = "diary_crisis"  # 위기 신호에 공감 + 상담 안내를 하는가


class ConversationEvalCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    mode: PersonalAssistantMode
    input: str = Field(min_length=1)
    history: list[EvalHistoryMessage] = Field(default_factory=list)
    category: ConversationCategory
    note: str | None = None


def load_conversation_cases(path: Path) -> tuple[list[ConversationEvalCase], list[str]]:
    errors: list[str] = []
    cases: list[ConversationEvalCase] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [], [f"{path}: 파일을 읽을 수 없습니다: {exc}"]
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            errors.append(f"{path}:{line_number}: 빈 JSONL 행은 허용되지 않습니다")
            continue
        try:
            cases.append(ConversationEvalCase.model_validate(json.loads(line)))
        except json.JSONDecodeError as exc:
            errors.append(f"{path}:{line_number}: JSON 파싱 실패: {exc.msg}")
        except ValidationError as exc:
            errors.append(f"{path}:{line_number}: 스키마 오류: {exc}")
    return cases, errors


def validate_conversation_cases(
    cases: Sequence[ConversationEvalCase], path: Path
) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    for case in cases:
        if case.id in seen_ids:
            errors.append(f"{path}: id 중복: {case.id}")
        seen_ids.add(case.id)
        if case.category == ConversationCategory.DIARY_CRISIS and case.mode != PersonalAssistantMode.DIARY:
            errors.append(f"{path}: {case.id}: diary_crisis는 diary mode여야 합니다")
        if case.category in {
            ConversationCategory.HISTORY_REFERENCE,
            ConversationCategory.REPETITION_PROBE,
        } and not case.history:
            errors.append(f"{path}: {case.id}: {case.category.value}는 history가 필요합니다")
        for item in case.history:
            if item.role not in {"user", "assistant"}:
                errors.append(f"{path}: {case.id}: 지원하지 않는 history role: {item.role}")
    return errors
