"""P2-1 T8 RED 断言：OB-13 审计贯穿（§8/§10 T8）.

对齐草案 §10 T8：
- T8-1  audit_logs.detail.identity schema 完整（principal/delegated/effective/
        proxy_source/proxy_chain/request_id 六键；lifecycle/delegation/purge 并入）
- T8-2  委托请求代理出站审计：detail 两层 + X-Agent-Id principal 一致（抽样比对）
- T8-3  代理出站审计钩子用例绿：record_proxy_hop 落库 action=proxy.outbound 且
        request_id 与入站一致（AuditMiddleware 响应后接线）
- T8-4  sk-agent 直连端点审计含 agent_id+source+域+动作（§8.3）
- T8-5  中间件链路：AuthMiddleware 写 request.state.identity → AuditMiddleware 记录
- T8-6  既有字段不回退：user_id/tenant_id/request_id 列与委托签发审计 schema 兼容
- T8-7  U4 联动边界文档化（§8.1 D-OB13-3）
"""
from __future__ import annotations

import asyncio
import types
from pathlib import Path

import pytest

from openbase.core.models import AuditLog
from openbase.modules.audit import ENV_AUDIT_DB_PERSIST, audit_persist_queue
from openbase.modules.identity.delegation import (
    DELEGATION_ACTION_ISSUE,
    enqueue_delegation_audit,
)
from openbase.modules.protocol_headers import (
    HEADER_AGENT_ID,
    HEADER_TENANT_ID,
    HEADER_USER_ID,
    HEADER_USER_ROLE,
    PROXY_SOURCE_DPS,
    PROXY_SOURCE_RAG,
    build_outbound_headers,
)
from openbase.modules.protocol_headers.identity_audit import (
    ACTION_PROXY_OUTBOUND,
    build_identity_section,
    enqueue_proxy_outbound_audit,
    record_proxy_hop,
)

_ROOT = Path(__file__).resolve().parent.parent

_IDENTITY_KEYS = {
    "principal",
    "delegated",
    "effective",
    "proxy_source",
    "proxy_chain",
    "request_id",
}


class _RecordingSession:
    """记录 add/flush/commit 的假会话（DB 免依赖审计断言）."""

    def __init__(self) -> None:
        self.added: list[AuditLog] = []
        self.committed = False

    def add(self, record: AuditLog) -> None:
        self.added.append(record)

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        return None


def _req(request_id: str = "req-t8-0001") -> types.SimpleNamespace:
    return types.SimpleNamespace(
        headers={},
        state=types.SimpleNamespace(request_id=request_id),
    )


def _agent_ctx(agent_id: int = 7) -> dict:
    return {
        "id": agent_id,
        "username": f"agent-{agent_id}",
        "tenant_code": "acme",
        "subject_type": "agent",
        "roles": ["viewer"],
        "permissions": [],
        "status_state": "active",
        "auth_method": "sk-agent",
    }


def _delegated_agent_ctx(agent_id: int = 7) -> dict:
    """委托场景统一主体上下文（agent principal + on_behalf_of user）. """
    ctx = _agent_ctx(agent_id)
    ctx["delegated"] = {
        "subject_id": 88,
        "subject_type": "user",
        "tenant_code": "acme",
        "role": "viewer",
    }
    return ctx


def _assert_identity_keys(identity: dict) -> None:
    """T8-1：§8.2 identity 块六键完整（值可为 None，键必须存在）."""
    assert isinstance(identity, dict)
    assert _IDENTITY_KEYS <= set(identity), f"identity schema missing keys: {_IDENTITY_KEYS - set(identity)}"


# ---------------------------------------------------------------------------
# T8-1：audit_logs.detail.identity schema 完整
# ---------------------------------------------------------------------------


