"""Retrieval 평가 데이터셋 검증기 — fixture 정답 참조 무결성까지 검사한다."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from evals.retrieval_schemas import RetrievalEvalCase, RetrievalKind
from evals.validate_fixtures import FIXTURE_DIR, FixtureSet, validate_fixture_dir

DATASET_DIR = Path(__file__).parent / "datasets"
RETRIEVAL_DATASET_FILENAME = "retrieval_cases.jsonl"


def load_retrieval_cases(path: Path) -> tuple[list[RetrievalEvalCase], list[str]]:
    errors: list[str] = []
    cases: list[RetrievalEvalCase] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [], [f"{path}: 파일을 읽을 수 없습니다: {exc}"]
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            errors.append(f"{path}:{line_number}: 빈 JSONL 행은 허용되지 않습니다")
            continue
        try:
            cases.append(RetrievalEvalCase.model_validate(json.loads(line)))
        except json.JSONDecodeError as exc:
            errors.append(f"{path}:{line_number}: JSON 파싱 실패: {exc.msg}")
        except ValidationError as exc:
            errors.append(f"{path}:{line_number}: 스키마 오류: {exc}")
    return cases, errors


def validate_retrieval_cases(
    cases: Sequence[RetrievalEvalCase], fixtures: FixtureSet, path: Path
) -> list[str]:
    errors: list[str] = []
    known_devices = set(fixtures.device_ids)
    # kind별로 (chunk 라벨 → 소유 device) 맵을 만들어 참조 무결성을 검사한다
    diary_owner = {
        chunk.chunk_id: day.device_id
        for day in fixtures.diary_days
        for chunk in day.gold_chunks
    }
    health_owner = {day.fixture_id: day.device_id for day in fixtures.health_days}
    diary_devices_with_chunks = set(diary_owner.values())
    health_devices_with_chunks = set(health_owner.values())

    seen_ids: set[str] = set()
    for case in cases:
        if case.id in seen_ids:
            errors.append(f"{path}: id 중복: {case.id}")
        seen_ids.add(case.id)
        if case.device_id not in known_devices:
            errors.append(f"{path}: {case.id}: 미등록 device_id: {case.device_id}")
            continue
        owner = diary_owner if case.kind == RetrievalKind.DIARY else health_owner
        for chunk_id in case.relevant_chunk_ids:
            if chunk_id not in owner:
                errors.append(
                    f"{path}: {case.id}: fixture에 없는 {case.kind.value} 정답: {chunk_id}"
                )
            elif owner[chunk_id] != case.device_id:
                errors.append(
                    f"{path}: {case.id}: 정답 {chunk_id}의 소유자({owner[chunk_id]})가 "
                    f"case device({case.device_id})와 다릅니다"
                )
        if not case.relevant_chunk_ids:
            # 빈 정답은 해당 사용자가 그 kind의 데이터를 갖지 않을 때만 성립한다.
            # (데이터가 있으면 벡터 검색은 항상 top-k를 반환하므로 0건이 될 수 없다)
            devices_with_data = (
                diary_devices_with_chunks
                if case.kind == RetrievalKind.DIARY
                else health_devices_with_chunks
            )
            if case.device_id in devices_with_data:
                errors.append(
                    f"{path}: {case.id}: {case.device_id}는 {case.kind.value} 데이터가 있어 "
                    "빈 정답 케이스가 될 수 없습니다"
                )
    return errors


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Retrieval 평가 데이터셋 검증")
    parser.add_argument("--dataset", type=Path, default=DATASET_DIR / RETRIEVAL_DATASET_FILENAME)
    parser.add_argument("--fixture-dir", type=Path, default=FIXTURE_DIR)
    args = parser.parse_args(argv)
    fixtures, fixture_errors = validate_fixture_dir(args.fixture_dir)
    cases, errors = load_retrieval_cases(args.dataset)
    errors = fixture_errors + errors + validate_retrieval_cases(cases, fixtures, args.dataset)
    if errors:
        print("retrieval 데이터셋 검증 실패:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(f"retrieval 데이터셋 검증 통과: {len(cases)}개 케이스")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
