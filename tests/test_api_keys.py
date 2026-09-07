"""测试 v1.4.1 A 类补足（R-367~370）.

覆盖：① ApiKeyStore 签发/校验/吊销；② require_api_key 认证与 scope 校验；
③ get_identity_context 四维身份头解析；④ 审计上下文注入 tenant_id/user_id。
"""

import pytest

from openbase.core.errors import ErrorCode
from openbase.core.errors.codes import ERROR_HTTP_MAP

# ---- 1. 错误码 ----

def test_api_key_error_codes_defined() -> None:
    """服务 Key 认证错误码定义齐全."""
    assert ErrorCode.AUTH_API_KEY_INVALID == "AUTH_API_KEY_INVALID"
    assert ErrorCode.PERM_API_KEY_SCOPE == "PERM_API_KEY_SCOPE"


def test_api_key_error_http_map() -> None:
    """错误码 HTTP 映射正确."""
    assert ERROR_HTTP_MAP[ErrorCode.AUTH_API_KEY_INVALID] == 401
    assert ERROR_HTTP_MAP[ErrorCode.PERM_API_KEY_SCOPE] == 403


# ---- 2. ApiKeyStore ----

def test_api_key_store_create_verify_revoke() -> None:
    """签发/校验/吊销闭环."""
    from openbase.modules.auth.api_keys import ApiKeyStore

    store = ApiKeyStore()
    key = store.create("gateway-agent", scope={"system": ["openllm"], "tenants": ["*"]})
    assert key.startswith("ob_k_")

    # 校验通过
    assert store.verify(key) is not None

    # 吊销后校验失败
    store.revoke(key)
    assert store.verify(key) is None


def test_api_key_store_rejects_unknown_key() -> None:
    """未知 Key 校验失败."""
    from openbase.modules.auth.api_keys import ApiKeyStore

    store = ApiKeyStore()
    assert store.verify("ob_k_unknown") is None


def test_api_key_store_list() -> None:
    """列表返回签发记录（不含明文 Key）."""
    from openbase.modules.auth.api_keys import ApiKeyStore

    store = ApiKeyStore()
    key = store.create("ops-agent")
    records = store.list_keys()
    assert len(records) == 1
    assert records[0]["name"] == "ops-agent"
    assert "key" not in records[0] or records[0]["key"] != key  # 不回显明文


def test_api_key_scope_check() -> None:
    """scope 校验：越系统/越租户拒绝."""
    from openbase.modules.auth.api_keys import ApiKeyStore

    store = ApiKeyStore()
    key = store.create("llm-only", scope={"system": ["openllm"], "tenants": ["tenant_a"]})

    assert store.verify(key, system="openllm", tenant_id="tenant_a") is not None
    assert store.verify(key, system="openrag", tenant_id="tenant_a") is None  # 越系统
    assert store.verify(key, system="openllm", tenant_id="tenant_b") is None  # 越租户


# ---- 3. require_api_key 依赖（HTTP 层） ----

class _FakeRequest:
    """基础请求桩（headers）."""

    def __init__(self, headers: dict[str, str]) -> None:
        self.headers = headers


class _FakeUrl:
    def __init__(self, path: str) -> None:
        self.path = path


class _FakeKeyRequest(_FakeRequest):
    """带 URL path 的请求（scope 校验从路径提取 system）."""

    def __init__(self, headers: dict[str, str], path: str = "/api/v1/proxy/openllm/chat") -> None:
        super().__init__(headers)
        self.url = _FakeUrl(path)


def test_require_api_key_accepts_valid_key() -> None:
    """有效 Key 认证通过并返回凭据."""
    from openbase.core.deps.auth import require_api_key
    from openbase.modules.auth.api_keys import ApiKeyStore

    store = ApiKeyStore()
    key = store.create("svc", scope={"system": ["*"], "tenants": ["*"]})

    request = _FakeKeyRequest({"X-API-Key": key})
    credential = require_api_key(request=request, store=store)
    assert credential is not None
    assert credential["name"] == "svc"


def test_require_api_key_rejects_invalid() -> None:
    """无效 Key → AUTH_API_KEY_INVALID."""
    from openbase.core.deps.auth import require_api_key
    from openbase.core.errors import BaseError
    from openbase.modules.auth.api_keys import ApiKeyStore

    store = ApiKeyStore()
    request = _FakeKeyRequest({"X-API-Key": "ob_k_unknown"})
    with pytest.raises(BaseError) as exc_info:
        require_api_key(request=request, store=store)
    assert exc_info.value.code == ErrorCode.AUTH_API_KEY_INVALID


def test_require_api_key_rejects_scope_mismatch() -> None:
    """scope 不匹配 → PERM_API_KEY_SCOPE."""
    from openbase.core.deps.auth import require_api_key
    from openbase.core.errors import BaseError
    from openbase.modules.auth.api_keys import ApiKeyStore

    store = ApiKeyStore()
    key = store.create("llm-only", scope={"system": ["openllm"], "tenants": ["*"]})

    # 请求路径指向 openrag（越 scope）
    request = _FakeKeyRequest({"X-API-Key": key}, path="/api/v1/proxy/openrag/search")
    with pytest.raises(BaseError) as exc_info:
        require_api_key(request=request, store=store)
    assert exc_info.value.code == ErrorCode.PERM_API_KEY_SCOPE


