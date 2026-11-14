"""auth 模块覆盖率边角补测（覆盖率治理 v1.6.0）.

覆盖 ``openbase/modules/auth/__init__.py`` 中既有用例未触达的降级与校验分支：
密码哈希异常、登录租户策略、租户 code 解析、刷新链主体/状态分支、
个人资料与改密边界、通知偏好 Webhook 校验、角色契约与 API Key 端点边界。
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import openbase.modules.auth as auth_module
from openbase.core.db.session import get_db
from openbase.core.deps.auth import get_current_user
from openbase.core.errors import BaseError, ErrorCode, install_exception_handlers
from openbase.core.models import NotificationPreference, User
from openbase.modules.auth import (
    _caller_tenant_code,
    _load_profile_user,
    apply_login_tenant_policy,
    resolve_tenant_code,
    router,
    verify_password,
)
from openbase.modules.auth import rbac as rbac_module
from openbase.modules.auth import role_contract as role_contract_module
from openbase.modules.auth.service_keys import ServiceKeyService


class _Result:
    """SQLAlchemy 结果替代（scalars/scalar_one_or_none 链式）."""

    def __init__(self, rows):
        self._rows = list(rows)

    def scalars(self):
        return self

    def all(self):
        return list(self._rows)

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None


class _Session:
    """最小异步会话：execute 按队列返回，get 按模型返回."""

    def __init__(self, *, results=None, get_map=None, fail_get=False):
        self._results = list(results or [])
        self._get_map = dict(get_map or {})
        self._fail_get = fail_get
        self.added: list[object] = []
        self.commits = 0
        self.get_calls = 0

    async def execute(self, stmt):
        return self._results.pop(0) if self._results else _Result([])

    async def get(self, model, pk):
        self.get_calls += 1
        if self._fail_get:
            raise RuntimeError("db unreachable")
        return self._get_map.get(model)

    def add(self, obj) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.commits += 1


def _client(*, user=None, session=None) -> tuple[TestClient, _Session]:
    session = session or _Session()
    app = FastAPI()
    install_exception_handlers(app)
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: user or {
        "id": 1,
        "username": "alice",
        "tenant_id": None,
    }
    app.dependency_overrides[get_db] = lambda: session
    return TestClient(app), session


def _login_settings(**overrides):
    defaults = {
        "default_tenant_code": "",
        "require_tenant_on_login": False,
        "env": "dev",
        "jwt_expire_seconds": 7200,
        "refresh_expire_seconds": 604800,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _db_user(**overrides):
    row = {
        "id": 1,
        "username": "alice",
        "password_hash": auth_module.hash_password("OldPass123"),
        "tenant_id": None,
        "subject_type": "user",
        "credential_type": "password",
        "status_state": "active",
        "status_reason": None,
        "token_version": 0,
        "tenant_code": None,
    }
    row.update(overrides)
    return SimpleNamespace(**row)


# ---------------------------------------------------------------------------
# 纯函数
# ---------------------------------------------------------------------------


def test_verify_password_invalid_hash_returns_false():
    assert verify_password("any", "not-a-bcrypt-hash") is False


def test_apply_login_tenant_policy_fallback_and_gate():
    assert apply_login_tenant_policy("acme") == ("acme", None)
    assert apply_login_tenant_policy(None, default_tenant_code="fallback") == (
        "fallback",
        "default_config",
    )
    with pytest.raises(BaseError) as exc_info:
        apply_login_tenant_policy(
            None, require_tenant_on_login=True, is_production=True
        )
    assert exc_info.value.code == ErrorCode.AUTH_FORBIDDEN
    assert apply_login_tenant_policy(None) == (None, "unbound")


async def test_resolve_tenant_code_branches():
    assert await resolve_tenant_code(None, _Session()) is None
    assert await resolve_tenant_code("", _Session()) is None
    assert await resolve_tenant_code("acme", _Session()) == "acme"
    assert await resolve_tenant_code("42", _Session(results=[_Result(["acme"])])) == "acme"

    class _BrokenSession:
        async def execute(self, stmt):
            raise RuntimeError("db down")

    assert await resolve_tenant_code("42", _BrokenSession()) is None


async def test_load_profile_user_non_numeric_returns_none():
    assert await _load_profile_user(_Session(), "oidc-subject") is None


def test_caller_tenant_code_prefers_bound_tenant():
    assert _caller_tenant_code({"tenant_code": "acme"}, {}) == "acme"
    assert _caller_tenant_code({}, {"tenants": ["*", "acme"]}) == "acme"
    assert _caller_tenant_code({}, {"tenants": ["a", "b"]}) is None
    assert _caller_tenant_code({}, {}) is None


# ---------------------------------------------------------------------------
# 登录 / 刷新
# ---------------------------------------------------------------------------


def _patch_login_env(monkeypatch, settings) -> None:
    from openbase.core.cache import redis_client

    monkeypatch.setattr(redis_client, "cache_get", lambda key: None)
    monkeypatch.setattr(redis_client, "cache_set", lambda *a, **k: None)
    monkeypatch.setattr(auth_module, "get_settings", lambda: settings)


def test_login_rejects_unknown_user(monkeypatch):
    _patch_login_env(monkeypatch, _login_settings())
    client, _ = _client(session=_Session(results=[_Result([])]))
    resp = client.post(
        "/api/v1/auth/login", json={"username": "ghost", "password": "whatever1"}
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == ErrorCode.AUTH_UNAUTHORIZED.value


def test_login_default_tenant_fallback(monkeypatch):
    _patch_login_env(monkeypatch, _login_settings(default_tenant_code="fallback"))
    session = _Session(results=[_Result([_db_user()]), _Result(["user"])])
    client, _ = _client(session=session)
    resp = client.post(
        "/api/v1/auth/login", json={"username": "alice", "password": "OldPass123"}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["access_token"]


def test_refresh_rejects_invalid_and_subjectless_token(monkeypatch):
    client, _ = _client()
    monkeypatch.setattr(auth_module, "decode_refresh_token", lambda token: None)
    invalid = client.post("/api/v1/auth/refresh", json={"refresh_token": "bad"})
    assert invalid.status_code == 401, invalid.text

    monkeypatch.setattr(auth_module, "decode_refresh_token", lambda token: {})
    missing = client.post("/api/v1/auth/refresh", json={"refresh_token": "bad"})
    assert missing.status_code == 401, missing.text
    assert "missing subject" in missing.json()["message"]


def test_refresh_string_subject_skips_database(monkeypatch):
    client, session = _client()
    monkeypatch.setattr(
        auth_module,
        "decode_refresh_token",
        lambda token: {"sub": "oidc-sub", "tenant_code": "acme", "role": "viewer"},
    )
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "t"})
    assert resp.status_code == 200, resp.text
    assert session.get_calls == 0


def test_refresh_database_failure_degrades(monkeypatch):
    client, _ = _client(session=_Session(fail_get=True))
    monkeypatch.setattr(
        auth_module,
        "decode_refresh_token",
        lambda token: {"sub": "5", "tenant_code": "acme", "role": "viewer"},
    )
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "t"})
    assert resp.status_code == 200, resp.text


def test_refresh_rejects_agent_subject(monkeypatch):
    row = SimpleNamespace(
        id=5,
        username="agent-x",
        tenant_id=None,
        tenant_code=None,
        subject_type="agent",
        status_state="active",
        token_version=0,
    )
    client, _ = _client(session=_Session(get_map={User: row}))
    monkeypatch.setattr(
        auth_module, "decode_refresh_token", lambda token: {"sub": "5"}
    )
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "t"})
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == ErrorCode.AUTH_FORBIDDEN.value


def test_refresh_subject_row_tenant_and_role_fallbacks(monkeypatch):
    row = SimpleNamespace(
        id=5,
        username="alice",
        tenant_id=42,
        tenant_code="",
        subject_type="user",
        status_state="active",
        token_version=3,
    )
    session = _Session(
        results=[_Result(["acme"]), _Result(["admin"])],
        get_map={User: row},
    )
    client, _ = _client(session=session)
    monkeypatch.setattr(
        auth_module,
        "decode_refresh_token",
        lambda token: {"sub": "5", "username": "alice"},
    )
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "t"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["access_token"]


def test_refresh_direct_payload_keeps_tenant_code(monkeypatch):
    client, session = _client()
    monkeypatch.setattr(
        auth_module,
        "decode_refresh_token",
        lambda token: {
            "sub": "oidc-sub",
            "tenant_id": "acme",
            "tenant_code": "acme",
            "role": "admin",
        },
    )
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "t"})
    assert resp.status_code == 200, resp.text
    assert session.get_calls == 0


# ---------------------------------------------------------------------------
# /me 与资料更新
# ---------------------------------------------------------------------------


def _patch_permissions(monkeypatch, permissions: list[str]) -> None:
    async def _resolve(session, user):  # noqa: ANN001
        return list(permissions)

    monkeypatch.setattr(rbac_module, "resolve_user_permissions", _resolve)


def test_me_prepends_superadmin_wildcard(monkeypatch):
    _patch_permissions(monkeypatch, ["system:superadmin"])
    row = SimpleNamespace(id=1, display_name=None, email=None, phone=None)
    client, _ = _client(session=_Session(get_map={User: row}))
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 200, resp.text
    assert resp.json()["permissions"] == ["*", "system:superadmin"]


def test_update_me_missing_row_returns_404(monkeypatch):
    _patch_permissions(monkeypatch, [])
    client, _ = _client(session=_Session())
    resp = client.put("/api/v1/auth/me", json={"display_name": "New"})
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == ErrorCode.BIZ_NOT_FOUND.value


def test_update_me_partial_phone_only(monkeypatch):
    _patch_permissions(monkeypatch, [])
    row = SimpleNamespace(
        id=1, display_name="Alice", email="alice@example.com", phone=None
    )
    session = _Session(get_map={User: row})
    client, _ = _client(session=session)
    resp = client.put("/api/v1/auth/me", json={"phone": "13900000000"})
    assert resp.status_code == 200, resp.text
    assert row.phone == "13900000000"
    assert session.commits == 1


def test_update_me_without_phone_field_keeps_value(monkeypatch):
    """未传 phone → 不触碰原字段（phone 分支为假）."""
    _patch_permissions(monkeypatch, [])
    row = SimpleNamespace(
        id=1, display_name="Alice", email="alice@example.com", phone="13800000000"
    )
    session = _Session(get_map={User: row})
    client, _ = _client(session=session)
    resp = client.put("/api/v1/auth/me", json={"email": "new@example.com"})
    assert resp.status_code == 200, resp.text
    assert row.phone == "13800000000"
    assert row.email == "new@example.com"


def test_change_password_missing_row_and_same_password(monkeypatch):
    client, _ = _client(session=_Session())
    missing = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "OldPass123", "new_password": "NewPass123"},
    )
    assert missing.status_code == 404, missing.text

    row = SimpleNamespace(id=1, password_hash=auth_module.hash_password("OldPass123"))
    client2, _ = _client(session=_Session(get_map={User: row}))
    same = client2.post(
        "/api/v1/auth/change-password",
        json={"old_password": "OldPass123", "new_password": "OldPass123"},
    )
    assert same.status_code == 400, same.text
    assert "不能与旧密码相同" in same.json()["message"]


# ---------------------------------------------------------------------------
# 通知偏好
# ---------------------------------------------------------------------------


def test_notification_webhook_url_requires_http_scheme():
    client, session = _client(session=_Session())
    resp = client.put(
        "/api/v1/auth/notification-preferences",
        json={"webhook": False, "webhook_url": "ftp://example.com/hook"},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["code"] == ErrorCode.PARAM_INVALID.value
    assert session.commits == 0


def test_notification_existing_row_updated_without_insert():
    existing = NotificationPreference(
        user_id=1,
        in_app=True,
        email=False,
        webhook=False,
        webhook_url=None,
        events={"alert": True},
    )
    session = _Session(get_map={NotificationPreference: existing})
    client, _ = _client(session=session)
    resp = client.put(
        "/api/v1/auth/notification-preferences", json={"email": True}
    )
    assert resp.status_code == 200, resp.text
    assert existing.email is True
    assert session.added == []
    assert session.commits == 1


# ---------------------------------------------------------------------------
# 角色契约 / API Key 端点边界
# ---------------------------------------------------------------------------


def test_roles_contract_endpoint(monkeypatch):
    async def _load(session):  # noqa: ANN001
        return {}

    monkeypatch.setattr(role_contract_module, "load_role_permissions", _load)
    monkeypatch.setattr(
        role_contract_module, "build_role_contract", lambda perms: {"roles": []}
    )
    client, _ = _client()
    resp = client.get("/api/v1/auth/roles/contract")
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"roles": []}


def _patch_api_key_guard(monkeypatch) -> None:
    async def _allow(*args, **kwargs):
        return None

    async def _tenant_filter(*args, **kwargs):
        return None

    monkeypatch.setattr(rbac_module, "ensure_user_permission", _allow)
    monkeypatch.setattr(rbac_module, "tenant_filter_code", _tenant_filter)


def test_expiring_api_keys_endpoint(monkeypatch):
    _patch_api_key_guard(monkeypatch)

    async def _list_expiring(*args, **kwargs):
        return []

    monkeypatch.setattr(ServiceKeyService, "list_expiring", _list_expiring)
    client, _ = _client()
    resp = client.get("/api/v1/auth/api-keys/expiring", params={"within_days": 3})
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_revoke_api_key_by_id_missing_returns_404(monkeypatch):
    _patch_api_key_guard(monkeypatch)

    async def _revoke(*args, **kwargs):
        return None

    monkeypatch.setattr(ServiceKeyService, "revoke_by_id", _revoke)
    client, _ = _client()
    resp = client.delete("/api/v1/auth/api-keys/by-id/missing-key")
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == ErrorCode.BIZ_NOT_FOUND.value
