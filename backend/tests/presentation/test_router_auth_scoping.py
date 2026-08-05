"""device_id 키잉 라우터의 토큰 스코핑 검증.

기존에는 insight·settings·me·game 라우터가 쿼리/헤더의 device_id를 검증 없이 신뢰해,
닉네임(= device_id "nick-{닉네임}")만 알면 타인 데이터를 조회·조작·삭제할 수 있었다.
이제 device_id는 Bearer 세션(get_current_device_id)에서만 나온다 — 무인증 요청은 401.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("GET", "/api/v1/insights/weekly", {"params": {"week": "2026-W23"}}),
        ("GET", "/api/v1/insights/monthly", {"params": {"month": "2026-06"}}),
        ("GET", "/api/v1/settings/clova", {}),
        ("PUT", "/api/v1/settings/clova", {"json": {"api_key": "sk-x-1234"}}),
        (
            "DELETE",
            "/api/v1/me/data",
            {"params": {"confirm": "DELETE-MY-DATA"}},
        ),
        ("GET", "/game/state", {}),
        ("POST", "/game/diary-complete", {"json": {"diary_date": "2026-08-05"}}),
        ("POST", "/game/claim-reward/churu_1", {}),
    ],
)
def test_device_scoped_routes_require_bearer_token(method: str, path: str, kwargs: dict):
    client = TestClient(app)
    resp = client.request(method, path, **kwargs)
    assert resp.status_code == 401


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("GET", "/api/v1/insights/weekly", {"params": {"week": "2026-W23"}}),
        ("GET", "/game/state", {}),
    ],
)
def test_client_supplied_device_id_is_ignored_without_token(method: str, path: str, kwargs: dict):
    """쿼리·헤더로 device_id를 흘려도 토큰 없이는 통과할 수 없다(기존 우회 경로 회귀 방지)."""
    client = TestClient(app)
    params = dict(kwargs.get("params", {}), device_id="nick-victim")
    resp = client.request(method, path, params=params, headers={"X-Device-Id": "nick-victim"})
    assert resp.status_code == 401
