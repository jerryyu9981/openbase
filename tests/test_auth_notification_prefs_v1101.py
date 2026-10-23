"""v1.10.1（OB-01）通知偏好端点回归.

覆盖 `GET/PUT /auth/notification-preferences`：默认值、upsert 持久化、事件白名单、
Webhook 启用时地址必填与协议校验、OIDC 字符串主体无本地行时的降级。
使用假会话与依赖覆盖，不依赖真实数据库。
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from openbase.core.db.session import get_db
from openbase.core.deps.auth import get_current_user
from openbase.core.errors import ErrorCode, install_exception_handlers
from openbase.core.models import NotificationPreference, User
from openbase.modules.auth import router

PREF_URL = "/api/v1/auth/notification-preferences"


class FakeSession:
    """最小异步会话：仅实现 get/add/commit（通知偏好用例所需）."""

    def __init__(self, user: User | None = None) -> None:
        self.user = user
        self.pref_row: NotificationPreference | None = None
        self.added: list[object] = []
        self.commit_count = 0

    async def get(self, model, pk):  # noqa: ANN001
        if model is NotificationPreference:
            if self.pref_row is not None and self.pref_row.user_id == pk:
                return self.pref_row
            return None
        if model is User:
            return self.user if self.user is not None and pk == self.user.id else None
        return None

    def add(self, obj) -> None:  # noqa: ANN001
        self.added.append(obj)
        if isinstance(obj, NotificationPreference):
            self.pref_row = obj

    async def commit(self) -> None:
        self.commit_count += 1


def _build_client(user_id: int | str = 1, user: User | None = None):  # noqa: ANN001
    session = FakeSession(user)
    app = FastAPI()
    install_exception_handlers(app)
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: {
        "id": user_id,
        "username": "alice",
        "tenant_id": None,
    }
    app.dependency_overrides[get_db] = lambda: session
    return TestClient(app), session


def test_get_returns_defaults_without_row():
    client, _ = _build_client()
    resp = client.get(PREF_URL)
    assert resp.status_code == 200
    body = resp.json()
    assert body["in_app"] is True
    assert body["email"] is False
    assert body["webhook"] is False
    assert body["webhook_url"] is None
    assert body["events"] == {"alert": True, "approval": True, "system": True}


def test_put_creates_row_and_persists():
    client, session = _build_client()
    resp = client.put(
        PREF_URL,
        json={
            "in_app": False,
            "email": True,
            "webhook": True,
            "webhook_url": "https://example.com/hooks/openbase",
            "events": {"alert": True, "approval": False, "system": True},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["in_app"] is False
    assert body["email"] is True
    assert body["webhook"] is True
    assert body["webhook_url"] == "https://example.com/hooks/openbase"
    assert body["events"] == {"alert": True, "approval": False, "system": True}
    assert session.commit_count == 1
    assert session.pref_row is not None

    # 再次 GET 应读到刚保存的值（同一行，不重复插入）
    resp2 = client.get(PREF_URL)
    assert resp2.status_code == 200
    assert resp2.json()["email"] is True
    assert len(session.added) == 1


def test_put_rejects_unknown_event():
    client, session = _build_client()
    resp = client.put(PREF_URL, json={"events": {"alert": True, "unknown": True}})
    assert resp.status_code == 400
    assert resp.json()["code"] == ErrorCode.PARAM_INVALID.value
    assert session.commit_count == 0


def test_put_requires_webhook_url_when_enabled():
    client, session = _build_client()
    resp = client.put(PREF_URL, json={"webhook": True, "webhook_url": None})
    assert resp.status_code == 400
    assert resp.json()["code"] == ErrorCode.PARAM_INVALID.value
    assert "Webhook" in resp.json()["message"]
    assert session.commit_count == 0


def test_put_rejects_non_http_webhook_url():
    client, _ = _build_client()
    resp = client.put(PREF_URL, json={"webhook": True, "webhook_url": "ftp://example.com/hook"})
    assert resp.status_code == 400
    assert resp.json()["code"] == ErrorCode.PARAM_INVALID.value


def test_oidc_subject_without_local_row():
    client, session = _build_client(user_id="oidc|bob")
    resp = client.get(PREF_URL)
    assert resp.status_code == 200
    assert resp.json()["in_app"] is True

    resp2 = client.put(PREF_URL, json={"in_app": False})
    assert resp2.status_code == 404
    assert resp2.json()["code"] == ErrorCode.BIZ_NOT_FOUND.value
    assert session.commit_count == 0
