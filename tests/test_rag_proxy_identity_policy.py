"""rag-proxy 身份头注入策略与租户码对齐测试（R-387 / DEF-BE-1410-001）.

演进脉络（TDD：先 RED 后 GREEN）：

1. **DEF-BE-147-005（v1.4.7）**：启用 OpenRAG M2 受信模式后，rag-proxy 注入的
   `X-Tenant-ID: default` 命中 OpenRAG「保留租户码碰撞」防护 →
   `GET /api/v1/rag-proxy/collections` 由 200 变 **400 `BIZ_RESERVED_TENANT_CODE_COLLISION`**。
   当时裁定走**方案 B**：不注入身份头（`rag_inject_identity_headers=False`）。

2. **DEF-BE-1410-001（v1.4.10，2026-10-08 实测）**：方案 B 的连带后果暴露 ——
   不注入身份头时出站为「匿名 + 仅服务密钥」，OpenRAG M2 对 **write 类方法**要求已绑定主体，
   故全部写类端点（建库/上传/删除/检索/问答/流式问答）恒 **403
   `PERM_SERVICE_KEY_WRITE_DENIED`**，形成「读通写断 / 写通读空」的互斥两难。

3. **R-387 根因消解（本文件 GREEN 目标）**：出站头矩阵实测（`doc/test/evidence/manual/`）
   已证明根因不是「注入」本身，而是**注入的租户码落在 OpenRAG 保留码上或缺省**：

   | 出站形态 | 读 | 写 |
   |---------|:--:|:--:|
   | 仅服务密钥 + 来源（方案 B） | 200（12 项） | **403** |
   | 受信入站 + 无租户头（开关置 true 时 admin 的真实形态） | **400** | **400** |
   | 受信入站 + 非保留码 `tenant-1` | **200**（有数据） | **200** |
   | 受信入站 + 保留码 `default` | 400 | 400 |

   故收口＝**出站租户码恒对齐为非保留码**：保留码（`default`/`openrag-local`）与缺省值
   统一归一到 `settings.rag_default_tenant_code`（非保留），随后恢复身份头注入。
"""

from __future__ import annotations

import json
import types
from dataclasses import dataclass

import pytest

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
from openbase.settings import RAG_RESERVED_TENANT_CODES, get_settings

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


def _user_ctx(tenant_code: str | None = "tenant-1", **overrides) -> dict:
    """统一主体上下文；``tenant_code=None`` 模拟「主体无租户声明」.

    ``tenant_id`` 与 ``tenant_code`` 同源（统一主体上下文下二者一致）；
    无租户声明时同时为 None，避免解析链回落到 id 值而掩盖缺省场景。
    """
    context = {
        "id": "1",
        "username": "admin",
        "tenant_code": tenant_code,
        "tenant_id": tenant_code,
        "org_id": tenant_code,
        "subject_type": "user",
        "role": "admin",
        "permissions": [],
        "auth_method": "jwt",
    }
    context.update(overrides)
    return context


def _set_policy(monkeypatch, enabled: bool) -> None:
    """切换 rag-proxy 身份注入策略（settings 单例属性注入）."""
    monkeypatch.setattr(
        get_settings(), "rag_inject_identity_headers", enabled, raising=False
    )


def _set_fallback(monkeypatch, code: str) -> None:
    """设置 rag 目标出站兜底码（经 A 批 A1/A2 统一登记入口覆盖）."""
    monkeypatch.setattr(
        get_settings(),
        "proxy_code_map",
        json.dumps({"targets": {"rag": {"default_tenant_code": code}}}),
        raising=False,
    )


# ---------------------------------------------------------------------------
# 1) 保留码契约（单一事实源：OpenRAG 实测 payload detail.reserved_codes）
# ---------------------------------------------------------------------------


def test_reserved_tenant_codes_match_openrag_contract() -> None:
    """保留码集合须与 OpenRAG 实测返回一致（防契约漂移后护栏失效）."""
    assert set(RAG_RESERVED_TENANT_CODES) == {"default", "openrag-local"}


# ---------------------------------------------------------------------------
# 2) 出站租户码对齐（R-387 收口主判据）
# ---------------------------------------------------------------------------


