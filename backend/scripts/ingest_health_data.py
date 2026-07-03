"""
삼성 헬스 더미 데이터를 파싱하여 DB에 적재하고 RAG 청크를 생성하는 스크립트.
idempotent: source_hash가 이미 존재하면 skip.

실행: uv run python scripts/ingest_health_data.py
"""

import asyncio
import hashlib
import json
import sys
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.domain.model.health_chunk import HealthChunk
from app.domain.model.health_record import HealthDailySummary
from app.infrastructure.config.database import async_session_factory
from app.infrastructure.external.embedding_service_impl import SentenceTransformerEmbeddingService
from app.infrastructure.persistence.health_chunk_repository_impl import HealthChunkRepositoryImpl
from app.infrastructure.persistence.health_record_repository_impl import HealthRecordRepositoryImpl

DUMMY_DATA_DIR = Path(__file__).parent.parent / "dummy_data"

EXERCISE_DIR = DUMMY_DATA_DIR / "com.samsung.shealth.exercise"
HEART_RATE_DIR = DUMMY_DATA_DIR / "com.samsung.shealth.tracker.heart_rate"
PEDOMETER_DIR = DUMMY_DATA_DIR / "com.samsung.shealth.tracker.pedometer_day_summary"
STEP_TREND_DIR = DUMMY_DATA_DIR / "com.samsung.shealth.step_daily_trend"
FLOORS_DIR = DUMMY_DATA_DIR / "com.samsung.shealth.tracker.floors_day_summary"


# ---------------------------------------------------------------------------
# 데이터 중간 집계 구조체 (도메인 모델 아님, 파서 내부용)
# ---------------------------------------------------------------------------


@dataclass
class ExerciseData:
    duration_sec: int = 0
    distance_m: float = 0.0
    calories: float = 0.0
    source_files: list[Path] = field(default_factory=list)


@dataclass
class HeartRateData:
    avg: float = 0.0
    min: float = 0.0
    max: float = 0.0
    source_files: list[Path] = field(default_factory=list)


@dataclass
class PedometerData:
    step_count: int = 0
    step_goal: int = 0
    step_goal_achieved: bool = False
    calories: float = 0.0
    distance_m: float = 0.0
    source_files: list[Path] = field(default_factory=list)


@dataclass
class StepTrendData:
    step_count: int = 0
    calories: float = 0.0
    distance_m: float = 0.0
    source_files: list[Path] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 파서들
# ---------------------------------------------------------------------------


class ExerciseParser:
    """exercise/*/live_data.json 파싱. start_time ms → date 변환."""

    def parse(self, base_dir: Path) -> dict[date, ExerciseData]:
        result: dict[date, ExerciseData] = {}
        if not base_dir.exists():
            return result

        for json_file in base_dir.rglob("*.live_data.json"):
            try:
                entries = json.loads(json_file.read_text())
            except (json.JSONDecodeError, OSError):
                continue

            if not entries:
                continue

            # heart_rate 전용 파일은 skip (distance 필드가 없음)
            first = entries[0]
            if "heart_rate" in first and "distance" not in first:
                continue

            for entry in entries:
                start_ms = entry.get("start_time", 0)
                if not start_ms:
                    continue
                record_date = _ms_to_date(start_ms)
                data = result.setdefault(record_date, ExerciseData())
                data.distance_m += entry.get("distance", 0.0)
                data.calories += entry.get("calorie", 0.0)
                if json_file not in data.source_files:
                    data.source_files.append(json_file)

            # 운동 시간: 마지막 segment start_time - 첫 번째 start_time (초)
            if len(entries) >= 2:
                first_ms = entries[0].get("start_time", 0)
                last_ms = entries[-1].get("start_time", 0)
                if first_ms and last_ms and last_ms > first_ms:
                    record_date = _ms_to_date(first_ms)
                    result[record_date].duration_sec = (last_ms - first_ms) // 1000

        return result