def test_require_api_key_missing_key() -> None:
    """缺 Key → AUTH_API_KEY_INVALID."""
    from openbase.core.deps.auth import require_api_key
    from openbase.core.errors import BaseError
    from openbase.modules.auth.api_keys import ApiKeyStore

    store = ApiKeyStore()
    request = _FakeKeyRequest({})
    with pytest.raises(BaseError) as exc_info:
        require_api_key(request=request, store=store)
    assert exc_info.value.code == ErrorCode.AUTH_API_KEY_INVALID


def test_require_api_key_accepts_bearer_key() -> None:
    """Authorization: Bearer <key>（非 jwt 前缀）视为服务 Key."""
    from openbase.core.deps.auth import require_api_key
    from openbase.modules.auth.api_keys import ApiKeyStore

    store = ApiKeyStore()
    key = store.create("svc-bearer", scope={"system": ["*"], "tenants": ["*"]})

    request = _FakeKeyRequest({"Authorization": f"Bearer {key}"})
    credential = require_api_key(request=request, store=store)
    assert credential["name"] == "svc-bearer"


def test_require_api_key_x_api_key_header() -> None:
    """X-API-Key 头认证通过（非 proxy 路径时 system=None 不校验 scope）."""
    from openbase.core.deps.auth import require_api_key
    from openbase.modules.auth.api_keys import ApiKeyStore

    store = ApiKeyStore()
    key = store.create("svc", scope={"system": ["openllm"], "tenants": ["*"]})

    # 非 proxy 路径（system=None，scope 校验跳过 system）
    request = _FakeKeyRequest({"X-API-Key": key}, path="/api/v1/items")
    credential = require_api_key(request=request, store=store)
    assert credential["name"] == "svc"


# ---- 4. get_identity_context 四维身份头（P2-1 T3 试点收口）----

def _trusted_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """构造受信来源白名单非空的 settings 单例（P2-1 协议头试点）."""
    import importlib

    from openbase.settings import Settings

    settings = Settings()
    settings.trusted_proxy_sources = "openbase-orchestrator,openbase-memory-proxy"
    settings_module = importlib.import_module("openbase.settings")
    monkeypatch.setattr(settings_module, "_settings", settings)


def test_identity_context_parses_four_headers_with_trusted_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """受信来源（X-Proxy-Source ∈ 白名单）携带四维身份头 → 采纳解析."""
    from openbase.core.deps.auth import get_identity_context

    _trusted_settings(monkeypatch)
    request = _FakeRequest(
        {
            "X-Proxy-Source": "openbase-orchestrator",
            "X-User-Id": "42",
            "X-Tenant-Id": "tenant_a",
            "X-Team-Id": "team_1",
            "X-Agent-Id": "agent_x",
        }
    )
    context = get_identity_context(request)
    assert context.user_id == 42
    assert context.tenant_id == "tenant_a"
    assert context.team_id == "team_1"
    assert context.agent_id == "agent_x"


def test_identity_context_ignores_untrusted_headers() -> None:
    """非受信来源（客户端直连伪造）带四维头 → 忽略（P2-1 T3-6 试点语义）."""
    from openbase.core.deps.auth import get_identity_context

    request = _FakeRequest(
        {
            "X-User-Id": "999",
            "X-Tenant-Id": "evil_tenant",
            "X-Team-Id": "team_1",
            "X-Agent-Id": "agent_x",
        }
    )
    context = get_identity_context(request)
    # 客户端自带头不再作为事实源（identity_headers_ignored 标注）
    assert context.user_id is None
    assert context.tenant_id is None
    assert context.team_id is None
    assert context.agent_id is None


def test_identity_context_handles_missing_headers() -> None:
    """缺省头返回 None 字段（不抛异常）."""
    from openbase.core.deps.auth import get_identity_context

    request = _FakeRequest({})
    context = get_identity_context(request)
    assert context.user_id is None
    assert context.tenant_id is None
    assert context.team_id is None
    assert context.agent_id is None


# ---- 5. 审计上下文注入 ----

def test_audit_record_injects_identity() -> None:
    """审计记录绑定 tenant_id/operator_id（R-370，APICallRecord 结构）."""
    from openbase.core.deps.auth import IdentityContext
    from openbase.modules.audit import APICallRecord, build_audit_record

    context = IdentityContext(user_id=42, tenant_id="tenant_a", team_id="team_1", agent_id="agent_x")
    record = build_audit_record(
        method="GET",
        path="/api/v1/services",
        status_code=200,
        duration_ms=12,
        request_id="req-1",
        identity=context,
    )
    assert record.tenant_id == "tenant_a"
    assert record.operator_id == "42"
    assert isinstance(record, APICallRecord)
