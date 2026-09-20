"""rag-proxy 身份头注入策略测试（DEF-BE-147-005，TDD：先 RED 后 GREEN）.

背景（《OpenBase-问题跟踪记录-v1.4.7》§1 DEF-BE-147-005）：

- 启用 OpenRAG M2 受信模式（`OPENRAG_IDENTITY_TRUSTED_PROXY_SOURCES`）后，rag-proxy 注入的
  `X-Tenant-ID: default` 命中 OpenRAG `identity_gate.py` 的「保留租户码碰撞」防护
  → `GET /api/v1/rag-proxy/collections` 由 200 变 **400 BIZ_RESERVED_TENANT_CODE_COLLISION**；
- 实测（`doc/test/evidence/v147/def005-multiprobe-20260920.json`）：
  ① 改用**非保留**租户码（方案 A）→ 200 但 `data.items=[]`（租户隔离使既有知识库不可见）；
  ② **不注入身份头**（方案 B，仅 `X-API-Key` + `X-Proxy-Source` + `X-Request-Id`）→ 200 且数据完整、
    `request_id` 仍复用网关出站值（串联不破）。
- 故本仓按方案 B 落地，并以**显式开关**（`rag_inject_identity_headers`，默认 True 保持既有语义）
  表达「不静默降级」：联调环境由编排器显式置 false。
"""

from __future__ import annotations

import types
from dataclasses import dataclass

from openbase.modules.protocol_headers.constants import (
    HEADER_ORG_ID,
    HEADER_PROXY_SOURCE,
    HEADER_REQUEST_ID,
    HEADER_TENANT_ID,
    HEADER_USER_ID,
    HEADER_USER_ROLE,
    PROXY_SOURCE_RAG,
)
from openbase.modules.rag_proxy import _build_upstream_headers
from openbase.settings import get_settings

IDENTITY_HEADERS = (
    HEADER_USER_ID,
    HEADER_TENANT_ID,
    HEADER_ORG_ID,
    HEADER_USER_ROLE,
)


@dataclass
class StubRequest:
    """出站装配读请求桩（state.request_id 供串联契约断言）."""

    request_id: str = "req-chain-0001"

    @property
    def state(self) -> types.SimpleNamespace:
        return types.SimpleNamespace(request_id=self.request_id)


def _user_ctx() -> dict:
    """统一主体上下文（联调口径：tenant_code=default，角色 admin）."""
    return {
        "id": "1",
        "username": "admin",
        "tenant_code": "default",
        "tenant_id": "1",
        "org_id": "default",
        "subject_type": "user",
        "role": "admin",
        "permissions": [],
        "auth_method": "jwt",
    }


def _set_policy(monkeypatch, enabled: bool) -> None:
    """切换 rag-proxy 身份注入策略（settings 单例属性注入）."""
    monkeypatch.setattr(
        get_settings(), "rag_inject_identity_headers", enabled, raising=False
    )


def test_rag_proxy_injects_identity_headers_by_default(monkeypatch) -> None:
    """默认（开关 True）：维持既有四头 + 来源 + 请求 id 注入（不改变既有语义）."""
    _set_policy(monkeypatch, True)

    headers = _build_upstream_headers(StubRequest(), _user_ctx())

    assert headers[HEADER_USER_ID] == "1"
    assert headers[HEADER_TENANT_ID] == "default"
    assert headers[HEADER_USER_ROLE] == "admin"
    assert headers[HEADER_PROXY_SOURCE] == PROXY_SOURCE_RAG
    assert headers[HEADER_REQUEST_ID] == "req-chain-0001"
    assert headers["X-API-Key"]


def test_rag_proxy_omits_identity_headers_when_policy_disabled(monkeypatch) -> None:
    """开关 False（DEF-BE-147-005 联调解）：不注入四头，仅保留服务级认证 + 来源 + 请求 id."""
    _set_policy(monkeypatch, False)

    headers = _build_upstream_headers(StubRequest(), _user_ctx())

    for name in IDENTITY_HEADERS:
        assert name not in headers, f"策略关闭后不应注入 {name}"
    assert headers[HEADER_PROXY_SOURCE] == PROXY_SOURCE_RAG
    assert headers["X-API-Key"]


def test_rag_proxy_policy_disabled_keeps_request_id_for_chain(monkeypatch) -> None:
    """策略关闭后仍须携带网关 `X-Request-Id`（跨系统串联契约不可回退）."""
    _set_policy(monkeypatch, False)

    headers = _build_upstream_headers(StubRequest(request_id="req-chain-9f9f"), _user_ctx())

    assert headers[HEADER_REQUEST_ID] == "req-chain-9f9f"
