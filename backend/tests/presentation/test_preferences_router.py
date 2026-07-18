from __future__ import annotations

import uuid
from datetime import datetime, time

from fastapi.testclient import TestClient

from app.infrastructure.config.database import get_db
from app.infrastructure.persistence.models import UserModel, UserPreferenceModel
from app.main import app
from app.presentation.auth_deps import get_current_nickname_user


class FakeDb:
    def __init__(self, preference: UserPreferenceModel | None = None):
        self.preference = preference
        self.executed = []
        self.committed = 0
        self.rolled_back = 0

    async def scalar(self, stmt):
        return self.preference

    async def execute(self, stmt):
        self.executed.append(stmt)

    async def commit(self):
        self.committed += 1

    async def rollback(self):
        self.rolled_back += 1


def setup_function():
    app.dependency_overrides.clear()


def teardown_function():
    app.dependency_overrides.clear()


def test_night_chat_preference_requires_authentication():
    response = TestClient(app).get("/api/v1/me/preferences/night-chat")

    assert response.status_code == 401


def test_get_returns_default_when_preference_does_not_exist():
    user = UserModel(id=uuid.uuid4(), nickname="hana")
    db = FakeDb()
    app.dependency_overrides[get_current_nickname_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db

    response = TestClient(app).get("/api/v1/me/preferences/night-chat")

    assert response.status_code == 200
    assert response.json() == {"open_time": "19:00", "timezone": "Asia/Seoul"}


def test_get_returns_current_users_preference():
    user = UserModel(id=uuid.uuid4(), nickname="hana")
    preference = UserPreferenceModel(
        user_id=user.id,
        night_chat_open_time=time(21, 30),
        timezone="Asia/Seoul",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    app.dependency_overrides[get_current_nickname_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: FakeDb(preference)

    response = TestClient(app).get("/api/v1/me/preferences/night-chat")

    assert response.status_code == 200
    assert response.json()["open_time"] == "21:30"


def test_put_uses_authenticated_user_and_upsert():
    user = UserModel(id=uuid.uuid4(), nickname="hana")
    db = FakeDb()
    app.dependency_overrides[get_current_nickname_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db

    response = TestClient(app).put(
        "/api/v1/me/preferences/night-chat",
        json={"open_time": "21:30", "timezone": "Asia/Seoul"},
    )

    assert response.status_code == 200
    assert response.json() == {"open_time": "21:30", "timezone": "Asia/Seoul"}
    assert db.committed == 1
    assert len(db.executed) == 1
    assert "ON CONFLICT" in str(db.executed[0])


def test_put_rejects_invalid_time_and_timezone():
    user = UserModel(id=uuid.uuid4(), nickname="hana")
    app.dependency_overrides[get_current_nickname_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: FakeDb()
    client = TestClient(app)

    early = client.put(
        "/api/v1/me/preferences/night-chat",
        json={"open_time": "17:59", "timezone": "Asia/Seoul"},
    )
    invalid_timezone = client.put(
        "/api/v1/me/preferences/night-chat",
        json={"open_time": "19:00", "timezone": "Not/A-Timezone"},
    )

    assert early.status_code == 422
    assert invalid_timezone.status_code == 422


def test_preference_model_has_single_user_cascade_foreign_key():
    table = UserPreferenceModel.__table__

    assert list(table.primary_key.columns.keys()) == ["user_id"]
    foreign_key = next(iter(table.foreign_keys))
    assert foreign_key.target_fullname == "users.id"
    assert foreign_key.ondelete == "CASCADE"