class HeartRateParser:
    """tracker.heart_rate/*/binning_data.json 파싱. start_time ms → date 변환."""

    def parse(self, base_dir: Path) -> dict[date, HeartRateData]:
        result: dict[date, HeartRateData] = {}
        if not base_dir.exists():
            return result

        daily_readings: dict[date, list[float]] = {}
        daily_min: dict[date, float] = {}
        daily_max: dict[date, float] = {}
        daily_files: dict[date, list[Path]] = {}

        for json_file in base_dir.rglob("*.heart_rate.binning_data.json"):
            try:
                entries = json.loads(json_file.read_text())
            except (json.JSONDecodeError, OSError):
                continue

            for entry in entries:
                start_ms = entry.get("start_time", 0)
                if not start_ms:
                    continue
                record_date = _ms_to_date(start_ms)
                hr = entry.get("heart_rate", 0.0)
                hr_min = entry.get("heart_rate_min", hr)
                hr_max = entry.get("heart_rate_max", hr)

                daily_readings.setdefault(record_date, []).append(hr)
                daily_min[record_date] = min(daily_min.get(record_date, hr_min), hr_min)
                daily_max[record_date] = max(daily_max.get(record_date, hr_max), hr_max)
                daily_files.setdefault(record_date, [])
                if json_file not in daily_files[record_date]:
                    daily_files[record_date].append(json_file)

        for d, readings in daily_readings.items():
            result[d] = HeartRateData(
                avg=sum(readings) / len(readings),
                min=daily_min[d],
                max=daily_max[d],
                source_files=daily_files.get(d, []),
            )

        return result


class PedometerParser:
    """pedometer_day_summary/*/achievement.json + binning_data.json 파싱.
    날짜는 achievement.json의 mBestStepsDate에서 추출.
    동일 날짜 여러 UUID 존재시 mBestSteps 최대값 선택.
    """

    def parse(self, base_dir: Path) -> dict[date, PedometerData]:
        result: dict[date, PedometerData] = {}
        if not base_dir.exists():
            return result

        for achievement_file in base_dir.rglob("*.achievement.json"):
            try:
                achievement = json.loads(achievement_file.read_text())
            except (json.JSONDecodeError, OSError):
                continue

            best_steps_ms = achievement.get("mBestStepsDate", 0)
            if not best_steps_ms:
                continue

            record_date = _ms_to_date(best_steps_ms)
            best_steps = achievement.get("mBestSteps", 0)

            # 같은 날짜에 여러 UUID가 있으면 최대 걸음수 선택
            existing = result.get(record_date)
            if existing and existing.step_count >= best_steps:
                continue

            # binning_data에서 칼로리/거리 합산
            uuid_stem = achievement_file.stem.replace(".achievement", "").replace("achievement", "")
            uuid_stem = achievement_file.stem.split(".achievement")[0]
            binning_file = achievement_file.parent / f"{uuid_stem}.binning_data.json"

            calories = 0.0
            distance_m = 0.0
            if binning_file.exists():
                try:
                    bins = json.loads(binning_file.read_text())
                    for b in bins:
                        calories += b.get("mCalorie", 0.0)
                        distance_m += b.get("mDistance", 0.0)
                except (json.JSONDecodeError, OSError):
                    pass

            source_files = [achievement_file]
            if binning_file.exists():
                source_files.append(binning_file)

            result[record_date] = PedometerData(
                step_count=best_steps,
                step_goal=achievement.get("mTarget", 6000),
                step_goal_achieved=achievement.get("mIsGoalAchieved", False),
                calories=calories,
                distance_m=distance_m,
                source_files=source_files,
            )

        return result


class StepTrendParser:
    """step_daily_trend/*/binning_data.json 파싱.
    날짜는 파일 mtime에서 추출. 144구간 합산.
    """

    def parse(self, base_dir: Path) -> dict[date, StepTrendData]:
        result: dict[date, StepTrendData] = {}
        if not base_dir.exists():
            return result

        for json_file in base_dir.rglob("*.binning_data.json"):
            try:
                bins = json.loads(json_file.read_text())
            except (json.JSONDecodeError, OSError):
                continue

            if not bins or not isinstance(bins[0], dict):
                continue

            record_date = _file_mtime_to_date(json_file)
            data = result.setdefault(record_date, StepTrendData())
            for b in bins:
                data.step_count += b.get("count", 0)
                data.calories += b.get("calorie", 0.0)
                data.distance_m += b.get("distance", 0.0)
            if json_file not in data.source_files:
                data.source_files.append(json_file)

        return result


