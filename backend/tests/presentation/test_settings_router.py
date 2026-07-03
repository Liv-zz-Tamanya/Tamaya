"""설정 라우터 — 연결 테스트 + 마스킹 설정 영속 (G003-2, TDD).

핵심 보안 불변식: 어떤 응답에도 원문 키가 노출되지 않고(마스킹만), 서버는 원문 키를
저장하지 않는다(repo에 들어오는 값은 마스킹된 값). TestClient + fake DI로 검증.
"""

import pytest
from fastapi.testclient import TestClient

from app.application.service.clova_connection_tester import ClovaConnectionTester
from app.domain.model.clova_setting import ClovaSetting
from app.domain.repository.clova_setting_repository import ClovaSettingRepository
from app.infrastructure.config.dependencies import (
    get_clova_connection_tester,
    get_clova_setting_repo,
)
from app.main import app

_RAW_KEY = "sk-secret-value-1234"


class _FakeTester(ClovaConnectionTester):
    def __init__(self, result: bool) -> None:
        self._result = result

    async def test_connection(self, api_key: str) -> bool:
        return self._result


class _FakeRepo(ClovaSettingRepository):
    def __init__(self, existing: ClovaSetting | None = None) -> None:
        self.store: dict[str, ClovaSetting] = {}
        if existing:
            self.store[existing.device_id] = existing

    async def get(self, device_id: str) -> ClovaSetting | None:
        return self.store.get(device_id)

    async def upsert(self, setting: ClovaSetting) -> None:
        self.store[setting.device_id] = setting


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_connection_test_ok_returns_masked_not_raw():
    app.dependency_overrides[get_clova_connection_tester] = lambda: _FakeTester(True)
    client = TestClient(app)
    resp = client.post("/api/v1/settings/clova/test", json={"api_key": _RAW_KEY})

    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["masked"] == "••••1234"
    assert _RAW_KEY not in resp.text  # 원문 키 미노출


def test_connection_test_empty_key_returns_400():
    app.dependency_overrides[get_clova_connection_tester] = lambda: _FakeTester(True)
    client = TestClient(app)
    resp = client.post("/api/v1/settings/clova/test", json={"api_key": "  "})
    assert resp.status_code == 400


def test_put_setting_stores_masked_only_not_raw():
    repo = _FakeRepo()
    app.dependency_overrides[get_clova_setting_repo] = lambda: repo
    client = TestClient(app)
    resp = client.put("/api/v1/settings/clova", json={"device_id": "dev-1", "api_key": _RAW_KEY})

    assert resp.status_code == 200
    body = resp.json()
    assert body["has_key"] is True
    assert body["masked"] == "••••1234"
    assert _RAW_KEY not in resp.text
    # 서버 저장소에는 원문 키가 절대 들어가지 않는다(마스킹만)
    stored = repo.store["dev-1"]
    assert stored.masked_key == "••••1234"
    assert _RAW_KEY not in stored.masked_key


def test_put_setting_twice_updates_masked():
    # 동일 device_id로 키를 교체하면 마스킹 프리뷰가 갱신된다(upsert 업데이트 경로)
    repo = _FakeRepo()
    app.dependency_overrides[get_clova_setting_repo] = lambda: repo
    client = TestClient(app)

    client.put("/api/v1/settings/clova", json={"device_id": "dev-1", "api_key": "sk-old-key-0001"})
    resp = client.put(
        "/api/v1/settings/clova", json={"device_id": "dev-1", "api_key": "sk-new-key-9999"}
    )

    assert resp.status_code == 200
    assert resp.json()["masked"] == "••••9999"
    assert repo.store["dev-1"].masked_key == "••••9999"
    assert len(repo.store) == 1  # 새 레코드가 아니라 갱신


def test_get_setting_existing_returns_masked():
    repo = _FakeRepo(ClovaSetting(device_id="dev-1", masked_key="••••1234", has_key=True))
    app.dependency_overrides[get_clova_setting_repo] = lambda: repo
    client = TestClient(app)
    resp = client.get("/api/v1/settings/clova", params={"device_id": "dev-1"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["has_key"] is True
    assert body["masked"] == "••••1234"


def test_get_setting_missing_returns_empty():
    repo = _FakeRepo()
    app.dependency_overrides[get_clova_setting_repo] = lambda: repo
    client = TestClient(app)
    resp = client.get("/api/v1/settings/clova", params={"device_id": "unknown"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["has_key"] is False
    assert body["masked"] == ""
