"""End-to-End Agent RAG 평가 데이터셋의 스키마와 검증.

사용자 입력 → tool 선택 → query 생성 → 검색(평가 DB) → 최종 답변까지
프로덕션 agent 전체 경로를 실행하는 평가다.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.application.usecase.personal_assistant_agent import PersonalAssistantMode
from evals.schemas import EvalHistoryMessage, ExpectedDecision
from evals.validate_dataset import registered_tools_by_mode
from evals.validate_fixtures import FixtureSet


class E2EEvalCase(BaseModel):
    """E2E 케이스 1건.

    relevant_chunk_ids: 검색이 반드시 표면화해야 하는 정답 문서.
    TOOL_CALL 기대인데 비어 있으면 "기록이 없어 abstain해야 하는" 케이스다.
    expected_facts: 최종 답변이 담아야 할 사실 그룹(generation 평가와 동일 규칙).
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    mode: PersonalAssistantMode
    device_id: str = Field(min_length=1)
    input: str = Field(min_length=1)
    history: list[EvalHistoryMessage] = Field(default_factory=list)
    expected_decision: ExpectedDecision
    expected_tools: list[str] = Field(default_factory=list)
    forbidden_tools: list[str] = Field(default_factory=list)
    relevant_chunk_ids: list[str] = Field(default_factory=list)
    expected_facts: list[list[str]] = Field(default_factory=list)
    category: str = Field(min_length=1)
    note: str | None = None


def load_e2e_cases(path: Path) -> tuple[list[E2EEvalCase], list[str]]:
    errors: list[str] = []
    cases: list[E2EEvalCase] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [], [f"{path}: 파일을 읽을 수 없습니다: {exc}"]
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            errors.append(f"{path}:{line_number}: 빈 JSONL 행은 허용되지 않습니다")
            continue
        try:
            cases.append(E2EEvalCase.model_validate(json.loads(line)))
        except json.JSONDecodeError as exc:
            errors.append(f"{path}:{line_number}: JSON 파싱 실패: {exc.msg}")
        except ValidationError as exc:
            errors.append(f"{path}:{line_number}: 스키마 오류: {exc}")
    return cases, errors


def validate_e2e_cases(
    cases: Sequence[E2EEvalCase], fixtures: FixtureSet, path: Path
) -> list[str]:
    errors: list[str] = []
    known_devices = set(fixtures.device_ids)
    allowed_by_mode = registered_tools_by_mode()
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
        allowed = allowed_by_mode[case.mode]
        for tool in case.expected_tools:
            if tool not in allowed:
                errors.append(
                    f"{path}: {case.id}: {case.mode.value} mode에서 사용할 수 없는 tool: {tool}"
                )
        if case.expected_decision == ExpectedDecision.TOOL_CALL and not case.expected_tools:
            errors.append(f"{path}: {case.id}: TOOL_CALL 기대에는 expected_tools가 필요합니다")
        if case.expected_decision == ExpectedDecision.NO_TOOL and (
            case.relevant_chunk_ids or case.expected_facts
        ):
            errors.append(
                f"{path}: {case.id}: NO_TOOL 기대에는 relevant_chunk_ids/expected_facts를 둘 수 없습니다"
            )
        # 정답 문서는 기대 tool의 kind에서만 나올 수 있다
        for chunk_id in case.relevant_chunk_ids:
            if chunk_id in diary_owner:
                owner, needed = diary_owner[chunk_id], "search_diary_memories"
            elif chunk_id in health_owner:
                owner, needed = health_owner[chunk_id], "search_health_records"
            else:
                errors.append(f"{path}: {case.id}: fixture에 없는 정답 문서: {chunk_id}")
                continue
            if owner != case.device_id:
                errors.append(
                    f"{path}: {case.id}: 정답 {chunk_id}의 소유자({owner})가 "
                    f"case device({case.device_id})와 다릅니다"
                )
            if needed not in case.expected_tools:
                errors.append(
                    f"{path}: {case.id}: 정답 {chunk_id}는 {needed} 호출을 기대해야 합니다"
                )
    return errors
