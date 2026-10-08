"""出站租户码空间统一登记（A 批 A1/A2）：单一登记入口 + 覆盖 + 护栏.

演进脉络：

1. **R-387（DEF-BE-1410-001）**：实测证明根因是「注入的租户码落在 OpenRAG 保留码上或缺省」，
   而非「注入」本身 —— 受信入站 + 非保留码（`tenant-1`）时读、写同时 200。
2. **统一码空间收口**：实测各下游可接受码空间**不同**——`default` 对 OpenRAG 是禁用保留码，
   对 OpenMemory 却是唯一已登记组织码（`tenant-1`/`tenant-2` → 403）。
3. **A 批 A1/A2（本文件 GREEN 目标）**：把码空间登记从「散落字段」收敛为**单一入口**——
   内置基线（`OUTBOUND_RESERVED_TENANT_CODES_BY_TARGET` +
   `BUILTIN_DEFAULT_TENANT_CODE_BY_TARGET`）+ `OPENBASE_PROXY_CODE_MAP` 覆盖，
   并由同一组纯函数在**启动期**（Settings 校验）与**运行期**（code_space 二次防线）校验。

本文件为 TDD 护栏：锁定内置基线、覆盖语义、校验规则与两个 proxy 的实际出站行为。
"""

from __future__ import annotations

import json
import types

import pytest
from pydantic import ValidationError

from openbase.modules.protocol_headers.code_space import (
    get_target_code_space,
    reserved_tenant_map,
)
from openbase.modules.protocol_headers.constants import HEADER_TENANT_ID
from openbase.modules.proxy.memory_proxy import _build_upstream_headers
from openbase.settings import (
    BUILTIN_DEFAULT_TENANT_CODE_BY_TARGET,
    OUTBOUND_RESERVED_TENANT_CODES_BY_TARGET,
    RAG_RESERVED_TENANT_CODES,
    Settings,
    get_settings,
    parse_proxy_code_map,
    resolve_target_code_space,
)

MEMORY_STUB_HEADERS = {"Authorization": "Bearer stub.jwt.token"}


class StubRequest:
    """memory_proxy 出站装配桩（读 Authorization + request_id）."""

    headers = MEMORY_STUB_HEADERS

    @property
    def state(self) -> types.SimpleNamespace:
        return types.SimpleNamespace(request_id="req-mem-0001")


def _user(tenant_code: str | None = None) -> dict:
    """统一主体上下文（默认无租户声明 → 触发目标兜底码）."""
    return {
        "id": "1",
        "username": "admin",
        "tenant_code": tenant_code,
        "tenant_id": tenant_code,
        "subject_type": "user",
        "role": "admin",
        "permissions": [],
        "auth_method": "jwt",
    }


def _set_code_map(monkeypatch, targets: dict) -> None:
    """注入 `proxy_code_map` 覆盖（运行期视图）."""
    monkeypatch.setattr(
        get_settings(), "proxy_code_map", json.dumps({"targets": targets}), raising=False
    )


# ---------------------------------------------------------------------------
# 1) 内置登记基线
# ---------------------------------------------------------------------------


def test_builtin_baseline_declares_reserved_and_default() -> None:
    """内置基线：仅 rag 有保留码；rag/memory 兜底码同为统一非保留码，llm/dps 不设兜底.

    C1-a 终态（2026-10-08）：memory 兜底码由 `default` 切换为 `tenant-1`，
    前提是 OpenMemory 已登记该组织码（编排器 `OPENMEMORY_RBAC__ORG_POLICIES`）。
    """
    assert set(OUTBOUND_RESERVED_TENANT_CODES_BY_TARGET["rag"]) == {"default", "openrag-local"}
    assert OUTBOUND_RESERVED_TENANT_CODES_BY_TARGET["memory"] == frozenset()
    assert BUILTIN_DEFAULT_TENANT_CODE_BY_TARGET == {"rag": "tenant-1", "memory": "tenant-1"}
    assert "llm" not in BUILTIN_DEFAULT_TENANT_CODE_BY_TARGET
    assert "dps" not in BUILTIN_DEFAULT_TENANT_CODE_BY_TARGET


def test_builtin_defaults_are_non_reserved_for_their_target() -> None:
    """统一空间终态不变量：任一目标的兜底码都不得是**该目标**的保留码."""
    for target, code in BUILTIN_DEFAULT_TENANT_CODE_BY_TARGET.items():
        assert code not in OUTBOUND_RESERVED_TENANT_CODES_BY_TARGET[target]


def test_rag_reserved_alias_points_to_registry() -> None:
    """RAG 保留码别名须指向登记表（单一事实源，防两处漂移）."""
    assert RAG_RESERVED_TENANT_CODES == OUTBOUND_RESERVED_TENANT_CODES_BY_TARGET["rag"]


def test_resolved_baseline_without_override() -> None:
    """未配置覆盖时：解析结果等于内置基线."""
    resolved = resolve_target_code_space("")

    assert resolved["rag"]["default_tenant_code"] == "tenant-1"
    assert resolved["memory"]["default_tenant_code"] == "tenant-1"
    assert resolved["llm"]["default_tenant_code"] is None
    assert resolved["dps"]["default_tenant_code"] is None