def test_t8_1_proxy_outbound_identity_schema_complete() -> None:
    """proxy.outbound 落库 detail.identity 六键完整（§8.2）. """
    session = _RecordingSession()
    asyncio.run(
        enqueue_proxy_outbound_audit(
            session,
            user_ctx=_agent_ctx(),
            target_system="dps",
            method="POST",
            path="/api/v2/portrait/calculate",
            request_id="req-t8-1",
            proxy_chain=["openbase-orchestrator", "openbase-dps-proxy"],
        )
    )
    assert len(session.added) == 1
    record = session.added[0]
    identity = record.detail["identity"]
    _assert_identity_keys(identity)
    assert identity["principal"]["subject_type"] == "agent"
    assert identity["proxy_source"] == PROXY_SOURCE_DPS
    assert identity["proxy_chain"] == ["openbase-orchestrator", "openbase-dps-proxy"]
    assert identity["request_id"] == "req-t8-1"
    assert record.action == ACTION_PROXY_OUTBOUND
    assert record.request_id == "req-t8-1"


def test_t8_1_delegation_audit_identity_schema_complete() -> None:
    """委托签发审计 detail 并入 identity 块（六键 + 两层 principal/delegated）."""
    session = _RecordingSession()
    asyncio.run(
        enqueue_delegation_audit(
            session,
            principal_id=7,
            principal_tenant_code="acme",
            principal_tenant_id=77,
            delegated={
                "subject_id": 88,
                "subject_type": "user",
                "tenant_code": "acme",
                "role": "viewer",
            },
            request_id="req-t8-deleg",
        )
    )
    assert len(session.added) == 1
    record = session.added[0]
    assert record.action == DELEGATION_ACTION_ISSUE
    assert record.user_id == 7
    assert record.tenant_id == 77
    assert record.request_id == "req-t8-deleg"
    identity = record.detail["identity"]
    _assert_identity_keys(identity)
    # 两层 + effective（委托时 = delegated 目标）
    assert identity["principal"]["subject_id"] == "7"
    assert identity["delegated"]["subject_id"] == "88"
    assert identity["effective"]["subject_id"] == "88"
    assert identity["effective"]["tenant_code"] == "acme"
    # legacy 顶层字段保留不回退（T8-6）
    assert record.detail["principal"]["id"] == 7
    assert record.detail["delegated"]["id"] == 88
    assert record.detail["tenant_code"] == "acme"
    assert record.detail["request_id"] == "req-t8-deleg"


def test_t8_1_lifecycle_purge_audit_merged_identity_section() -> None:
    """lifecycle/purge 既有 DB 审计 detail 并入 §8.2 identity 块（代码事实核对）."""
    for relative_path in (
        "openbase/modules/identity/lifecycle.py",
        "openbase/modules/identity/purge.py",
    ):
        source = (_ROOT / relative_path).read_text(encoding="utf-8")
        assert "build_identity_section" in source, f"{relative_path} 未并入 identity 块"


def test_t8_1_build_identity_section_six_keys_present() -> None:
    """build_identity_section（最小块）六键完整（lifecycle/purge 复用）. """
    identity = build_identity_section(
        subject_id=3,
        subject_type="user",
        tenant_code="acme",
        role="org_admin",
        auth_method="jwt",
        request_id="req-t8-1",
    )
    _assert_identity_keys(identity)
    assert identity["principal"]["subject_id"] == "3"
    assert identity["effective"]["subject_id"] == "3"
    assert identity["proxy_chain"] is None


# ---------------------------------------------------------------------------
# T8-2：委托出站审计 detail 两层 + X-Agent-Id principal 一致（抽样比对）
# ---------------------------------------------------------------------------


def test_t8_2_delegated_outbound_audit_matches_agent_header() -> None:
    """委托出站头 X-Agent-Id == 审计 principal；X-User-ID == 委托目标（抽样）."""
    ctx = _delegated_agent_ctx(agent_id=7)
    headers = build_outbound_headers(
        _req("req-t8-2"),
        ctx,
        target_system="dps",
        role_map=None,
    )
    assert headers[HEADER_USER_ID] == "88"  # delegated.subject_id
    assert headers[HEADER_AGENT_ID] == "7"  # 执行 agent principal
    assert headers[HEADER_TENANT_ID] == "acme"
    assert headers[HEADER_USER_ROLE] == "viewer"

    session = _RecordingSession()
    asyncio.run(
        enqueue_proxy_outbound_audit(
            session,
            user_ctx=ctx,
            target_system="dps",
            method="POST",
            path="/api/v2/portrait/calculate",
            request_id="req-t8-2",
        )
    )
    record = session.added[0]
    identity = record.detail["identity"]
    assert str(identity["principal"]["subject_id"]) == headers[HEADER_AGENT_ID]
    assert str(identity["delegated"]["subject_id"]) == headers[HEADER_USER_ID]
    assert identity["effective"]["subject_id"] == "88"


