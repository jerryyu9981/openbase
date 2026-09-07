"""P2-1 T2/T3 RED 断言：入站身份头门禁与 OpenBase 试点收口.

对齐草案 §10：
- T2-5/T3-7  非白名单带头：enforce → 403 PERM_UNTRUSTED_IDENTITY_HEADER；
              strip（enforce 关）→ 仅剥除不 403（§5.4 两段式）
- T3-5  get_current_tenant：客户端自带头不再无校验覆盖 JWT（受信来源头仍优先）
- T3-6  get_identity_context：非受信来源带头 → 忽略 + identity_headers_ignored 标注
- T3-8  双通道（A 直连 / B 编排）出站身份语义一致性（builder 视角）
"""
from __future__ import annotations

import asyncio
import importlib
import types
from typing import Any

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from openbase.core.deps.auth import (
    AuthMiddleware,
    get_current_tenant,
    get_identity_context,
)
from openbase.modules.auth.jwt import create_access_token
from openbase.modules.protocol_headers import (
    PROXY_SOURCE_ORCHESTRATOR,
    PROXY_SOURCE_RAG,
    build_outbound_headers,
)
from openbase.settings import Settings

_SECRET = "p21-test-secret-0123456789abcdef0123456789abcdef"


def _apply_settings(monkeypatch: pytest.MonkeyPatch, **overrides: Any) -> Settings:
    """构造并替换 settings 单例（返回实例；可带协议头开关覆盖）."""
    settings = Settings(jwt_secret=_SECRET, **overrides)
    module = importlib.import_module("openbase.settings")
    monkeypatch.setattr(module, "_settings", settings)
    return settings


# ---------------------------------------------------------------------------
# T2-5 / T3-7：AuthMiddleware 入站身份头门禁（HTTP 层）
# ---------------------------------------------------------------------------


def _token(subject: str = "42") -> str:
    return create_access_token(subject, username="alice")


def _build_app(monkeypatch: pytest.MonkeyPatch, **settings_overrides: Any) -> TestClient:
    from openbase import init_app
    from openbase.modules.auth import UserService

    settings = _apply_settings(monkeypatch, **settings_overrides)
    for module_name in ("auth", "audit", "tenant", "config"):
        settings.enable_module(module_name)
    UserService.seed_memory_user("admin", "admin123")
    app = init_app(settings)
    return TestClient(app)


def test_t2_5_enforce_403_untrusted_identity_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """enforce_inbound_identity_headers=True：非白名单带头 → 403 PERM_UNTRUSTED."""
    client = _build_app(monkeypatch, enforce_inbound_identity_headers=True)
    token = _token()
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}", "X-User-ID": "999"},
    )
    assert resp.status_code == 403, resp.text
    body = resp.json()
    assert body["code"] == "PERM_UNTRUSTED_IDENTITY_HEADER"
    assert body["detail"]["headers"] == ["X-User-ID"]


