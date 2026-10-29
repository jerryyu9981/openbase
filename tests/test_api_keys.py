"""测试 v1.4.1 A 类补足（R-367~370）.

覆盖：① ServiceKeyService 签发/校验/吊销（v1.5 起 DB 持久化，替代内存态 ApiKeyStore）；
② require_api_key 认证与 scope 校验；③ get_identity_context 四维身份头解析；
④ 审计上下文注入 tenant_id/user_id。
"""

import asyncio
import tempfile
import uuid
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

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


# ---- 2. ServiceKeyService（DB 持久化）----

_DB_PATH = Path(tempfile.gettempdir()) / (
    f"openbase_test_service_keys_{uuid.uuid4().hex[:8]}.db"
)


def _clear_metadata_schema() -> None:
    """SQLite 无 schema 概念：建表前置空（与 tests/test_tenant_admin.py 同口径）."""
    from openbase.core.models import Base

    Base.metadata.schema = None
    for table in Base.metadata.tables.values():
        table.schema = None


async def _create_schema(engine) -> None:
    from openbase.core.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture(scope="module")
def key_engine():
    """文件型 SQLite 引擎（跨 session 共享，用于验证"重启后仍在"）."""
    _clear_metadata_schema()
    if _DB_PATH.exists():
        _DB_PATH.unlink()
    engine = create_async_engine(f"sqlite+aiosqlite:///{_DB_PATH}")
    asyncio.run(_create_schema(engine))
    yield engine
    asyncio.run(engine.dispose())


@pytest.fixture()
async def session(key_engine):
    factory = async_sessionmaker(key_engine, expire_on_commit=False)
    async with factory() as db_session:
        yield db_session


async def test_service_key_issue_verify_revoke(session) -> None:
    """签发/校验/吊销闭环."""
    from openbase.modules.auth.service_keys import ServiceKeyService

    raw_key, record = await ServiceKeyService.issue(
        session, name="gateway-agent", scope={"system": ["openllm"], "tenants": ["*"]}
    )
    assert raw_key.startswith("ob_k_")
    assert record.key_id

    # 校验通过
    assert await ServiceKeyService.verify(session, raw_key) is not None

    # 吊销后校验失败（E1-1 起吊销返回记录对象；None 表示未命中）
    revoked_record = await ServiceKeyService.revoke_by_raw(session, raw_key)
    assert revoked_record is not None and revoked_record.key_id == record.key_id
    assert await ServiceKeyService.verify(session, raw_key) is None


async def test_service_key_rejects_unknown_key(session) -> None:
    """未知 Key 校验失败."""
    from openbase.modules.auth.service_keys import ServiceKeyService

    assert await ServiceKeyService.verify(session, "ob_k_unknown") is None


async def test_service_key_list_excludes_secret(session) -> None:
    """列表返回签发记录（不含明文 Key / 哈希）."""
    from openbase.modules.auth.service_keys import ServiceKeyService, public_record

    raw_key, _ = await ServiceKeyService.issue(session, name="ops-agent")
    records = [public_record(item) for item in await ServiceKeyService.list_keys(session)]
    target = next(item for item in records if item["name"] == "ops-agent")
    assert "key" not in target and "key_hash" not in target
    assert raw_key not in str(records)  # 明文不外泄


async def test_service_key_lookup_excludes_key_hash(session) -> None:
    """lookup 返回的凭据不得携带 key_hash，且为副本（防调用方改坏记录）."""
    from openbase.modules.auth.service_keys import ServiceKeyService

    raw_key, _ = await ServiceKeyService.issue(
        session, name="svc", scope={"system": ["*"], "tenants": ["*"]}
    )
    record = await ServiceKeyService.lookup(session, raw_key)
    assert record is not None
    assert "key_hash" not in record
    assert record["name"] == "svc"
    assert record["id"]  # 稳定标识保留（按 id 吊销依赖）
    assert "scope" in record

    # 副本语义：改写返回 dict 不得影响存储内记录
    record["name"] = "tampered"
    refreshed = await ServiceKeyService.lookup(session, raw_key)
    assert refreshed is not None and refreshed["name"] == "svc"


async def test_service_key_scope_check(session) -> None:
    """scope 校验：越系统/越租户拒绝."""
    from openbase.modules.auth.service_keys import ServiceKeyService

    raw_key, _ = await ServiceKeyService.issue(
        session, name="llm-only", scope={"system": ["openllm"], "tenants": ["tenant_a"]}
    )

    assert await ServiceKeyService.verify(
        session, raw_key, system="openllm", tenant_id="tenant_a"
    ) is not None
    assert await ServiceKeyService.verify(
        session, raw_key, system="openrag", tenant_id="tenant_a"
    ) is None  # 越系统
    assert await ServiceKeyService.verify(
        session, raw_key, system="openllm", tenant_id="tenant_b"
    ) is None  # 越租户