# ---------------------------------------------------------------------------
# T8-3：record_proxy_hop 落库（action=proxy.outbound + 入站 request_id 一致）
# ---------------------------------------------------------------------------


def test_t8_3_record_proxy_hop_lands_row_same_request_id() -> None:
    """record_proxy_hop 落库：action=proxy.outbound、request_id 与入站一致."""
    session = _RecordingSession()
    identity = build_identity_section(
        subject_id=7,
        subject_type="agent",
        tenant_code="acme",
        role="viewer",
        auth_method="sk-agent",
        proxy_source=PROXY_SOURCE_RAG,
        request_id="req-t8-3",
        proxy_chain=["openbase-orchestrator", "openbase-rag-proxy"],
    )
    asyncio.run(
        record_proxy_hop(
            session,
            identity=identity,
            system="rag",
            method="POST",
            path="/api/v1/collections",
            request_id="req-t8-3",
        )
    )
    assert len(session.added) == 1
    record = session.added[0]
    assert record.action == ACTION_PROXY_OUTBOUND
    assert record.resource == "rag"
    assert record.request_id == "req-t8-3"
    assert record.detail["identity"]["request_id"] == "req-t8-3"
    assert record.detail["identity"]["proxy_chain"] == [
        "openbase-orchestrator",
        "openbase-rag-proxy",
    ]