def test_rag_proxy_injects_identity_headers_by_default(monkeypatch) -> None:
    """默认（注入开启）：非保留主体码原样透传，四头 + 来源 + 请求 id 齐备."""
    _set_policy(monkeypatch, True)
    _set_fallback(monkeypatch, "tenant-1")

    headers = _build_upstream_headers(StubRequest(), _user_ctx("tenant-2"))

    assert headers[HEADER_USER_ID] == "1"
    assert headers[HEADER_TENANT_ID] == "tenant-2"
    assert headers[HEADER_ORG_ID] == "tenant-2"
    assert headers[HEADER_USER_ROLE] == "admin"
    assert headers[HEADER_PROXY_SOURCE] == PROXY_SOURCE_RAG
    assert headers[HEADER_REQUEST_ID] == "req-chain-0001"
    assert headers["X-API-Key"]


def test_rag_proxy_aligns_reserved_principal_tenant_code(monkeypatch) -> None:
    """主体码为 OpenRAG 保留码 → 对齐为兜底非保留码（不再 400 保留码碰撞）."""
    _set_policy(monkeypatch, True)
    _set_fallback(monkeypatch, "tenant-1")

    headers = _build_upstream_headers(StubRequest(), _user_ctx("default"))

    assert headers[HEADER_TENANT_ID] == "tenant-1"
    assert headers[HEADER_TENANT_ID] not in RAG_RESERVED_TENANT_CODES
    assert headers[HEADER_ORG_ID] == headers[HEADER_TENANT_ID]


def test_rag_proxy_falls_back_when_principal_has_no_tenant_code(monkeypatch) -> None:
    """主体无租户声明 → 补非保留兜底码（修复「缺省即保留码」的 400 根因）.

    实测背景：`admin` 的 JWT 无 `tenant_id`/`tenant_code` 声明，出站若省略
    `X-Tenant-ID`，OpenRAG 受信入站按保留码 `default` 处理 → 读写皆 400。
    """
    _set_policy(monkeypatch, True)
    _set_fallback(monkeypatch, "tenant-1")

    headers = _build_upstream_headers(StubRequest(), _user_ctx(None))

    assert headers[HEADER_TENANT_ID] == "tenant-1"
    assert headers[HEADER_TENANT_ID] not in RAG_RESERVED_TENANT_CODES
    assert headers[HEADER_ORG_ID] == "tenant-1"


def test_rag_proxy_never_emits_reserved_tenant_code(monkeypatch) -> None:
    """兜底码被配置为保留码时：出站**不得**产出保留码（fail-closed 拦在配置面）."""
    _set_policy(monkeypatch, True)
    _set_fallback(monkeypatch, "openrag-local")

    with pytest.raises(Exception) as excinfo:
        _build_upstream_headers(StubRequest(), _user_ctx("tenant-2"))

    assert "openrag-local" in str(excinfo.value)


# ---------------------------------------------------------------------------
# 3) 配置面护栏
# ---------------------------------------------------------------------------
# 说明：兜底码的「启动期」校验（保留码/空值/结构非法 → 拒绝启动）已随 A 批 A1/A2
# 收敛到统一登记入口，护栏见 `tests/test_outbound_tenant_code_space.py`；本文件只保留
# 「rag 目标出厂兜底码非保留」这一 rag 侧不变量。


def test_rag_builtin_default_code_is_non_reserved() -> None:
    """rag 目标出厂兜底码须为非空且非保留码（否则受信入站恒 400）."""
    from openbase.settings import BUILTIN_DEFAULT_TENANT_CODE_BY_TARGET

    default_code = BUILTIN_DEFAULT_TENANT_CODE_BY_TARGET["rag"]

    assert default_code
    assert default_code not in RAG_RESERVED_TENANT_CODES


# ---------------------------------------------------------------------------
# 4) 回滚杠杆（开关仍保留，可一键回到 DEF-BE-147-005 联调口径）
# ---------------------------------------------------------------------------


def test_rag_proxy_omits_identity_headers_when_policy_disabled(monkeypatch) -> None:
    """开关 False（应急回滚）：不注入四头，仅保留服务级认证 + 来源 + 请求 id."""
    _set_policy(monkeypatch, False)

    headers = _build_upstream_headers(StubRequest(), _user_ctx("tenant-1"))

    for name in IDENTITY_HEADERS:
        assert name not in headers, f"策略关闭后不应注入 {name}"
    assert headers[HEADER_PROXY_SOURCE] == PROXY_SOURCE_RAG
    assert headers["X-API-Key"]


def test_rag_proxy_policy_disabled_keeps_request_id_for_chain(monkeypatch) -> None:
    """策略关闭后仍须携带网关 `X-Request-Id`（跨系统串联契约不可回退）."""
    _set_policy(monkeypatch, False)

    headers = _build_upstream_headers(StubRequest(request_id="req-chain-9f9f"), _user_ctx())

    assert headers[HEADER_REQUEST_ID] == "req-chain-9f9f"
