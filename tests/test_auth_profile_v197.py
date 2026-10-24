"""R7（v1.9.7）：个人资料与密码修改端点回归.

覆盖 `GET /auth/me` 资料字段、`PUT /auth/me` 更新与校验、`POST /auth/change-password`
旧密码校验/强度校验。使用假会话与依赖覆盖，不依赖真实数据库。
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from openbase.core.db.session import get_db
from openbase.core.deps.auth import get_current_user
from openbase.core.errors import ErrorCode, install_exception_handlers
from openbase.core.models import User
from openbase.modules.auth import hash_password, router, verify_password
from openbase.modules.auth.rbac import PermissionService


class FakeSession:
    """最小异步会话：仅实现 get/commit."""

    def __init__(self, user: User) -> None:
        self.user = user
        self.commit_count = 0

    async def get(self, model, pk):  # noqa: ANN001
        return self.user if pk == self.user.id else None

    async def commit(self) -> None:
        self.commit_count += 1


def _build_client(monkeypatch, user: User):  # noqa: ANN001
    async def fake_permissions(session, user_id):  # noqa: ANN001
        return []

    monkeypatch.setattr(
        PermissionService,
        "permissions_for_with_fallback",
        staticmethod(fake_permissions),
    )

    session = FakeSession(user)
    app = FastAPI()
    install_exception_handlers(app)
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: {
        "id": user.id,
        "username": user.username,
        "tenant_id": None,
    }
    app.dependency_overrides[get_db] = lambda: session
    return TestClient(app), session


def _user(password: str = "OldPass123") -> User:
    return User(
        id=1,
        username="alice",
        password_hash=hash_password(password),
        display_name="Alice",
        email="alice@example.com",
        phone=None,
        status=1,
    )


def test_me_returns_profile_fields(monkeypatch):
    client, _ = _build_client(monkeypatch, _user())
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "alice"
    assert body["display_name"] == "Alice"
    assert body["email"] == "alice@example.com"
    assert body["phone"] is None


def test_update_me_persists_profile(monkeypatch):
    client, session = _build_client(monkeypatch, _user())
    resp = client.put(
        "/api/v1/auth/me",
        json={"display_name": "Alice New", "email": "new@example.com", "phone": "13800000000"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["display_name"] == "Alice New"
    assert body["email"] == "new@example.com"
    assert body["phone"] == "13800000000"
    assert session.commit_count == 1
    assert session.user.display_name == "Alice New"


def test_update_me_rejects_invalid_email(monkeypatch):
    client, session = _build_client(monkeypatch, _user())
    resp = client.put("/api/v1/auth/me", json={"email": "not-an-email"})
    assert resp.status_code == 400
    assert resp.json()["code"] == ErrorCode.PARAM_INVALID.value
    assert session.commit_count == 0


def test_change_password_rejects_wrong_old_password(monkeypatch):
    client, session = _build_client(monkeypatch, _user())
    resp = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "WrongPass1", "new_password": "NewPass123"},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == ErrorCode.PARAM_INVALID.value
    assert session.commit_count == 0


def test_change_password_rejects_weak_password(monkeypatch):
    client, _ = _build_client(monkeypatch, _user())
    resp = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "OldPass123", "new_password": "abcdefgh"},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == ErrorCode.PARAM_INVALID.value


def test_change_password_success_updates_hash(monkeypatch):
    user = _user()
    client, session = _build_client(monkeypatch, user)
    resp = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "OldPass123", "new_password": "NewPass123"},
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "密码已修改"
    assert session.commit_count == 1
    assert verify_password("NewPass123", user.password_hash)
    assert not verify_password("OldPass123", user.password_hash)
