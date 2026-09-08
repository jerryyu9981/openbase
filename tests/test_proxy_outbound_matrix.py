"""P2-1 T1 RED 断言：proxy 族出站矩阵（§3.5 目标矩阵）.

对齐草案 §10 T1：T1-1（user/agent/委托三类出站头）、T1-2、T1-3（sk-agent llm/memory
不再 401）、T1-4、T1-8（逐 proxy 缺失头补齐）、T1-9、T1-10（通用 /proxy 双通道）。
"""
from __future__ import annotations

import types
from dataclasses import dataclass

from openbase.modules import dps_proxy as dps_proxy_module
from openbase.modules import llm_proxy as llm_proxy_module
from openbase.modules.protocol_headers import (
    HEADER_AGENT_ID,
    HEADER_ORG_ID,
    HEADER_PROXY_SOURCE,
    HEADER_REQUEST_ID,
    HEADER_TENANT_ID,
    HEADER_USER_ID,
    HEADER_USER_ROLE,
    PROXY_SOURCE_DPS,
    PROXY_SOURCE_GENERIC,
    PROXY_SOURCE_LLM,
    PROXY_SOURCE_MEMORY,
    PROXY_SOURCE_RAG,
    build_outbound_headers,
)
from openbase.modules.proxy import memory_proxy as memory_proxy_module
from openbase.modules.rag_proxy import _build_upstream_headers as rag_build_headers


@dataclass
class StubRequest:
    """出站装配读请求桩（headers + state.request_id）."""

    headers: dict[str, str]
    request_id: str = "req-out-0001"

    @property
    def state(self) -> types.SimpleNamespace:
        return types.SimpleNamespace(request_id=self.request_id)


def _req() -> StubRequest:
    return StubRequest(headers={})


def _user_ctx(*, role: str = "org_admin", tenant_code: str = "acme") -> dict:
    """普通 user 统一主体上下文."""
    return {
        "id": "42",
        "username": "alice",
        "tenant_code": tenant_code,
        "tenant_id": "tenant-001",
        "org_id": tenant_code,
        "subject_type": "user",
        "role": role,
        "permissions": [],
        "auth_method": "jwt",
    }


def _agent_ctx(agent_id: int = 7) -> dict:
    """agent 统一主体上下文（sk-agent 通道形态）."""
    return {
        "id": agent_id,
        "username": f"agent-{agent_id}",
        "tenant_code": "acme",
        "subject_type": "agent",
        "roles": ["viewer"],
        "auth_method": "sk-agent",
    }


# ---------------------------------------------------------------------------
# T1-8：逐 proxy 缺失头补齐（§3.5 目标列）
# ---------------------------------------------------------------------------


def test_t1_8_dps_proxy_adds_proxy_source_and_request_id() -> None:
    """dps-proxy 补 X-Proxy-Source/X-Request-Id（四头保持不变）."""
    headers = dps_proxy_module._build_identity_headers(_user_ctx(), _req())
    assert headers[HEADER_USER_ID] == "42"
    assert headers[HEADER_TENANT_ID] == "acme"
    assert headers[HEADER_ORG_ID] == "acme"
    assert headers[HEADER_USER_ROLE] == "org_admin"
    assert headers[HEADER_PROXY_SOURCE] == PROXY_SOURCE_DPS  # 补齐
    assert headers[HEADER_REQUEST_ID] == "req-out-0001"  # 补齐


def test_t1_8_llm_proxy_adds_tenant_and_role() -> None:
    """llm-proxy 补 X-Tenant-ID/X-User-Role（原来源/用户保持）."""
    from starlette.requests import Request as StarletteRequest

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/openllm/v1/models",
        "raw_path": b"/openllm/v1/models",
        "query_string": b"",
        "root_path": "",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("test", 80),
        "state": {},
    }
    headers = llm_proxy_module._build_upstream_headers(StarletteRequest(scope), _user_ctx())
    assert headers[HEADER_USER_ID] == "42"
    assert headers[HEADER_TENANT_ID] == "acme"  # 补齐
    assert headers[HEADER_USER_ROLE] == "org_admin"  # 补齐
    assert headers[HEADER_PROXY_SOURCE] == PROXY_SOURCE_LLM
    assert headers["Authorization"].startswith("Bearer sk-openllm-")
    assert "X-API-Key" not in headers


def test_t1_8_memory_proxy_adds_role_and_source() -> None:
    """memory-proxy 补 X-User-Role/X-Proxy-Source（双层认证/默认域保持）."""
    headers = memory_proxy_module._build_upstream_headers(
        StubRequest(headers={"Authorization": "Bearer original.user.jwt"}),
        _user_ctx(),
    )
    assert headers[HEADER_USER_ID] == "42"
    assert headers[HEADER_TENANT_ID] == "acme"
    assert headers[HEADER_USER_ROLE] == "org_admin"  # 补齐
    assert headers[HEADER_PROXY_SOURCE] == PROXY_SOURCE_MEMORY  # 补齐
    assert headers["X-API-Key"]  # 双层认证第一层保持
    # user JWT 场景：透传原 JWT（第二层认证保持）
    assert headers["Authorization"] == "Bearer original.user.jwt"


def test_t1_8_memory_proxy_default_domain_fallback() -> None:
    """memory-proxy 缺省域显式兜底：X-Tenant-ID=default / X-Org-ID=default（T7 别名）."""
    ctx = {
        "id": "1",
        "subject_type": "user",
        "role": None,
        "auth_method": "jwt",
        "on_behalf_of": None,
        "delegated": None,
    }
    headers = memory_proxy_module._build_upstream_headers(_req(), ctx)
    assert headers[HEADER_TENANT_ID] == "default"
    # P2-1 T7（OB-8）：org==tenant 同源别名（openbase-default 默认链退役）
    assert headers[HEADER_ORG_ID] == "default"
    assert headers[HEADER_USER_ROLE] == "viewer"


