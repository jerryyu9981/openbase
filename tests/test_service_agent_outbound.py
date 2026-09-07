"""P2-1 T5 RED 断言：OB-6 sk-agent 统一出站与审计（§9.1/§10 T5）.

对齐草案 §10 T5：
- T5-1  sk-agent 经 dps-proxy 出站：四头 + X-Proxy-Source + X-Agent-Id
- T5-2  sk-agent 经 rag-proxy 出站：四头齐全且域正确（原零身份头已注入）
- T5-3  sk-agent 经 memory-proxy 出站不再 401：X-API-Key+四头+来源+X-Agent-Id（无伪 JWT）
- T5-4  sk-agent 经 llm-proxy 出站：X-User-ID/X-Tenant-ID/X-User-Role/来源齐全
- T5-5  agent 匿名直连写子系统 → 拒绝（0 可达）：写端点全量受信认证 + 无效 agent 直写 401
- T5-6  agent 出站审计：identity.principal.subject_type=agent + agent_id + proxy_source
        + tenant_code + action（审计记录 detail/extra 贯穿）
- T5-7  U1 agent 密钥面回归守卫（发放/轮换/吊销语义常量不回退）
- 附加：批次 1 遗留通用 proxy ob_k_「服务账号主体映射」（草案 §3.7 例 3）
"""
from __future__ import annotations

import asyncio
import importlib
import json
import types
from typing import Any

import pytest
from fastapi.testclient import TestClient

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
from openbase.settings import Settings

_SECRET = "p21-test-secret-0123456789abcdef0123456789abcdef"
_WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_PROXY_PREFIXES = (
    "/api/v1/dps-proxy",
    "/api/v1/llm-proxy",
    "/api/v1/rag-proxy",
    "/api/v1/memory-proxy",
    "/api/v1/proxy",
)


def _req(request_id: str = "req-t5-0001") -> types.SimpleNamespace:
    return types.SimpleNamespace(
        headers={},
        state=types.SimpleNamespace(request_id=request_id),
    )


def _agent_ctx(agent_id: int = 7, *, role: str = "viewer") -> dict:
    """sk-agent 通道统一主体上下文（resolve_agent_principal 返回形态）."""
    return {
        "id": agent_id,
        "username": f"agent-{agent_id}",
        "tenant_code": "acme",
        "subject_type": "agent",
        "roles": [role],
        "permissions": [],
        "status_state": "active",
        "token_version": 0,
        "auth_method": "sk-agent",
    }


def _apply_settings(monkeypatch: pytest.MonkeyPatch, **overrides: object) -> Settings:
    settings = Settings(jwt_secret=_SECRET, **overrides)
    module = importlib.import_module("openbase.settings")
    monkeypatch.setattr(module, "_settings", settings)
    return settings


# ---------------------------------------------------------------------------
# T5-1 / T5-2 / T5-3 / T5-4：四 proxy sk-agent 统一出站
# ---------------------------------------------------------------------------


def test_t5_1_sk_agent_dps_outbound_identity_headers_full() -> None:
    """sk-agent 经 dps-proxy：四头 + X-Proxy-Source=dps + X-Agent-Id=agent id."""
    headers = dps_proxy_module._build_identity_headers(_agent_ctx(), _req())
    assert headers[HEADER_USER_ID] == "7"
    assert headers[HEADER_TENANT_ID] == "acme"
    assert headers[HEADER_ORG_ID] == "acme"
    assert headers[HEADER_USER_ROLE] == "viewer"
    assert headers[HEADER_PROXY_SOURCE] == PROXY_SOURCE_DPS
    assert headers[HEADER_REQUEST_ID] == "req-t5-0001"
    assert headers[HEADER_AGENT_ID] == "7"


