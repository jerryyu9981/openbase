"""v1.9.0：通用代理 /api/v1/proxy/{system}/{path} 出站来源按被代理系统映射.

背景（全栈功能审计 S6-T5 结论）：通用代理此前固定以 `openbase-generic-proxy` 出站，
而 OpenLLM/OpenRAG/OpenMemory/DPS 的 `TRUSTED_PROXY_SOURCES` 只登记各自的
`openbase-*-proxy`，导致下游「身份头被忽略 → 401」，聚合能力不可达。
本组用例锁定映射关系，防止回归为单一 generic 来源。
"""
from __future__ import annotations

import types

import pytest

from openbase.modules import proxy as proxy_module
from openbase.modules.protocol_headers import (
    HEADER_TENANT_ID,
    PROXY_SOURCE_DPS,
    PROXY_SOURCE_GENERIC,
    PROXY_SOURCE_LLM,
    PROXY_SOURCE_MEMORY,
    PROXY_SOURCE_RAG,
    SOURCE_BY_TARGET_SYSTEM,
    TARGET_SYSTEM_DPS,
    TARGET_SYSTEM_GENERIC,
    TARGET_SYSTEM_LLM,
    TARGET_SYSTEM_MEMORY,
    TARGET_SYSTEM_RAG,
)


class _StopProxy(Exception):
    """在装配出站头后立即中止，避免真实上游调用."""


class _StubRequest:
    """proxy() 读取的最小请求桩."""

    def __init__(self) -> None:
        self.method = "GET"
        self.headers = {"Accept": "application/json"}
        self.state = types.SimpleNamespace(request_id="req-test-v190")

    async def body(self) -> bytes:
        return b""


def _identity() -> dict:
    return {
        "id": "1",
        "username": "admin",
        "tenant_code": "acme",
        "tenant_id": "tenant-001",
        "org_id": "acme",
        "subject_type": "user",
        "role": "admin",
        "permissions": ["*"],
        "auth_method": "jwt",
    }


@pytest.mark.parametrize(
    ("system", "target", "source"),
    [
        ("openllm", TARGET_SYSTEM_LLM, PROXY_SOURCE_LLM),
        ("openrag", TARGET_SYSTEM_RAG, PROXY_SOURCE_RAG),
        ("openmemory", TARGET_SYSTEM_MEMORY, PROXY_SOURCE_MEMORY),
        ("dps", TARGET_SYSTEM_DPS, PROXY_SOURCE_DPS),
    ],
)
def test_target_system_maps_to_registered_proxy_source(
    system: str, target: str, source: str
) -> None:
    """四个被代理系统分别映射到下游已登记的来源常量."""
    assert proxy_module._target_system_of(system) == target
    assert SOURCE_BY_TARGET_SYSTEM[target] == source


def test_unknown_system_falls_back_to_generic() -> None:
    """未登记系统回落 generic，不臆造新来源."""
    assert proxy_module._target_system_of("unknown-system") == TARGET_SYSTEM_GENERIC
    assert SOURCE_BY_TARGET_SYSTEM[TARGET_SYSTEM_GENERIC] == PROXY_SOURCE_GENERIC


async def test_proxy_passes_mapped_target_system(monkeypatch: pytest.MonkeyPatch) -> None:
    """proxy() 出站装配使用映射后的 target_system（不再固定 generic）."""
    captured: dict = {}

    def fake_build(request, identity, *, target_system, extra_headers, enforce_org_alias):  # noqa: ANN001
        captured["target_system"] = target_system
        raise _StopProxy

    monkeypatch.setattr(proxy_module, "build_outbound_headers", fake_build)

    with pytest.raises(_StopProxy):
        await proxy_module.proxy(
            "openllm",
            "api/v1/providers",
            _StubRequest(),
            identity=_identity(),
        )

    assert captured["target_system"] == TARGET_SYSTEM_LLM


class _StubSettings:
    """settings 桩：只需 llm_api_key 与租户 Key 映射."""

    llm_api_key = "ob_llm_test_key"
    llm_api_keys_by_tenant = ""


def test_inject_credentials_for_openllm(monkeypatch: pytest.MonkeyPatch) -> None:
    """openllm → 注入 Authorization: Bearer <OpenLLM API Key>."""
    monkeypatch.setattr(proxy_module, "get_settings", lambda: _StubSettings())
    headers = proxy_module._inject_upstream_credentials(
        "openllm", {HEADER_TENANT_ID: "tenant-1", "Accept": "application/json"}
    )
    assert headers["Authorization"] == "Bearer ob_llm_test_key"


def test_inject_credentials_skipped_for_other_systems(monkeypatch: pytest.MonkeyPatch) -> None:
    """非 openllm 系统不注入凭据，避免越权携带 OpenLLM Key."""
    monkeypatch.setattr(proxy_module, "get_settings", lambda: _StubSettings())
    for system in ("openrag", "openmemory", "dps"):
        headers = proxy_module._inject_upstream_credentials(system, {"Accept": "application/json"})
        assert "Authorization" not in headers