def test_t1_8_rag_proxy_injects_four_headers_and_source() -> None:
    """rag-proxy 现补四头 + X-Proxy-Source + X-Request-Id（原零身份头）."""
    headers = rag_build_headers(_req(), _user_ctx())
    assert headers[HEADER_USER_ID] == "42"
    assert headers[HEADER_TENANT_ID] == "acme"
    assert headers[HEADER_ORG_ID] == "acme"
    assert headers[HEADER_USER_ROLE] == "org_admin"
    assert headers[HEADER_PROXY_SOURCE] == PROXY_SOURCE_RAG  # 补齐
    assert HEADER_REQUEST_ID in headers  # 补齐
    assert headers.get("X-API-Key")  # X-API-Key 保留（任务书 M1）


# ---------------------------------------------------------------------------
# T1-3：sk-agent 主体出站不再 401（二次解码路径删除）
# ---------------------------------------------------------------------------


def test_t1_3_sk_agent_memory_outbound_no_fake_jwt() -> None:
    """sk-agent 经 memory-proxy：出站头=agent 主体 + 来源；不构造伪 JWT（D-OB6-3）."""
    headers = memory_proxy_module._build_upstream_headers(_req(), _agent_ctx())
    assert headers[HEADER_USER_ID] == "7"
    assert headers[HEADER_PROXY_SOURCE] == PROXY_SOURCE_MEMORY
    assert headers[HEADER_AGENT_ID] == "7"
    assert "Authorization" not in headers  # agent 无原 JWT → 不构造伪 JWT 透传
    assert headers["X-API-Key"]


def test_t1_3_sk_agent_llm_outbound_success() -> None:
    """sk-agent 经 llm-proxy：出站头齐全（原二次解码路径删除，不再 401）."""
    from starlette.requests import Request as StarletteRequest

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/openllm/v1/models",
        "raw_path": b"/openllm/v1/models",
        "query_string": b"",
        "root_path": "",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("test", 80),
        "state": {},
    }
    headers = llm_proxy_module._build_upstream_headers(StarletteRequest(scope), _agent_ctx())
    assert headers[HEADER_USER_ID] == "7"
    assert headers[HEADER_TENANT_ID] == "acme"
    assert headers[HEADER_USER_ROLE] == "viewer"  # agent roles[0]
    assert headers[HEADER_AGENT_ID] == "7"
    assert headers[HEADER_PROXY_SOURCE] == PROXY_SOURCE_LLM


def test_t1_3_sk_agent_dps_outbound_success() -> None:
    """sk-agent 经 dps-proxy：出站头 = agent 主体 + X-Agent-Id + 来源."""
    headers = dps_proxy_module._build_identity_headers(_agent_ctx(), _req())
    assert headers[HEADER_USER_ID] == "7"
    assert headers[HEADER_AGENT_ID] == "7"
    assert headers[HEADER_PROXY_SOURCE] == PROXY_SOURCE_DPS


# ---------------------------------------------------------------------------
# T1-10：通用 /proxy 双通道出站（JWT 与 ob_k_）
# ---------------------------------------------------------------------------


def test_t1_10_generic_proxy_jwt_channel_outbound() -> None:
    """JWT 通道：主体身份头 + X-Proxy-Source + X-Request-Id."""
    headers = build_outbound_headers(
        _req(), _user_ctx(), target_system="generic"
    )
    assert headers[HEADER_USER_ID] == "42"
    assert headers[HEADER_TENANT_ID] == "acme"
    assert headers[HEADER_PROXY_SOURCE] == PROXY_SOURCE_GENERIC
    assert HEADER_REQUEST_ID in headers


def test_t1_10_generic_proxy_service_key_channel_outbound() -> None:
    """ob_k_ 服务 Key 通道：来源标注 + request-id（不构造伪主体身份头）."""
    service_key_credential = {
        "name": "gateway-monitor",
        "scope": {"system": ["*"], "tenants": ["*"]},
    }
    headers = build_outbound_headers(
        _req(), service_key_credential, target_system="generic"
    )
    # resolve_identity 无 id → 不注入伪身份头
    assert HEADER_USER_ID not in headers
    assert headers[HEADER_PROXY_SOURCE] == PROXY_SOURCE_GENERIC
    assert HEADER_REQUEST_ID in headers


# ---------------------------------------------------------------------------
# 委托出站 X-Agent-Id（T1-4；与 dps/llm/memory 委托取值一致）
# ---------------------------------------------------------------------------


def test_t1_4_delegated_outbound_via_builder() -> None:
    """委托请求出站：四头取委托域 + X-Agent-Id=principal agent id."""
    delegated_ctx = {
        "id": 7,
        "subject_type": "agent",
        "tenant_code": "acme",
        "role": "viewer",
        "auth_method": "jwt",
        "delegated": {
            "subject_id": 88,
            "subject_type": "user",
            "tenant_code": "acme",
            "role": "viewer",
        },
    }
    for target, expected_source in (
        ("dps", PROXY_SOURCE_DPS),
        ("llm", PROXY_SOURCE_LLM),
        ("rag", PROXY_SOURCE_RAG),
        ("memory", PROXY_SOURCE_MEMORY),
    ):
        headers = build_outbound_headers(_req(), delegated_ctx, target_system=target)
        assert headers[HEADER_USER_ID] == "88"
        assert headers[HEADER_TENANT_ID] == "acme"
        assert headers[HEADER_ORG_ID] == "acme"
        assert headers[HEADER_USER_ROLE] == "viewer"
        assert headers[HEADER_AGENT_ID] == "7"
        assert headers[HEADER_PROXY_SOURCE] == expected_source