class FloorsParser:
    """floors_day_summary/*/binning_data.json 파싱.
    날짜는 파일 mtime에서 추출. 144구간 정수 합산.
    """

    def parse(self, base_dir: Path) -> dict[date, tuple[int, list[Path]]]:
        result: dict[date, tuple[int, list[Path]]] = {}
        if not base_dir.exists():
            return result

        for json_file in base_dir.rglob("*.binning_data.json"):
            try:
                data = json.loads(json_file.read_text())
            except (json.JSONDecodeError, OSError):
                continue

            if not isinstance(data, list) or not data:
                continue

            # floors 파일: 정수 배열
            if not isinstance(data[0], int):
                continue

            record_date = _file_mtime_to_date(json_file)
            total_floors = sum(data)
            existing_floors, existing_files = result.get(record_date, (0, []))
            result[record_date] = (
                existing_floors + total_floors,
                existing_files + [json_file],
            )

        return result


# ---------------------------------------------------------------------------
# 데이터 로더 (파서 통합)
# ---------------------------------------------------------------------------


class HealthDataLoader:
    """파서들의 결과를 날짜별로 merge하여 HealthDailySummary 목록 반환."""

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._exercise_parser = ExerciseParser()
        self._hr_parser = HeartRateParser()
        self._pedometer_parser = PedometerParser()
        self._step_trend_parser = StepTrendParser()
        self._floors_parser = FloorsParser()

    def load(self) -> list[HealthDailySummary]:
        exercise_by_date = self._exercise_parser.parse(EXERCISE_DIR)
        hr_by_date = self._hr_parser.parse(HEART_RATE_DIR)
        pedometer_by_date = self._pedometer_parser.parse(PEDOMETER_DIR)
        step_trend_by_date = self._step_trend_parser.parse(STEP_TREND_DIR)
        floors_by_date = self._floors_parser.parse(FLOORS_DIR)

        all_dates = (
            set(exercise_by_date)
            | set(hr_by_date)
            | set(pedometer_by_date)
            | set(step_trend_by_date)
            | set(floors_by_date)
        )

        summaries = []
        for record_date in sorted(all_dates):
            exercise = exercise_by_date.get(record_date)
            hr = hr_by_date.get(record_date)
            # 걸음수는 pedometer 우선, 없으면 step_trend
            pedometer = pedometer_by_date.get(record_date)
            step_trend = step_trend_by_date.get(record_date)
            floors_tuple = floors_by_date.get(record_date, (0, []))

            if pedometer:
                step_count = pedometer.step_count
                step_goal = pedometer.step_goal
                step_goal_achieved = pedometer.step_goal_achieved
                step_calories = pedometer.calories
                step_distance_m = pedometer.distance_m
                step_files = pedometer.source_files
            elif step_trend:
                step_count = step_trend.step_count
                step_goal = 6000  # 기본값
                step_goal_achieved = step_count >= 6000
                step_calories = step_trend.calories
                step_distance_m = step_trend.distance_m
                step_files = step_trend.source_files
            else:
                step_count = 0
                step_goal = 6000
                step_goal_achieved = False
                step_calories = 0.0
                step_distance_m = 0.0
                step_files = []

            source_files: list[Path] = []
            source_files.extend(step_files)
            if exercise:
                source_files.extend(exercise.source_files)
            if hr:
                source_files.extend(hr.source_files)
            source_files.extend(floors_tuple[1])

            source_hash = _compute_hash(source_files)

            summary = HealthDailySummary(
                record_date=record_date,
                step_count=step_count,
                step_goal=step_goal,
                step_goal_achieved=step_goal_achieved,
                step_calories=step_calories,
                step_distance_m=step_distance_m,
                has_exercise=exercise is not None,
                exercise_duration_sec=exercise.duration_sec if exercise else 0,
                exercise_distance_m=exercise.distance_m if exercise else 0.0,
                exercise_calories=exercise.calories if exercise else 0.0,
                heart_rate_avg=hr.avg if hr else None,
                heart_rate_min=hr.min if hr else None,
                heart_rate_max=hr.max if hr else None,
                floors_climbed=floors_tuple[0],
                source_hash=source_hash,
            )
            summaries.append(summary)

        return summaries


# ---------------------------------------------------------------------------
# 청크 빌더
# ---------------------------------------------------------------------------


