"""PersonalAssistantAgent 오프라인 평가 데이터셋 검증기.

실행기는 포함하지 않는다. 이 모듈은 JSONL 계약과 현재 AgentFactory의 도구 등록
정책이 어긋나지 않았는지만 검사한다.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable, Sequence
from pathlib import Path
from uuid import UUID

from pydantic import ValidationError

from app.application.tool.read_tools import (
    AgentToolExecutionContext,
    create_read_tools,
    create_search_health_records_tool,
)
from app.application.usecase.personal_assistant_agent import PersonalAssistantMode
from evals.schemas import PersonalAssistantEvalCase

DATASET_FILENAMES = (
    "diary_cases.jsonl",
    "health_cases.jsonl",
    "coaching_cases.jsonl",
    "guardrail_cases.jsonl",
)


class _EmptyDiaryQuery:
    async def search_similar(
        self,
        device_id: str,
        query: str,
        exclude_session_id: UUID | None = None,
        limit: int = 5,
    ) -> list[object]:
        return []


class _EmptyHealthQuery:
    async def search_similar(self, device_id: str, query: str, limit: int = 5) -> list[object]:
        return []


def registered_tools_by_mode() -> dict[PersonalAssistantMode, frozenset[str]]:
    """AgentFactory와 같은 tool 생성 함수에서 현재 등록 이름을 읽는다."""
    context = AgentToolExecutionContext(device_id="eval-validator")
    diary_tools = create_read_tools(_EmptyDiaryQuery(), _EmptyHealthQuery(), context)
    health_tool = create_search_health_records_tool(_EmptyHealthQuery(), context)
    return {
        PersonalAssistantMode.DIARY: frozenset(tool.name for tool in diary_tools),
        PersonalAssistantMode.HEALTH: frozenset({health_tool.name}),
        PersonalAssistantMode.COACHING: frozenset(),
    }


def validate_dataset_files(paths: Iterable[Path]) -> list[str]:
    """모든 JSONL 파일을 읽어 사람이 고칠 수 있는 오류 목록을 반환한다."""
    errors: list[str] = []
    seen_ids: dict[str, Path] = {}
    allowed_by_mode = registered_tools_by_mode()
    registered_tools = frozenset().union(*allowed_by_mode.values())

    for path in paths:
        errors.extend(_validate_file(path, seen_ids, registered_tools, allowed_by_mode))
    return errors


def _validate_file(
    path: Path,
    seen_ids: dict[str, Path],
    registered_tools: frozenset[str],
    allowed_by_mode: dict[PersonalAssistantMode, frozenset[str]],
) -> list[str]:
    errors: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [f"{path}: 파일을 읽을 수 없습니다: {exc}"]

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            errors.append(f"{path}:{line_number}: 빈 JSONL 행은 허용되지 않습니다")
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"{path}:{line_number}: JSON 파싱 실패: {exc.msg}")
            continue
        try:
            case = PersonalAssistantEvalCase.model_validate(raw)
        except ValidationError as exc:
            errors.append(f"{path}:{line_number}: 스키마 오류: {exc}")
            continue

        if not case.input.strip():
            errors.append(f"{path}:{line_number}: input은 비어 있을 수 없습니다")
        if case.id in seen_ids:
            errors.append(
                f"{path}:{line_number}: id 중복: {case.id} (첫 위치: {seen_ids[case.id]})"
            )
        else:
            seen_ids[case.id] = path

        expected = set(case.expected_tools)
        forbidden = set(case.forbidden_tools)
        overlap = sorted(expected & forbidden)
        if overlap:
            errors.append(
                f"{path}:{line_number}: expected/forbidden tool 중복: {', '.join(overlap)}"
            )

        unknown = sorted((expected | forbidden) - registered_tools)
        if unknown:
            errors.append(f"{path}:{line_number}: 등록되지 않은 tool: {', '.join(unknown)}")

        unavailable = sorted(expected - allowed_by_mode[case.mode])
        if unavailable:
            errors.append(
                f"{path}:{line_number}: {case.mode.value} mode에서 사용할 수 없는 expected tool: "
                f"{', '.join(unavailable)}"
            )
    return errors


def default_dataset_paths(dataset_dir: Path) -> list[Path]:
    return [dataset_dir / filename for filename in DATASET_FILENAMES]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PersonalAssistantAgent eval JSONL 검증")
    parser.add_argument("paths", nargs="*", type=Path, help="검사할 JSONL 파일")
    args = parser.parse_args(argv)
    paths = args.paths or default_dataset_paths(Path(__file__).parent / "datasets")
    errors = validate_dataset_files(paths)
    if errors:
        print("데이터셋 검증 실패:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(f"데이터셋 검증 통과: {len(paths)}개 파일")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