def test_t5_2_sk_agent_rag_outbound_four_headers() -> None:
    """sk-agent 经 rag-proxy：四头齐全且域正确（原零身份头现已注入）."""
    headers = rag_build_headers(_req(), _agent_ctx(agent_id=9))
    assert headers[HEADER_USER_ID] == "9"
    assert headers[HEADER_TENANT_ID] == "acme"
    assert headers[HEADER_ORG_ID] == "acme"
    assert headers[HEADER_USER_ROLE] == "viewer"
    assert headers[HEADER_PROXY_SOURCE] == PROXY_SOURCE_RAG
    assert headers[HEADER_AGENT_ID] == "9"
    assert headers.get("X-API-Key")  # 服务级 Key 保留（任务书 M1）


def test_t5_3_sk_agent_memory_outbound_contract() -> None:
    """sk-agent 经 memory-proxy：X-API-Key+四头+来源+X-Agent-Id；无伪 JWT（D-OB6-3）."""
    headers = memory_proxy_module._build_upstream_headers(
        _req(), _agent_ctx(agent_id=7)
    )
    assert headers[HEADER_USER_ID] == "7"
    assert headers[HEADER_TENANT_ID] == "acme"
    assert headers[HEADER_USER_ROLE] == "viewer"
    assert headers[HEADER_PROXY_SOURCE] == PROXY_SOURCE_MEMORY
    assert headers[HEADER_AGENT_ID] == "7"
    assert headers["X-API-Key"]
    assert "Authorization" not in headers  # agent 无原 JWT → 不构造伪 JWT


def test_t5_4_sk_agent_llm_outbound_headers() -> None:
    """sk-agent 经 llm-proxy：X-User-ID/X-Tenant-ID/X-User-Role/来源齐全."""
    headers = llm_proxy_module._build_upstream_headers(_req(), _agent_ctx(agent_id=5))
    assert headers[HEADER_USER_ID] == "5"
    assert headers[HEADER_TENANT_ID] == "acme"
    assert headers[HEADER_USER_ROLE] == "viewer"
    assert headers[HEADER_PROXY_SOURCE] == PROXY_SOURCE_LLM
    assert headers[HEADER_AGENT_ID] == "5"
    assert headers["Authorization"].startswith("Bearer sk-openllm-")


# ---------------------------------------------------------------------------
# T5-5：agent 匿名直连写拒绝（全量断言 + 集成 401）
# ---------------------------------------------------------------------------


def _dependency_call_names(route: Any, seen: set[int] | None = None) -> set[str]:
    """收集路由依赖树中的 call 名（递归 Dependant.dependencies）."""
    names: set[str] = set()
    seen = seen or set()
    stack = [getattr(route, "dependant", None)]
    while stack:
        dependant = stack.pop()
        if dependant is None or id(dependant) in seen:
            continue
        seen.add(id(dependant))
        call = getattr(dependant, "call", None)
        if call is not None:
            names.add(getattr(call, "__name__", str(call)))
        stack.extend(getattr(dependant, "dependencies", None) or [])
    return names


def _iter_routes(*routers: Any) -> list[Any]:
    """迭代 APIRouter.routes 中的具名路由（兼容 FastAPI 嵌套 _IncludedRouter）."""
    collected: list[Any] = []
    for router in routers:
        for route in getattr(router, "routes", []) or []:
            sub = getattr(route, "routes", None)
            if isinstance(sub, list) and sub:
                collected.extend(_iter_routes(route))
            else:
                collected.append(route)
    return collected


def test_t5_5_all_proxy_write_routes_require_authn_dependency() -> None:
    """全量扫描：四 proxy + 通用 /proxy 所有写端点均依赖 get_current_user/
    get_proxy_identity 认证（agent 匿名直连写 0 可达）."""
    from openbase.modules import dps_proxy as dps_proxy_router_module
    from openbase.modules import llm_proxy as llm_proxy_router_module
    from openbase.modules import proxy as proxy_pkg
    from openbase.modules import rag_proxy as rag_proxy_router_module
    from openbase.modules.proxy import memory_proxy as memory_proxy_router_module

    routers = (
        dps_proxy_router_module.router,
        llm_proxy_router_module.router,
        rag_proxy_router_module.router,
        memory_proxy_router_module.router,
        proxy_pkg.router,
    )
    auth_deps = {"get_current_user", "get_proxy_identity"}
    violations: list[str] = []
    scanned = 0
    for route in _iter_routes(*routers):
        methods = set(getattr(route, "methods", None) or [])
        path = str(getattr(route, "path", ""))
        if not any(path.startswith(prefix) for prefix in _PROXY_PREFIXES):
            continue
        if not (methods & _WRITE_METHODS):
            continue
        scanned += 1
        if not (_dependency_call_names(route) & auth_deps):
            violations.append(f"{sorted(methods)} {path}")
    assert scanned > 0, "未扫描到任何 proxy 写端点"
    assert violations == [], f"存在无认证依赖的代理写端点: {violations}"