def test_t3_7_strip_removes_headers_without_403(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """strip 开 + enforce 关：非受信身份头物理剥除，请求继续（不 403）."""
    app = FastAPI()
    from openbase.core.errors import install_exception_handlers

    install_exception_handlers(app)
    _apply_settings(
        monkeypatch, strip_inbound_identity_headers=True, enforce_inbound_identity_headers=False
    )
    from openbase.modules.auth import UserService

    UserService.seed_memory_user("admin", "admin123")
    app.add_middleware(AuthMiddleware)

    @app.get("/api/v1/probe")
    async def probe(request: Request) -> JSONResponse:
        tenant_header = request.headers.get("X-Tenant-Id")
        return JSONResponse({"tenant_from_header": tenant_header})

    client = TestClient(app)
    token = create_access_token("oidc-user", username="oidc")  # 非数字 sub：中间件免验
    resp = client.get(
        "/api/v1/probe",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Id": "spoofed"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["tenant_from_header"] is None  # 剥除生效，未作为事实源


# ---------------------------------------------------------------------------
# T3-5：get_current_tenant 试点收口
# ---------------------------------------------------------------------------


def _token_with_tenant(tenant_code: str = "acme") -> str:
    return create_access_token("42", username="alice", tenant_code=tenant_code)


def _tenant_request(headers: dict[str, str]) -> types.SimpleNamespace:
    return types.SimpleNamespace(headers=headers, state=types.SimpleNamespace())


def test_t3_5_client_header_no_longer_overrides_jwt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """客户端自带头 + JWT → 头不再无校验覆盖 JWT（受信来源空）."""
    _apply_settings(monkeypatch)
    token = _token_with_tenant("acme")
    request = _tenant_request(
        {
            "Authorization": f"Bearer {token}",
            "X-Tenant-Id": "evil-tenant",  # 非受信客户端伪造
        }
    )
    tenant = asyncio.run(get_current_tenant(request))
    assert tenant == "acme"  # JWT 生效，伪造头被忽略


def test_t3_5_trusted_source_header_still_priority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """受信来源（X-Proxy-Source ∈ 白名单）携带 X-Tenant-Id 仍优先."""
    _apply_settings(monkeypatch, trusted_proxy_sources=PROXY_SOURCE_RAG)
    token = _token_with_tenant("acme")
    request = _tenant_request(
        {
            "Authorization": f"Bearer {token}",
            "X-Proxy-Source": PROXY_SOURCE_RAG,
            "X-Tenant-Id": "b-tenant",
        }
    )
    tenant = asyncio.run(get_current_tenant(request))
    assert tenant == "b-tenant"


# ---------------------------------------------------------------------------
# T3-6：get_identity_context 非受信带头忽略 + 审计标注
# ---------------------------------------------------------------------------


def test_t3_6_get_identity_context_marks_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """非受信来源带头 → 上下文忽略 + state.identity_headers_ignored=True."""
    _apply_settings(monkeypatch)
    request = _tenant_request({"X-User-Id": "999", "X-Tenant-Id": "evil"})
    context = get_identity_context(request)
    assert context.user_id is None
    assert context.tenant_id is None
    assert getattr(request.state, "identity_headers_ignored", False) is True


def test_t3_6_trusted_source_headers_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """受信来源带头 → 采纳（trusted 透传语义）."""
    _apply_settings(monkeypatch, trusted_proxy_sources=PROXY_SOURCE_ORCHESTRATOR)
    request = _tenant_request(
        {
            "X-Proxy-Source": PROXY_SOURCE_ORCHESTRATOR,
            "X-User-Id": "42",
            "X-Tenant-Id": "acme",
        }
    )
    context = get_identity_context(request)
    assert context.user_id == 42
    assert context.tenant_id == "acme"


# ---------------------------------------------------------------------------
# T3-8：双通道等价（A 直连 / B 编排）出站身份语义一致
# ---------------------------------------------------------------------------


def test_t3_8_dual_channel_identity_semantics_equivalent() -> None:
    """A/B 通道同一主体 → 出站身份头集合与语义一致（Q-4 双通道不变式）."""
    common_principal = {
        "id": "42",
        "username": "alice",
        "tenant_code": "acme",
        "subject_type": "user",
        "role": "org_admin",
        "auth_method": "jwt",
    }
    # A 直连：OpenBase 解析 JWT 得统一主体上下文
    channel_a_ctx = dict(common_principal)
    # B 编排：受信编排透传头 + 编排自身认证，经 OpenBase 出口仍重写为本 proxy 来源
    channel_b_ctx = dict(common_principal, auth_method="trusted-orchestrator")

    headers_a = build_outbound_headers(None, channel_a_ctx, target_system="rag")
    headers_b = build_outbound_headers(None, channel_b_ctx, target_system="rag")
    for name in ("X-User-ID", "X-Tenant-ID", "X-Org-ID", "X-User-Role"):
        assert headers_a[name] == headers_b[name], f"双通道 {name} 语义不一致"
    assert headers_a["X-Proxy-Source"] == headers_b["X-Proxy-Source"]
    assert headers_a["X-Proxy-Source"] == "openbase-rag-proxy"