async def test_service_key_survives_new_session(key_engine) -> None:
    """持久化回归（v1.5）：写入后由新 session（等价进程重启）仍可校验与列出.

    这是本轮修复的根因用例：原 ApiKeyStore 为进程内字典，重启即全部失效。
    """
    from openbase.modules.auth.service_keys import ServiceKeyService

    factory = async_sessionmaker(key_engine, expire_on_commit=False)
    async with factory() as first:
        raw_key, record = await ServiceKeyService.issue(first, name="restart-probe")
        await first.commit()
        key_id = record.key_id

    async with factory() as second:
        credential = await ServiceKeyService.verify(second, raw_key)
        assert credential is not None and credential["id"] == key_id
        listed = [item.key_id for item in await ServiceKeyService.list_keys(second)]
        assert key_id in listed

    async with factory() as third:
        revoked = await ServiceKeyService.revoke_by_id(third, key_id)
        assert revoked is not None and revoked.key_id == key_id
        await third.commit()

    async with factory() as fourth:
        assert await ServiceKeyService.verify(fourth, raw_key) is None


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


async def test_require_api_key_accepts_valid_key(session) -> None:
    """有效 Key 认证通过并返回凭据."""
    from openbase.core.deps.auth import require_api_key
    from openbase.modules.auth.service_keys import ServiceKeyService

    raw_key, _ = await ServiceKeyService.issue(
        session, name="svc", scope={"system": ["*"], "tenants": ["*"]}
    )

    credential = await require_api_key(
        request=_FakeKeyRequest({"X-API-Key": raw_key}), session=session
    )
    assert credential is not None
    assert credential["name"] == "svc"


async def test_require_api_key_credential_excludes_key_hash(session) -> None:
    """require_api_key 凭据仅暴露认证所需字段（无 key_hash），并带认证方式标记."""
    from openbase.core.deps.auth import require_api_key
    from openbase.modules.auth.service_keys import ServiceKeyService

    raw_key, _ = await ServiceKeyService.issue(
        session, name="svc", scope={"system": ["*"], "tenants": ["*"]}
    )
    credential = await require_api_key(
        request=_FakeKeyRequest({"X-API-Key": raw_key}), session=session
    )
    assert "key_hash" not in credential
    assert credential["auth_method"] == "service-key"
    assert credential["name"] == "svc"


async def test_require_api_key_rejects_invalid(session) -> None:
    """无效 Key → AUTH_API_KEY_INVALID."""
    from openbase.core.deps.auth import require_api_key
    from openbase.core.errors import BaseError

    with pytest.raises(BaseError) as exc_info:
        await require_api_key(
            request=_FakeKeyRequest({"X-API-Key": "ob_k_unknown"}), session=session
        )
    assert exc_info.value.code == ErrorCode.AUTH_API_KEY_INVALID


async def test_require_api_key_rejects_scope_mismatch(session) -> None:
    """scope 不匹配 → PERM_API_KEY_SCOPE."""
    from openbase.core.deps.auth import require_api_key
    from openbase.core.errors import BaseError
    from openbase.modules.auth.service_keys import ServiceKeyService

    raw_key, _ = await ServiceKeyService.issue(
        session, name="llm-only", scope={"system": ["openllm"], "tenants": ["*"]}
    )

    # 请求路径指向 openrag（越 scope）
    with pytest.raises(BaseError) as exc_info:
        await require_api_key(
            request=_FakeKeyRequest(
                {"X-API-Key": raw_key}, path="/api/v1/proxy/openrag/search"
            ),
            session=session,
        )
    assert exc_info.value.code == ErrorCode.PERM_API_KEY_SCOPE


async def test_require_api_key_missing_key(session) -> None:
    """缺 Key → AUTH_API_KEY_INVALID."""
    from openbase.core.deps.auth import require_api_key
    from openbase.core.errors import BaseError

    with pytest.raises(BaseError) as exc_info:
        await require_api_key(request=_FakeKeyRequest({}), session=session)
    assert exc_info.value.code == ErrorCode.AUTH_API_KEY_INVALID


async def test_require_api_key_accepts_bearer_key(session) -> None:
    """Authorization: Bearer <key>（非 jwt 前缀）视为服务 Key."""
    from openbase.core.deps.auth import require_api_key
    from openbase.modules.auth.service_keys import ServiceKeyService

    raw_key, _ = await ServiceKeyService.issue(
        session, name="svc-bearer", scope={"system": ["*"], "tenants": ["*"]}
    )

    credential = await require_api_key(
        request=_FakeKeyRequest({"Authorization": f"Bearer {raw_key}"}), session=session
    )
    assert credential["name"] == "svc-bearer"


async def test_require_api_key_x_api_key_header(session) -> None:
    """X-API-Key 头认证通过（非 proxy 路径时 system=None 不校验 scope）."""
    from openbase.core.deps.auth import require_api_key
    from openbase.modules.auth.service_keys import ServiceKeyService

    raw_key, _ = await ServiceKeyService.issue(
        session, name="svc", scope={"system": ["openllm"], "tenants": ["*"]}
    )

    # 非 proxy 路径（system=None，scope 校验跳过 system）
    credential = await require_api_key(
        request=_FakeKeyRequest({"X-API-Key": raw_key}, path="/api/v1/items"),
        session=session,
    )
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
