from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.domain.repository.diary_repository import DiaryRepository
from app.infrastructure.auth.jwt_handler import issue_access_token, issue_refresh_token
from app.infrastructure.config.database import get_db
from app.infrastructure.config.dependencies import get_diary_repo
from app.infrastructure.persistence.models import UserModel, UserSessionModel
from app.main import app
from app.presentation.auth_deps import get_current_nickname_user, get_current_session
from app.presentation.router.auth_router import _create_session, _revoke_existing_sessions


class _FakeDiaryRepo(DiaryRepository):
    async def save(self, diary):  # pragma: no cover
        raise NotImplementedError

    async def find_by_id(self, diary_id):  # pragma: no cover
        raise NotImplementedError

    async def find_by_device_and_date(self, device_id, diary_date):  # pragma: no cover
        raise NotImplementedError

    async def find_all(self, device_id: str, offset: int = 0, limit: int = 20):
        return []

    async def count(self, device_id: str) -> int:
        return 0


class _FakeDb:
    def __init__(
        self, session: UserSessionModel | None = None, *, fail_on_execute: bool = False
    ) -> None:
        self.session = session
        self.commit_count = 0
        self.rollback_count = 0
        self.fail_on_execute = fail_on_execute
        self.executed: list[str] = []
        self.added: list[UserSessionModel] = []

    async def scalar(self, stmt):
        return self.session

    async def execute(self, stmt):
        if self.fail_on_execute:
            raise RuntimeError("db execute failed")
        self.executed.append(str(stmt))
        return None

    def add(self, model) -> None:
        self.added.append(model)

    async def commit(self) -> None:
        self.commit_count += 1

    async def rollback(self) -> None:
        self.rollback_count += 1


def _make_session(
    *,
    identity: str = "dev-1",
    revoked: bool = False,
    expires_delta: timedelta = timedelta(minutes=15),
) -> UserSessionModel:
    now = datetime.now(UTC).replace(tzinfo=None)
    return UserSessionModel(
        id=uuid.uuid4(),
        device_id=identity,
        jti="jti-1",
        issued_at=now,
        expires_at=now + expires_delta,
        revoked_at=now if revoked else None,
    )


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_current_session_rejects_revoked_access_token():
    db = _FakeDb(_make_session(revoked=True))
    token = issue_access_token("dev-1", "jti-1")

    with pytest.raises(HTTPException) as exc_info:
        await get_current_session(authorization=f"Bearer {token}", db=db)

    assert exc_info.value.status_code == 401
    assert "로그아웃" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_session_rejects_refresh_token():
    db = _FakeDb(_make_session())
    refresh_token, _ = issue_refresh_token("dev-1")

    with pytest.raises(HTTPException) as exc_info:
        await get_current_session(authorization=f"Bearer {refresh_token}", db=db)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_nickname_user_resolves_user_from_nickname_session():
    session = _make_session(identity="nick-hana")
    user = UserModel(id=uuid.uuid4(), nickname="hana")

    class NicknameDb:
        async def scalar(self, stmt):
            return user

    result = await get_current_nickname_user(session=session, db=NicknameDb())

    assert result is user


@pytest.mark.asyncio
async def test_get_current_nickname_user_rejects_non_nickname_session():
    with pytest.raises(HTTPException) as exc_info:
        await get_current_nickname_user(session=_make_session(identity="dev-1"), db=_FakeDb())

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_nickname_user_rejects_missing_user():
    session = _make_session(identity="nick-missing")
    db = _FakeDb(None)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_nickname_user(session=session, db=db)

    assert exc_info.value.status_code == 401


def test_protected_route_returns_401_for_revoked_token():
    db = _FakeDb(_make_session(revoked=True))
    token = issue_access_token("dev-1", "jti-1")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_diary_repo] = _FakeDiaryRepo

    client = TestClient(app)
    resp = client.get(
        "/api/v1/diaries",
        params={"offset": 0, "limit": 1},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 401


def test_protected_route_returns_200_for_active_token():
    db = _FakeDb(_make_session())
    token = issue_access_token("dev-1", "jti-1")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_diary_repo] = _FakeDiaryRepo

    client = TestClient(app)
    resp = client.get(
        "/api/v1/diaries",
        params={"offset": 0, "limit": 1},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    assert resp.json() == {"items": [], "total": 0}


@pytest.mark.asyncio
async def test_revoke_existing_sessions_does_not_commit_midway():
    db = _FakeDb()

    await _revoke_existing_sessions(
        db, device_id="dev-1", revoked_at=datetime.now(UTC).replace(tzinfo=None)
    )

    assert db.commit_count == 0
    assert db.rollback_count == 0
    assert len(db.executed) == 1


@pytest.mark.asyncio
async def test_create_session_uses_single_commit_for_revoke_and_insert():
    db = _FakeDb()

    access_token, refresh_token, access_jti, identity = await _create_session(db, device_id="dev-1")

    assert access_token != ""
    assert refresh_token != ""
    assert access_jti != ""
    assert identity == "dev-1"
    assert db.commit_count == 1
    assert db.rollback_count == 0
    assert len(db.executed) == 2
    assert "pg_advisory_xact_lock" in db.executed[0]
    assert "UPDATE user_sessions" in db.executed[1]
    assert len(db.added) == 1
    assert db.added[0].device_id == "dev-1"
    assert db.added[0].jti == access_jti


@pytest.mark.asyncio
async def test_create_session_rolls_back_when_revoke_or_lock_fails():
    db = _FakeDb(fail_on_execute=True)

    with pytest.raises(RuntimeError):
        await _create_session(db, device_id="dev-1")

    assert db.commit_count == 0
    assert db.rollback_count == 1


def test_logout_revokes_current_session_from_authorization_header():
    db = _FakeDb(_make_session())
    token = issue_access_token("dev-1", "jti-1")
    app.dependency_overrides[get_db] = lambda: db

    client = TestClient(app)
    resp = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 204
    assert db.session is not None
    assert db.session.revoked_at is not None
    assert db.commit_count == 1


def test_logout_then_same_token_is_rejected_by_protected_route():
    db = _FakeDb(_make_session())
    token = issue_access_token("dev-1", "jti-1")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_diary_repo] = _FakeDiaryRepo

    client = TestClient(app)
    logout_resp = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    diary_resp = client.get(
        "/api/v1/diaries",
        params={"offset": 0, "limit": 1},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert logout_resp.status_code == 204
    assert diary_resp.status_code == 401