def test_t8_3_audit_middleware_persists_outbound_hop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AuditMiddleware 响应后接线：outbound_assembled → 落库 proxy.outbound."""
    import importlib

    monkeypatch.setenv(ENV_AUDIT_DB_PERSIST, "1")
    from openbase.modules.audit import AuditMiddleware

    session_mod = importlib.import_module("openbase.core.db.session")
    recording = _RecordingSession()

    class _SessionCM:
        async def __aenter__(self):
            return recording

        async def __aexit__(self, *exc: object) -> bool:
            return False

    class _FakeFactory:
        def __call__(self) -> _SessionCM:
            return _SessionCM()

    monkeypatch.setattr(session_mod, "get_session_factory", lambda: _FakeFactory())

    middleware = AuditMiddleware(app=object())  # type: ignore[arg-type]
    identity = build_identity_section(
        subject_id=7,
        subject_type="agent",
        tenant_code="acme",
        role="viewer",
        auth_method="sk-agent",
        proxy_source=PROXY_SOURCE_DPS,
        request_id="req-t8-3m",
    )
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/v1/dps-proxy/portraits/calculate",
        "raw_path": b"/api/v1/dps-proxy/portraits/calculate",
        "query_string": b"",
        "root_path": "",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("test", 80),
        "state": {},
    }
    from starlette.requests import Request as StarletteRequest

    request = StarletteRequest(scope)
    request.state.outbound_assembled = True
    request.state.outbound_system = "dps"
    request.state.identity = identity

    async def _run() -> None:
        # TT-056 整改：出站审计改为入队 → 由 writer（drain）批量落库
        await middleware._persist_outbound_proxy_hop(request, "req-t8-3m")
        await audit_persist_queue.drain_once()

    asyncio.run(_run())
    assert len(recording.added) == 1
    record = recording.added[0]
    assert record.action == ACTION_PROXY_OUTBOUND
    assert record.request_id == "req-t8-3m"
    assert record.resource == "dps"
    assert recording.committed


# ---------------------------------------------------------------------------
# T8-4：sk-agent 直连端点审计含 agent_id+source+域+动作
# ---------------------------------------------------------------------------


def test_t8_4_agent_audit_identity_carries_source_domain_action() -> None:
    """agent 出站审计 identity 含 subject_type=agent、proxy_source、tenant_code."""
    session = _RecordingSession()
    asyncio.run(
        enqueue_proxy_outbound_audit(
            session,
            user_ctx=_agent_ctx(agent_id=7),
            target_system="memory",
            method="POST",
            path="/api/v1/memories",
            request_id="req-t8-4",
        )
    )
    record = session.added[0]
    assert record.action == ACTION_PROXY_OUTBOUND
    identity = record.detail["identity"]
    principal = identity["principal"]
    assert principal["subject_type"] == "agent"
    assert principal["auth_method"] == "sk-agent"
    assert principal["tenant_code"] == "acme"
    assert identity["proxy_source"] is not None
    assert identity["request_id"] == "req-t8-4"
    assert record.detail["system"] == "memory"
    assert record.detail["method"] == "POST"


# ---------------------------------------------------------------------------
# T8-5：中间件链路（AuthMiddleware → AuditMiddleware 记录含 identity）
# ---------------------------------------------------------------------------


def test_t8_5_audit_middleware_record_merges_state_identity() -> None:
    """_record 读 request.state.identity（AuthMiddleware 写入）并入 extra.identity."""
    from starlette.requests import Request as StarletteRequest

    from openbase.modules.audit import AuditMiddleware, AuditService

    middleware = AuditMiddleware(app=object())  # type: ignore[arg-type]
    identity = build_identity_section(
        subject_id=42,
        subject_type="user",
        tenant_code="acme",
        role="org_admin",
        auth_method="jwt",
        proxy_source=PROXY_SOURCE_DPS,
        request_id="req-t8-5",
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
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("test", 80),
        "state": {},
    }
    request = StarletteRequest(scope)
    request.state.identity = identity
    request.state.request_id = "req-t8-5"
    before = len(AuditService._records)
    middleware._record(request, 200, 5, "req-t8-5")
    assert len(AuditService._records) == before + 1
    latest = AuditService._records[-1]
    assert latest.extra["identity"]["principal"]["subject_id"] == "42"
    assert latest.extra["identity"]["proxy_source"] == PROXY_SOURCE_DPS
    assert latest.request_id == "req-t8-5"


# ---------------------------------------------------------------------------
# T8-6：既有字段不回退（user_id/tenant_id/request_id 列兼容 + 委托 schema 兼容）
# ---------------------------------------------------------------------------


def test_t8_6_legacy_columns_kept() -> None:
    """代理出站审计 user_id 兼容位 = principal.subject_id；request_id 结构列保留."""
    session = _RecordingSession()
    asyncio.run(
        enqueue_proxy_outbound_audit(
            session,
            user_ctx=_agent_ctx(agent_id=7),
            target_system="dps",
            method="GET",
            path="/api/v2/portrait/list",
            request_id="req-t8-6",
        )
    )
    record = session.added[0]
    assert record.user_id == 7
    assert record.request_id == "req-t8-6"
    assert record.tenant_id is None  # 不进结构列（detail.identity 承载域）


def test_t8_6_delegation_audit_legacy_detail_intact() -> None:
    """委托签发审计 legacy detail.principal/delegated 顶层字段仍存在（U1 兼容）."""
    session = _RecordingSession()
    asyncio.run(
        enqueue_delegation_audit(
            session,
            principal_id=7,
            principal_tenant_code="acme",
            principal_tenant_id=77,
            delegated={
                "subject_id": 88,
                "tenant_code": "acme",
                "role": "viewer",
            },
            request_id="req-t8-6b",
        )
    )
    detail = session.added[0].detail
    assert set(detail["principal"]) == {"id", "tenant_code"}
    assert set(detail["delegated"]) == {"id", "tenant_code", "role"}


# ---------------------------------------------------------------------------
# T8-7：U4 联动边界文档化（§8.1 D-OB13-3 引用）
# ---------------------------------------------------------------------------


def test_t8_7_u4_boundary_documented() -> None:
    """设计草案 §8.1 D-OB13-3 U4 联动边界文档存在."""
    doc_path = _ROOT / "OpenBase-P2-1-统一身份协议头与信任链收口设计草案-v1.0.0.md"
    assert doc_path.exists()
    content = doc_path.read_text(encoding="utf-8")
    for marker in ("D-OB13-1", "D-OB13-2", "D-OB13-3", "audit_logs 不新增列"):
        assert marker in content, f"设计草案缺少 {marker}"