def test_t5_5_invalid_agent_key_direct_write_401(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sk-agent 无效密钥直连写 dps-proxy → 401/403（不落上游，0 可达直写）."""
    from openbase import init_app
    from openbase.modules.auth import UserService

    settings = _apply_settings(monkeypatch, dps_health_check_enabled=False)
    for module_name in ("auth", "proxy", "dps_proxy", "audit", "tenant", "config"):
        settings.enable_module(module_name)
    UserService.seed_memory_user("admin", "admin123")
    client = TestClient(init_app(settings))
    resp = client.post(
        "/api/v1/dps-proxy/portraits/calculate",
        json={"person_id": 1},
        headers={"Authorization": "Bearer sk-agent-invalid-key-000000000000"},
    )
    assert resp.status_code in (401, 403), resp.text


# ---------------------------------------------------------------------------
# T5-6：agent 出站审计 detail.identity 贯穿
# ---------------------------------------------------------------------------


def test_t5_6_enqueue_proxy_outbound_audit_agent_record() -> None:
    """agent 出站审计落库（AuditLog）：action=proxy.outbound + detail.identity
    principal.subject_type=agent + agent_id + proxy_source + tenant_code."""
    from openbase.core.models import AuditLog
    from openbase.modules.protocol_headers.identity_audit import (
        enqueue_proxy_outbound_audit,
    )

    added: list[AuditLog] = []

    class _RecordingSession:
        async def flush(self) -> None:
            return None

        def add(self, record: AuditLog) -> None:
            added.append(record)

    async def _run() -> None:
        await enqueue_proxy_outbound_audit(
            _RecordingSession(),
            user_ctx=_agent_ctx(agent_id=7),
            target_system="dps",
            method="POST",
            path="/api/v2/portrait/calculate",
            request_id="req-t5-6",
        )

    asyncio.run(_run())
    assert len(added) == 1
    record = added[0]
    assert record.action == "proxy.outbound"
    identity = record.detail["identity"]
    assert identity["principal"]["subject_type"] == "agent"
    assert str(identity["principal"]["subject_id"]) == "7"
    assert identity["principal"]["tenant_code"] == "acme"
    assert identity["principal"]["auth_method"] == "sk-agent"
    assert identity["proxy_source"] == PROXY_SOURCE_DPS
    assert record.request_id == "req-t5-6"
    assert record.detail["system"] == "dps"
    assert record.detail["method"] == "POST"


def test_t5_6_get_current_user_attaches_audit_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """get_current_user 解析 sk-agent principal 后写入 request.state.identity."""
    from starlette.requests import Request as StarletteRequest

    from openbase.core.deps.auth import get_current_user
    from openbase.modules.identity import agent_keys as agent_keys_module

    async def _fake_resolve_agent_principal(
        _session: Any, _raw_key: str
    ) -> dict[str, Any]:
        return _agent_ctx(agent_id=7)

    monkeypatch.setattr(
        agent_keys_module, "resolve_agent_principal", _fake_resolve_agent_principal
    )
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/api/v1/dps-proxy/portraits",
        "raw_path": b"/api/v1/dps-proxy/portraits",
        "query_string": b"",
        "root_path": "",
        "headers": [
            (b"authorization", b"Bearer sk-agent-test-token-0000000000000000"),
        ],
        "client": ("127.0.0.1", 12345),
        "server": ("test", 80),
        "state": {},
    }
    request = StarletteRequest(scope)
    principal = asyncio.run(get_current_user(request, None))
    assert principal["id"] == 7
    identity = request.state.identity
    assert identity["principal"]["subject_type"] == "agent"
    assert str(identity["principal"]["subject_id"]) == "7"
    assert identity["principal"]["auth_method"] == "sk-agent"


def test_t5_6_audit_middleware_records_identity_detail() -> None:
    """AuditMiddleware._record 读 request.state.identity 并入 extra（审计记录含身份）."""
    from starlette.requests import Request as StarletteRequest

    from openbase.modules.audit import AuditMiddleware, AuditService

    middleware = AuditMiddleware(app=object())  # type: ignore[arg-type]
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/v1/dps-proxy/portraits/calculate",
        "raw_path": b"/api/v1/dps-proxy/portraits/calculate",
        "query_string": b"",
        "root_path": "",
        "headers": [(b"authorization", b"Bearer sk-agent-test-token-00000000000000")],
        "client": ("127.0.0.1", 12345),
        "server": ("test", 80),
        "state": {},
    }
    request = StarletteRequest(scope)
    request.state.identity = {
        "principal": {
            "subject_id": "7",
            "subject_type": "agent",
            "tenant_code": "acme",
            "role": "viewer",
            "auth_method": "sk-agent",
        },
        "delegated": None,
        "effective": {
            "subject_id": "7",
            "subject_type": "agent",
            "tenant_code": "acme",
            "role": "viewer",
        },
        "proxy_source": PROXY_SOURCE_DPS,
        "request_id": "req-t5-6",
        "org_alias": "acme",
    }
    before = len(AuditService._records)
    middleware._record(request, 200, 5, "req-t5-6")
    record = AuditService._records[before]
    assert record.extra.get("identity", {}).get("principal", {}).get(
        "subject_type"
    ) == "agent"
    assert record.extra["identity"]["proxy_source"] == PROXY_SOURCE_DPS


def test_t5_6_builder_attaches_identity_state() -> None:
    """build_outbound_headers（唯一出站装配点）装配 agent 出站时写入
    request.state.identity（principal subject_type=agent + proxy_source）."""
    request = _req(request_id="req-t5-6b")
    headers = build_outbound_headers(
        request,
        _agent_ctx(agent_id=7),
        target_system="dps",
    )
    assert headers[HEADER_USER_ROLE] == "viewer"
    identity = request.state.identity
    assert identity["principal"]["subject_type"] == "agent"
    assert str(identity["principal"]["subject_id"]) == "7"
    assert identity["proxy_source"] == PROXY_SOURCE_DPS
    assert identity["request_id"] == "req-t5-6b"


# ---------------------------------------------------------------------------
# identity_audit 边界（§8.2 schema 纯函数 + attach 守卫 + enqueue 分支）
# ---------------------------------------------------------------------------


def test_identity_audit_principal_none_and_no_ctx() -> None:
    """无主体 id / user_ctx=None → principal=None（不构造伪主体审计块）."""
    from openbase.modules.protocol_headers.identity_audit import (
        build_identity_detail,
        build_principal_block,
    )

    assert build_principal_block({"scope": {"system": ["*"]}}) is None
    detail = build_identity_detail(None, proxy_source=PROXY_SOURCE_DPS)
    assert detail["principal"] is None
    assert detail["delegated"] is None
    assert detail["effective"] is None
    assert detail["proxy_source"] == PROXY_SOURCE_DPS
    assert detail["request_id"].startswith("req-")


def test_identity_audit_delegated_and_chain_blocks() -> None:
    """agent 委托 user 的审计块：delegated/effective=委托目标，principal=agent."""
    from openbase.modules.protocol_headers.identity_audit import (
        build_identity_detail,
    )

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
    detail = build_identity_detail(
        delegated_ctx,
        proxy_source=PROXY_SOURCE_LLM,
        request_id="req-ident-1",
        org_alias="acme",
        proxy_chain=["openbase-orchestrator", PROXY_SOURCE_LLM],
    )
    assert detail["principal"]["subject_type"] == "agent"
    assert str(detail["principal"]["subject_id"]) == "7"
    assert str(detail["delegated"]["subject_id"]) == "88"
    assert str(detail["effective"]["subject_id"]) == "88"
    assert detail["effective"]["role"] == "viewer"
    assert detail["proxy_chain"] == ["openbase-orchestrator", PROXY_SOURCE_LLM]
    assert detail["request_id"] == "req-ident-1"
    assert detail["org_alias"] == "acme"


def test_attach_outbound_identity_guard_clauses() -> None:
    """attach 守卫：无 request / 非 dict ctx / 无 id ctx → 不写 state."""
    from openbase.modules.protocol_headers.identity_audit import (
        attach_outbound_identity,
    )

    attach_outbound_identity(None, _agent_ctx(), proxy_source=PROXY_SOURCE_DPS)
    attach_outbound_identity(object(), None, proxy_source=PROXY_SOURCE_DPS)
    # 无 state 的请求对象：静默跳过
    attach_outbound_identity(
        types.SimpleNamespace(), _agent_ctx(), proxy_source=PROXY_SOURCE_DPS
    )
    # 服务 Key 凭据（无 id）→ 不写入（避免伪主体标注）
    service_key = {"name": "svc", "scope": {"system": ["*"]}}
    request = _req()
    attach_outbound_identity(request, service_key, proxy_source=PROXY_SOURCE_DPS)
    assert not hasattr(request.state, "identity")
    # 有效主体 → 写入（principal.subject_type=agent）
    attach_outbound_identity(request, _agent_ctx(), proxy_source=PROXY_SOURCE_DPS)
    assert request.state.identity["principal"]["subject_type"] == "agent"


def test_enqueue_proxy_outbound_audit_branches() -> None:
    """enqueue 分支：非数字 subject_id → user_id=None；显式 proxy_source 覆盖."""
    from openbase.core.models import AuditLog
    from openbase.modules.protocol_headers.identity_audit import (
        enqueue_proxy_outbound_audit,
    )

    added: list[AuditLog] = []

    class _RecordingSession:
        async def flush(self) -> None:
            return None

        def add(self, record: AuditLog) -> None:
            added.append(record)

    async def _run() -> None:
        await enqueue_proxy_outbound_audit(
            _RecordingSession(),
            user_ctx={
                "id": "oidc-external-subject",
                "subject_type": "user",
                "tenant_code": "acme",
                "role": "admin",
                "auth_method": "jwt",
            },
            target_system="dps",
            method="GET",
            path="/health",
            proxy_source=PROXY_SOURCE_DPS,
        )

    asyncio.run(_run())
    assert len(added) == 1
    record = added[0]
    assert record.action == "proxy.outbound"
    assert record.user_id is None  # 非数字 sub → 不落 user_id 结构列
    assert record.detail["identity"]["principal"]["subject_type"] == "user"
    assert record.detail["identity"]["proxy_source"] == PROXY_SOURCE_DPS
    assert record.detail["system"] == "dps"


# ---------------------------------------------------------------------------
# T5-7：U1 agent 密钥面回归守卫（发放/轮换/吊销语义不回退）
# ---------------------------------------------------------------------------


def test_t5_7_u1_key_surface_regression_guard() -> None:
    """U1 密钥面常量与哈希语义不回退（sk-agent 发放/轮换/吊销的既有契约）."""
    from openbase.modules.identity.agent_keys import (
        AGENT_KEY_PREFIX,
        AGENT_KEY_STATUS_ACTIVE,
        AGENT_KEY_STATUS_REVOKED,
        AgentKeyService,
        agent_key_hash,
        secrets_token_urlsafe,
    )

    assert AGENT_KEY_PREFIX == "sk-agent-"
    assert AGENT_KEY_STATUS_ACTIVE == "active"
    assert AGENT_KEY_STATUS_REVOKED == "revoked"
    assert hasattr(AgentKeyService, "issue_key")
    assert hasattr(AgentKeyService, "revoke_key")
    assert hasattr(AgentKeyService, "list_keys")
    raw_key = f"{AGENT_KEY_PREFIX}{secrets_token_urlsafe()}"
    digest = agent_key_hash(raw_key)
    assert digest == agent_key_hash(raw_key)  # 确定性哈希（轮换/吊销按 key_hash 查库）
    assert digest != raw_key
    assert raw_key.startswith("sk-agent-")


# ---------------------------------------------------------------------------
# 批次 1 遗留：通用 proxy ob_k_「服务账号主体映射」（草案 §3.7 例 3 / §5.2 D-V6）
# ---------------------------------------------------------------------------


def test_obk_service_account_subject_mapping_unit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """服务账号映射：ob_k_ 凭据 name 命中配置 → 服务账号主体上下文（例 3）. """
    from openbase.modules.proxy import _resolve_service_account_subject

    _apply_settings(
        monkeypatch,
        service_account_subject_map=json.dumps(
            [
                {
                    "name": "gateway-monitor",
                    "subject_id": 5001,
                    "tenant_code": "acme",
                    "role": "viewer",
                }
            ]
        ),
    )
    mapped = _resolve_service_account_subject(
        {"name": "gateway-monitor", "scope": {"system": ["*"]}}
    )
    assert mapped is not None
    assert mapped["id"] == 5001
    assert mapped["tenant_code"] == "acme"
    assert mapped["role"] == "viewer"
    assert mapped["auth_method"] == "service-key"

    # 未登记服务 Key → None（不构造伪主体身份头）
    assert _resolve_service_account_subject({"name": "unknown-svc"}) is None


def test_obk_service_account_mapped_outbound_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """例 3：绑定 read 服务账号的 ob_k_ 服务 Key 经通用 /proxy 读 OpenRAG——
    出站带 X-User-ID=5001/X-Tenant-ID/X-User-Role=viewer + X-Proxy-Source."""
    import httpx

    from openbase import init_app
    from openbase.modules.auth import UserService

    settings = _apply_settings(monkeypatch)
    for module_name in ("auth", "proxy", "audit", "tenant", "config"):
        settings.enable_module(module_name)
    UserService.seed_memory_user("admin", "admin123")

    class FakeResponse:
        status_code = 200

        def json(self) -> dict:
            return {"ok": True}

    captured: list[dict] = []

    class FakeAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.request_calls: list[dict] = []
            captured.append(self.request_calls)

        async def __aenter__(self) -> FakeAsyncClient:
            return self

        async def __aexit__(self, *args: Any) -> bool:
            return False

        async def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
            self.request_calls.append({"method": method, "url": url, **kwargs})
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    client = TestClient(init_app(settings))

    admin_token = client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "admin123"}
    ).json()["access_token"]
    key_name = "svc-obk-monitor"
    created = client.post(
        "/api/v1/auth/api-keys",
        json={"name": key_name, "scope": {"system": ["openrag"], "tenants": ["*"]}},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert created.status_code == 200, created.text
    raw_key = created.json()["key"]
    settings.service_account_subject_map = json.dumps(
        [
            {
                "name": key_name,
                "subject_id": 5001,
                "tenant_code": "acme",
                "role": "viewer",
            }
        ]
    )

    resp = client.get(
        "/api/v1/proxy/openrag/api/v1/collections",
        headers={"X-API-Key": raw_key},
    )
    assert resp.status_code == 200, resp.text
    outbound_headers = captured[-1][0]["headers"]
    assert outbound_headers.get(HEADER_USER_ID) == "5001"
    assert outbound_headers.get(HEADER_TENANT_ID) == "acme"
    assert outbound_headers.get(HEADER_ORG_ID) == "acme"
    assert outbound_headers.get(HEADER_USER_ROLE) == "viewer"
    assert outbound_headers.get(HEADER_PROXY_SOURCE) == PROXY_SOURCE_GENERIC
    assert HEADER_REQUEST_ID in outbound_headers
