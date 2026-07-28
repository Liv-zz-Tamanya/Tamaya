"""satisfaction 스코어링 일관성 측정 (PR-A2).

같은 회고 대화를 N회 반복 생성해 대화별 satisfaction 표준편차와
estimated(판단 불가) 비율을 잰다. 루브릭 적용 전후를 이 수치로 비교한다.

실제 CLOVA API를 호출한다 — mock 모드에서는 랜덤 응답이라 측정이 무의미하므로
즉시 중단한다. 프로덕션 DB는 사용하지 않는다(저장 없이 생성만 반복).

사용:
    uv run python -m scripts.measure_satisfaction_consistency --repeat 3
    uv run python -m scripts.measure_satisfaction_consistency \\
        --fixtures evals/fixtures/satisfaction_consistency_fixtures.jsonl \\
        --repeat 3 --out evals/reports/satisfaction-consistency.json

판정 기준(PR-A2 §5.3):
    표준편차 평균 <= 10  → PR-B 진행 가능
    10 < 평균 <= 20      → 루브릭 임계 서술 구체화 후 재측정
    평균 > 20            → 점수 추출을 별도 LLM 호출로 분리하는 방안 검토
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
from datetime import UTC, datetime
from pathlib import Path

from app.application.service.diary_parsing import parse_satisfaction
from app.domain.model.chat_message import ChatMessage
from app.infrastructure.config.settings import settings
from app.infrastructure.external.clova_client import ClovaClient
from evals.run_diary_generation_evaluation import diary_prompt_hash

DEFAULT_FIXTURES = Path("evals/fixtures/satisfaction_consistency_fixtures.jsonl")


def load_fixtures(path: Path) -> list[dict]:
    fixtures = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                fixtures.append(json.loads(line))
    return fixtures


def to_chat_messages(raw_messages: list[dict]) -> list[ChatMessage]:
    now = datetime.now(UTC)
    return [ChatMessage(role=m["role"], content=m["content"], created_at=now) for m in raw_messages]


async def measure_case(client: ClovaClient, fixture: dict, repeat: int) -> dict:
    messages = to_chat_messages(fixture["messages"])
    values: list[int] = []
    estimated_count = 0
    error_count = 0
    raw_outputs: list[object] = []

    for _ in range(repeat):
        try:
            diary_data = await client.generate_diary(messages)
        except Exception as exc:  # noqa: BLE001 — 오류도 측정 대상(가용성)
            error_count += 1
            raw_outputs.append(f"error: {exc}")
            continue
        raw = diary_data.get("satisfaction")
        raw_outputs.append(raw)
        value, estimated = parse_satisfaction(raw)
        if estimated:
            estimated_count += 1
        else:
            values.append(value)

    stdev = round(statistics.stdev(values), 2) if len(values) >= 2 else None
    return {
        "fixture_id": fixture["fixture_id"],
        "band": fixture.get("band"),
        "runs": repeat,
        "satisfaction_values": values,
        "raw_outputs": raw_outputs,
        "stdev": stdev,
        "estimated_count": estimated_count,
        "error_count": error_count,
    }


async def run(fixtures_path: Path, repeat: int, limit: int | None, out: Path | None) -> None:
    if settings.clova_mock_mode or not settings.clova_api_key:
        sys.exit(
            "mock 모드이거나 CLOVA_API_KEY가 없습니다 — 랜덤 응답으로는 측정이 무의미합니다. "
            "실키를 설정하고 CLOVA_MOCK_MODE=false로 실행하세요."
        )

    fixtures = load_fixtures(fixtures_path)
    if limit:
        fixtures = fixtures[:limit]
    print(f"이 실행은 실제 CLOVA API를 호출합니다 — {len(fixtures)}건 × {repeat}회")

    client = ClovaClient()
    cases = []
    for index, fixture in enumerate(fixtures, start=1):
        case = await measure_case(client, fixture, repeat)
        cases.append(case)
        print(
            f"[{index}/{len(fixtures)}] {case['fixture_id']}: "
            f"values={case['satisfaction_values']} stdev={case['stdev']} "
            f"estimated={case['estimated_count']}/{repeat} errors={case['error_count']}"
        )

    stdevs = [c["stdev"] for c in cases if c["stdev"] is not None]
    total_runs = sum(c["runs"] for c in cases)
    total_estimated = sum(c["estimated_count"] for c in cases)
    short_cases = [c for c in cases if c["band"] == "short"]
    short_estimated_cases = sum(1 for c in short_cases if c["estimated_count"] > 0)

    summary = {
        "measured_at": datetime.now(UTC).isoformat(),
        "model": settings.clova_model,
        "prompt_hash": diary_prompt_hash(),
        "fixtures": str(fixtures_path),
        "case_count": len(cases),
        "repeat": repeat,
        "mean_stdev": round(statistics.mean(stdevs), 2) if stdevs else None,
        "max_stdev": max(stdevs) if stdevs else None,
        "estimated_rate": round(total_estimated / total_runs * 100, 1) if total_runs else None,
        "short_case_count": len(short_cases),
        "short_cases_with_estimated": short_estimated_cases,
        "error_runs": sum(c["error_count"] for c in cases),
    }

    print("\n=== 요약 ===")
    for key, value in summary.items():
        print(f"{key}: {value}")

    verdict_mean = summary["mean_stdev"]
    if verdict_mean is not None:
        if verdict_mean <= 10:
            print("판정: 표준편차 평균 <= 10 — PR-B 진행 가능")
        elif verdict_mean <= 20:
            print("판정: 10 < 평균 <= 20 — 루브릭 임계 서술 구체화 후 재측정")
        else:
            print("판정: 평균 > 20 — 점수 추출의 별도 LLM 호출 분리 검토")

    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps({"summary": summary, "cases": cases}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\n리포트 저장: {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--limit", type=int, default=None, help="앞에서부터 N건만 측정")
    parser.add_argument("--out", type=Path, default=None, help="JSON 리포트 저장 경로")
    args = parser.parse_args()
    asyncio.run(run(args.fixtures, args.repeat, args.limit, args.out))


if __name__ == "__main__":
    main()