class HealthChunkBuilder:
    """HealthDailySummary를 한국어 자연어 텍스트로 변환 후 임베딩 생성."""

    def __init__(self, embedding_service: SentenceTransformerEmbeddingService) -> None:
        self._embedding_service = embedding_service

    def build(self, summaries: list[HealthDailySummary]) -> list[HealthChunk]:
        texts = [self._to_text(s) for s in summaries]
        chunks = []
        embeddings = self._embedding_service.embed(texts)
        for summary, text, embedding in zip(summaries, texts, embeddings):
            chunks.append(
                HealthChunk(
                    record_date=summary.record_date,
                    text=text,
                    embedding=embedding,
                    data_types=self._get_data_types(summary),
                )
            )
        return chunks

    def _to_text(self, summary: HealthDailySummary) -> str:
        parts: list[str] = []

        date_str = summary.record_date.strftime("%Y-%m-%d")
        parts.append(f"{date_str}에 {summary.step_count:,}걸음을 걸었어.")

        if summary.step_calories > 0:
            km = summary.step_distance_m / 1000
            parts.append(f"칼로리 {summary.step_calories:.0f}kcal 소모, 이동거리 {km:.1f}km.")

        if summary.step_goal > 0:
            achieved = "달성" if summary.step_goal_achieved else "미달성"
            parts.append(f"목표({summary.step_goal:,}걸음) {achieved}.")

        if summary.has_exercise:
            parts.append(
                f"운동 기록: {summary.exercise_distance_m:.0f}m, "
                f"칼로리 {summary.exercise_calories:.0f}kcal, "
                f"시간 {summary.exercise_duration_sec // 60}분."
            )

        if summary.heart_rate_avg is not None:
            parts.append(
                f"심박수 평균 {summary.heart_rate_avg:.0f}bpm "
                f"(최저 {summary.heart_rate_min:.0f}, 최고 {summary.heart_rate_max:.0f})."
            )
        else:
            parts.append("심박수 기록 없음.")

        if summary.floors_climbed > 0:
            parts.append(f"층 오르기 {summary.floors_climbed}층.")

        return " ".join(parts)

    @staticmethod
    def _get_data_types(summary: HealthDailySummary) -> list[str]:
        types = ["steps"]
        if summary.has_exercise:
            types.append("exercise")
        if summary.heart_rate_avg is not None:
            types.append("heart_rate")
        if summary.floors_climbed > 0:
            types.append("floors")
        return types


# ---------------------------------------------------------------------------
# 유틸 함수
# ---------------------------------------------------------------------------


def _ms_to_date(ms: int) -> date:
    return datetime.fromtimestamp(ms / 1000, tz=UTC).date()


def _file_mtime_to_date(path: Path) -> date:
    return datetime.fromtimestamp(path.stat().st_mtime).date()


def _compute_hash(files: list[Path]) -> str:
    sorted_paths = sorted(str(f.resolve()) for f in files)
    content = "\n".join(sorted_paths)
    return hashlib.sha256(content.encode()).hexdigest()


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------


async def main() -> None:
    print("삼성 헬스 데이터 수집 시작...")

    loader = HealthDataLoader(DUMMY_DATA_DIR)
    summaries = loader.load()
    print(f"파싱 완료: {len(summaries)}개 날짜 데이터 발견")

    embedding_service = SentenceTransformerEmbeddingService()
    chunk_builder = HealthChunkBuilder(embedding_service)

    async with async_session_factory() as db:
        record_repo = HealthRecordRepositoryImpl(db)
        chunk_repo = HealthChunkRepositoryImpl(db)

        new_summaries: list[HealthDailySummary] = []
        for summary in summaries:
            if await record_repo.source_hash_exists(summary.source_hash):
                print(f"  Skip (이미 존재): {summary.record_date}")
            else:
                await record_repo.save(summary)
                new_summaries.append(summary)
                print(
                    f"  Ingested: {summary.record_date} (걸음: {summary.step_count:,}, 심박수: {'있음' if summary.heart_rate_avg else '없음'})"
                )

        if new_summaries:
            print(f"\n청크 생성 중 ({len(new_summaries)}개)...")
            chunks = chunk_builder.build(new_summaries)
            await chunk_repo.save_all(chunks)
            print(f"청크 {len(chunks)}개 저장 완료.")
        else:
            print("\n새로 추가된 데이터 없음.")

    print("\n완료!")


if __name__ == "__main__":
    asyncio.run(main())
