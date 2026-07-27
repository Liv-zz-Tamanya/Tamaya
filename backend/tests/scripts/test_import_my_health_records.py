"""나의건강기록 수입 — 파싱·변환·검증 테스트 (DB 접근 없음)."""

import json
from datetime import date
from pathlib import Path

import pytest

from app.domain.model.medical_visit import MedicalVisit, MedicalVisitType
from app.domain.model.sleep_record import SleepRecord
from scripts.import_my_health_records import (
    convert_payload,
    parse_sleep_duration,
    parse_step_count,
)

SAMPLE_PATH = Path(__file__).parents[2] / "scripts" / "sample_my_health_records.json"


@pytest.mark.parametrize(
    ("text", "minutes"),
    [
        ("7시간44분", 464),
        ("6시간 48분", 408),
        ("3시간36분", 216),
        ("44분", 44),
        ("7시간", 420),
        ("8시간2분", 482),
    ],
)
def test_parse_sleep_duration(text: str, minutes: int):
    assert parse_sleep_duration(text) == minutes


@pytest.mark.parametrize("text", ["", "쾌면", "7:44", "0분", "25시간"])
def test_parse_sleep_duration_rejects_bad_input(text: str):
    with pytest.raises(ValueError):
        parse_sleep_duration(text)


@pytest.mark.parametrize(
    ("text", "count"),
    [("6,764걸음", 6764), ("10,268걸음", 10268), ("6764", 6764), (6764, 6764), ("0걸음", 0)],
)
def test_parse_step_count(text, count: int):
    assert parse_step_count(text) == count


@pytest.mark.parametrize("text", ["", "많이 걸음", "-100", True])
def test_parse_step_count_rejects_bad_input(text):
    with pytest.raises(ValueError):
        parse_step_count(text)


def test_convert_payload_full():
    raw = {
        "sleep": [{"측정일자": "2026-07-01", "측정값": "7시간44분"}],
        "steps": [{"측정일자": "2026-06-27", "측정값": "6,764걸음"}],
        "medical_visits": [
            {
                "진료일자": "2026-05-04", "진료구분": "처방 조제",
                "진료기관": "강변그랜드약국", "방문위치": "광진구 광나루로56길",
                "방문일수": 1, "처방횟수": 1, "투약일수": 2,
            }
        ],
    }
    payload, errors = convert_payload(raw, "nick-test")
    assert errors == []
    assert payload.sleep[0].duration_minutes == 464
    assert payload.sleep[0].device_id == "nick-test"
    assert payload.steps == [(date(2026, 6, 27), 6764)]
    visit = payload.visits[0]
    assert visit.visit_type == MedicalVisitType.PHARMACY
    assert visit.medication_days == 2


def test_convert_payload_accepts_alternate_medication_key():
    # 화면 표기('투약(요양)일수')를 그대로 쓴 경우도 허용
    raw = {
        "medical_visits": [
            {"진료일자": "2026-05-04", "진료구분": "방문 외래",
             "진료기관": "성모이비인후과의원", "투약(요양)일수": 3}
        ]
    }
    payload, errors = convert_payload(raw, "nick-test")
    assert errors == []
    assert payload.visits[0].medication_days == 3


def test_convert_payload_collects_errors_per_row():
    raw = {
        "sleep": [
            {"측정일자": "2026-07-01", "측정값": "7시간44분"},
            {"측정일자": "07/02", "측정값": "7시간"},
            {"측정일자": "2026-07-03", "측정값": "쾌면"},
        ],
        "steps": [{"측정일자": "2026-07-01"}],
        "medical_visits": [
            {"진료일자": "2026-05-04", "진료구분": "입원", "진료기관": "어딘가"}
        ],
    }
    payload, errors = convert_payload(raw, "nick-test")
    assert len(payload.sleep) == 1  # 유효한 행만 변환
    assert len(errors) == 4
    assert any("sleep[2]" in e for e in errors)
    assert any("sleep[3]" in e for e in errors)
    assert any("steps[1]" in e for e in errors)
    assert any("medical_visits[1]" in e for e in errors)  # '입원'은 미지원 진료구분


def test_convert_payload_detects_in_file_duplicates():
    raw = {
        "sleep": [
            {"측정일자": "2026-07-01", "측정값": "7시간"},
            {"측정일자": "2026-07-01", "측정값": "6시간"},
        ]
    }
    _, errors = convert_payload(raw, "nick-test")
    assert any("측정일자 중복" in e for e in errors)


def test_sample_file_converts_cleanly():
    raw = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    payload, errors = convert_payload(raw, "nick-test")
    assert errors == []
    assert len(payload.sleep) == 8
    assert len(payload.steps) == 8
    assert len(payload.visits) == 4
    # 같은 날 서로 다른 기관 3건은 중복이 아니다
    assert sum(v.visit_date == date(2026, 5, 4) for v in payload.visits) == 3


def test_domain_validation():
    with pytest.raises(ValueError):
        SleepRecord(device_id="d", record_date=date(2026, 7, 1), duration_minutes=0)
    with pytest.raises(ValueError):
        SleepRecord(device_id=" ", record_date=date(2026, 7, 1), duration_minutes=400)
    with pytest.raises(ValueError):
        MedicalVisit(
            device_id="d", visit_date=date(2026, 5, 4),
            visit_type=MedicalVisitType.OUTPATIENT, institution="병원",
            prescription_count=-1,
        )