def test_unknown_target_has_no_reserved_and_no_default() -> None:
    """未登记目标 → 安全空登记（无保留码、不设兜底），不抛错."""
    space = get_target_code_space("not-registered")

    assert space.reserved_codes == frozenset()
    assert space.default_tenant_code is None
    assert space.has_default is False
    assert space.reserved_map() == {}


# ---------------------------------------------------------------------------
# 2) 覆盖语义
# ---------------------------------------------------------------------------


def test_parse_rejects_invalid_json_and_structure() -> None:
    """覆盖表非法 → fail-fast（禁静默降级）."""
    with pytest.raises(ValueError):
        parse_proxy_code_map("{not-json")
    with pytest.raises(ValueError):
        parse_proxy_code_map("[]")
    with pytest.raises(ValueError):
        parse_proxy_code_map('{"targets": []}')
    with pytest.raises(ValueError):
        parse_proxy_code_map('{"targets": {"rag": {"reserved_codes": "default"}}}')


def test_override_changes_rag_default_and_mapping(monkeypatch) -> None:
    """覆盖 rag 兜底码 → 解析与保留码归一映射同步变化."""
    _set_code_map(monkeypatch, {"rag": {"default_tenant_code": "tenant-2"}})

    space = get_target_code_space("rag")

    assert space.default_tenant_code == "tenant-2"
    assert reserved_tenant_map("rag") == {"default": "tenant-2", "openrag-local": "tenant-2"}


def test_override_can_replace_reserved_set(monkeypatch) -> None:
    """覆盖保留码集合 → 归一映射随新的集合变化（防契约漂移后护栏失效）."""
    _set_code_map(
        monkeypatch,
        {"rag": {"reserved_codes": ["legacy-code"], "default_tenant_code": "tenant-1"}},
    )

    space = get_target_code_space("rag")

    assert space.reserved_codes == frozenset({"legacy-code"})
    assert reserved_tenant_map("rag") == {"legacy-code": "tenant-1"}


def test_override_declaring_default_enables_fallback_for_new_target(monkeypatch) -> None:
    """为原本不设兜底的目标声明兜底码 → 该目标获得兜底与归一能力."""
    _set_code_map(monkeypatch, {"llm": {"default_tenant_code": "tenant-2"}})

    space = get_target_code_space("llm")

    assert space.has_default is True
    assert space.default_tenant_code == "tenant-2"


# ---------------------------------------------------------------------------
# 3) 配置面护栏（启动即拒）
# ---------------------------------------------------------------------------


def test_settings_reject_reserved_default_code() -> None:
    """兜底码命中该目标保留码 → 启动失败."""
    payload = json.dumps({"targets": {"rag": {"default_tenant_code": "openrag-local"}}})
    with pytest.raises(ValidationError):
        Settings(proxy_code_map=payload)


def test_settings_reject_blank_default_code() -> None:
    """兜底码出现但为空 → 启动失败（空值会使受信入站缺头，退化为隐式默认）."""
    payload = json.dumps({"targets": {"rag": {"default_tenant_code": ""}}})
    with pytest.raises(ValidationError):
        Settings(proxy_code_map=payload)


def test_settings_reject_malformed_code_map() -> None:
    """覆盖表结构非法 → 启动失败."""
    with pytest.raises(ValidationError):
        Settings(proxy_code_map='{"targets": {"rag": {"reserved_codes": 1}}}')


def test_settings_default_code_map_is_empty_and_valid() -> None:
    """出厂默认：无覆盖（空串），且默认构造通过校验."""
    settings = Settings()

    assert settings.proxy_code_map == ""
    assert get_target_code_space("rag") is not None


# ---------------------------------------------------------------------------
# 4) 实际出站行为（memory 目标）
# ---------------------------------------------------------------------------


def test_memory_outbound_uses_registered_default(monkeypatch) -> None:
    """memory 兜底码来自登记（终态 tenant-1）→ 出站值随登记变化."""
    _set_code_map(monkeypatch, {})

    headers = _build_upstream_headers(StubRequest(), _user(None))

    assert headers[HEADER_TENANT_ID] == "tenant-1"


def test_memory_outbound_follows_override(monkeypatch) -> None:
    """覆盖 memory 兜底码 → 出站值随之变化（证明无写死字面量）."""
    _set_code_map(monkeypatch, {"memory": {"default_tenant_code": "mem-space"}})

    headers = _build_upstream_headers(StubRequest(), _user(None))

    assert headers[HEADER_TENANT_ID] == "mem-space"


def test_memory_outbound_passes_through_principal_code(monkeypatch) -> None:
    """主体有租户声明时原样透传（memory 目标未声明保留码，无需归一）."""
    _set_code_map(monkeypatch, {})

    headers = _build_upstream_headers(StubRequest(), _user("tenant-2"))

    assert headers[HEADER_TENANT_ID] == "tenant-2"
