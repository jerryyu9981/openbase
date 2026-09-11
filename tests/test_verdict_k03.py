"""P2-1 T2 RED 断言：K03 信任链裁定 D-V1~D-V7 编码（§5.1/§5.2）.

对齐草案 §10 T2：
- T2-1  V-1：DB 不可达 + 无委托 → 放行 + WARN 计数（db_degraded）；DB 恢复后强校验
- T2-2  V-2：行缺失无墓碑 + 无委托 → 放行；行缺失 + on_behalf_of → 403
- T2-3  V-3：委托请求 + DB 不可达 → 403 PERM_DELEGATION_VERIFY_UNAVAILABLE
- T2-4  V-4：Redis 停 → verify 直读 DB 判定（suspend 主体仍 401）
- T2-6  D-V6：ob_k_ 匿名写 → 403 PERM_SERVICE_KEY_WRITE_DENIED；白名单放行 + 逐条审计
- T2-7  D-V7：sk-agent + DB 不可达 → 401（fail-closed）
- T2-9  WARN 指标可查询（get_verdict_metrics）
"""
from __future__ import annotations

import asyncio
import importlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from openbase.core.errors import BaseError, ErrorCode
from openbase.modules.identity import agent_keys as agent_keys_module
from openbase.modules.identity import verification as verification_module
from openbase.modules.proxy import (
    _is_service_key_identity,
    _k03_bypass_matches,
    _record_k03_bypass_audit,
)
from openbase.settings import Settings

_SECRET = "p21-test-secret-0123456789abcdef0123456789abcdef"


# ---------------------------------------------------------------------------
# 会话桩
# ---------------------------------------------------------------------------


def _user_row(status_state: str = "active") -> SimpleNamespace:
    return SimpleNamespace(
        is_deleted=False,
        subject_type="user",
        status_state=status_state,
        token_version=0,
        username="alice",
        tenant_id=None,
        tenant_code="acme",
    )


class _GetResultStub:
    """session.execute(...).first() 桩（无墓碑命中 = 返回 None）."""

    def __init__(self, row: Any = None) -> None:
        self._row = row

    def first(self) -> Any:
        return self._row


class _HealthyGetSession:
    """DB 可用：get 返回主体行."""

    def __init__(self, row: Any = None) -> None:
        self._row = row

    async def get(self, _model: Any, _subject_id: int) -> Any:
        return self._row

    async def execute(self, _stmt: Any) -> _GetResultStub:
        return _GetResultStub(None)

    async def rollback(self) -> None:
        return None


class _DownGetSession:
    """DB 不可达：get 抛异常."""

    async def get(self, _model: Any, _subject_id: int) -> Any:
        raise RuntimeError("database connection refused")

    async def rollback(self) -> None:
        return None


class _DownExecuteSession:
    """DB 不可达：execute 抛异常（agent 密钥校验路径）."""

    async def execute(self, _stmt: Any) -> Any:
        raise RuntimeError("database connection refused")

    async def rollback(self) -> None:
        return None


class _RowMissingSession:
    """DB 可用但主体行缺失（get → None；无 purge 墓碑）."""

    async def get(self, _model: Any, _subject_id: int) -> Any:
        return None

    async def execute(self, _stmt: Any) -> _GetResultStub:
        return _GetResultStub(None)

    async def rollback(self) -> None:
        return None


def _payload(subject: str = "42", delegated: bool = False) -> dict:
    payload: dict[str, Any] = {"sub": subject}
    if delegated:
        payload["on_behalf_of"] = {
            "subject_id": "88",
            "subject_type": "user",
            "tenant_code": "acme",
            "role": "viewer",
        }
    return payload


@pytest.fixture(autouse=True)
def _reset_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    """每用例重置 WARN 指标计数（进程级共享，须隔离）."""
    monkeypatch.setattr(
        verification_module,
        "_VERDICT_METRICS",
        {
            "db_degraded": 0,
            "row_missing": 0,
            "delegation_denied_db": 0,
            "delegation_denied_row_missing": 0,
        },
    )


def _apply_settings(monkeypatch: pytest.MonkeyPatch, **overrides: Any) -> Settings:
    settings = Settings(jwt_secret=_SECRET, **overrides)
    module = importlib.import_module("openbase.settings")
    monkeypatch.setattr(module, "_settings", settings)
    return settings


# ---------------------------------------------------------------------------
# T2-1（V-1）：DB 不可达 + 无委托 → fail-open + WARN 计数
# ---------------------------------------------------------------------------


def test_t2_1_db_down_without_delegation_fail_open() -> None:
    """DB 读不可达 + 无 on_behalf_of → 放行（None）+ db_degraded 计数 +1."""
    result = asyncio.run(
        verification_module.verify_principal(_DownGetSession(), _payload())
    )
    assert result is None
    metrics = verification_module.get_verdict_metrics()
    assert metrics["db_degraded"] == 1


def test_t2_1_db_recovered_enforces_again() -> None:
    """DB 恢复 → 强校验即时恢复（suspend 主体仍 401）."""
    session = _HealthyGetSession(_user_row(status_state="suspended"))
    with pytest.raises(BaseError) as exc_info:
        asyncio.run(verification_module.verify_principal(session, _payload()))
    assert exc_info.value.code == ErrorCode.AUTH_PRINCIPAL_DISABLED
    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# T2-2（V-2）：行缺失裁定
# ---------------------------------------------------------------------------


def test_t2_2_row_missing_without_delegation_fail_open() -> None:
    """行缺失 + 无墓碑 + 无委托 → WARN 放行（row_missing 计数）."""
    result = asyncio.run(
        verification_module.verify_principal(_RowMissingSession(), _payload())
    )
    assert result is None
    metrics = verification_module.get_verdict_metrics()
    assert metrics["row_missing"] == 1


def test_t2_2_row_missing_with_delegation_rejected() -> None:
    """行缺失 + 携带 on_behalf_of → 403 PERM_DELEGATION_VERIFY_UNAVAILABLE."""
    with pytest.raises(BaseError) as exc_info:
        asyncio.run(
            verification_module.verify_principal(
                _RowMissingSession(), _payload(delegated=True)
            )
        )
    assert exc_info.value.code == ErrorCode.PERM_DELEGATION_VERIFY_UNAVAILABLE
    assert exc_info.value.status_code == 403
    metrics = verification_module.get_verdict_metrics()
    assert metrics["delegation_denied_row_missing"] == 1


# ---------------------------------------------------------------------------
# T2-3（V-3）：委托 + DB 不可达 fail-closed
# ---------------------------------------------------------------------------


def test_t2_3_delegation_with_db_down_403() -> None:
    """委托请求 + DB 不可达 → 403（fail-closed）；普通请求不受影响."""
    with pytest.raises(BaseError) as exc_info:
        asyncio.run(
            verification_module.verify_principal(
                _DownGetSession(), _payload(delegated=True)
            )
        )
    assert exc_info.value.code == ErrorCode.PERM_DELEGATION_VERIFY_UNAVAILABLE
    assert exc_info.value.status_code == 403
    metrics = verification_module.get_verdict_metrics()
    assert metrics["delegation_denied_db"] == 1
    # 对照：同 DB 故障下普通请求（无委托）仍放行
    result = asyncio.run(
        verification_module.verify_principal(_DownGetSession(), _payload())
    )
    assert result is None


# ---------------------------------------------------------------------------
# T2-4（V-4）：Redis 不可达直读 DB（缓存非信任源）
# ---------------------------------------------------------------------------


def test_t2_4_redis_down_verify_still_from_db(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Redis 停（cache_get 抛错=未命中）→ verify 直读 DB：suspend 主体仍 401."""
    from openbase.core.cache import redis_client as cache_module

    def _broken_get(*_args: Any, **_kwargs: Any) -> None:
        raise ConnectionError("redis down")

    monkeypatch.setattr(cache_module, "cache_get", _broken_get)
    session = _HealthyGetSession(_user_row(status_state="suspended"))
    with pytest.raises(BaseError) as exc_info:
        asyncio.run(verification_module.verify_principal(session, _payload()))
    assert exc_info.value.code == ErrorCode.AUTH_PRINCIPAL_DISABLED


# ---------------------------------------------------------------------------
# T2-7（D-V7）：sk-agent + DB 不可达 fail-closed（401）
# ---------------------------------------------------------------------------


def test_t2_7_sk_agent_db_down_fail_closed() -> None:
    """agent 密钥校验 DB 不可达 → 401（fail-closed，不降级放行）."""
    with pytest.raises(BaseError) as exc_info:
        asyncio.run(
            agent_keys_module.resolve_agent_principal(
                _DownExecuteSession(), "sk-agent-anything"
            )
        )
    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# T2-6（D-V6）：ob_k_ 匿名业务写 fail-closed + k03_bypass_whitelist
# ---------------------------------------------------------------------------


def _proxy_app(monkeypatch: pytest.MonkeyPatch, **overrides: Any) -> TestClient:
    from openbase import init_app
    from openbase.modules.auth import UserService

    settings = _apply_settings(monkeypatch, **overrides)
    for module_name in ("auth", "proxy", "audit", "tenant", "config"):
        settings.enable_module(module_name)
    UserService.seed_memory_user("admin", "admin123")
    app = init_app(settings)
    return TestClient(app)


def _create_service_key(client: TestClient, token: str) -> str:
    resp = client.post(
        "/api/v1/auth/api-keys",
        json={"name": "svc-dv6", "scope": {"system": ["*"], "tenants": ["*"]}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["key"]


def _admin_token(client: TestClient) -> str:
    resp = client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "admin123"}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def test_t2_6_unregistered_service_key_write_403(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """未登记 ob_k_ 写路径 → 403 PERM_SERVICE_KEY_WRITE_DENIED（D-V6）."""
    client = _proxy_app(monkeypatch)
    token = _admin_token(client)
    key = _create_service_key(client, token)
    resp = client.post(
        "/api/v1/proxy/openllm/chat",
        json={"messages": []},
        headers={"X-API-Key": key},
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "PERM_SERVICE_KEY_WRITE_DENIED"


def test_t2_6_whitelisted_write_allowed_with_bypass_audit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """白名单（k03_bypass_whitelist）内匿名写放行（非 403），逐条审计由记录函数覆盖."""
    whitelist = json.dumps(
        [
            {
                "id": "wb-001",
                "system": "openllm",
                "method": "POST",
                "path_pattern": "/chat",
                "reason": "transition",
                "owner": "p2-1",
            }
        ]
    )
    client = _proxy_app(monkeypatch, k03_bypass_whitelist=whitelist)
    # 隔离审计 DB 写入（本用例只验证白名单放行语义；审计落库由 test_t2_10 覆盖）
    class _NoopSession:
        def add(self, _record: Any) -> None:
            return None

        async def commit(self) -> None:
            return None

        async def rollback(self) -> None:
            return None

    class _SessionFactory:
        def __call__(self) -> _SessionFactory:
            return self

        async def __aenter__(self) -> _NoopSession:
            return _NoopSession()

        async def __aexit__(self, *_args: Any) -> bool:
            return False

    monkeypatch.setattr(
        "openbase.core.db.session.get_session_factory", lambda: _SessionFactory()
    )
    token = _admin_token(client)
    key = _create_service_key(client, token)
    resp = client.post(
        "/api/v1/proxy/openllm/chat",
        json={"messages": []},
        headers={"X-API-Key": key},
    )
    # 白名单内 → 不被 403（上游不可达时按既有 SYS_502 语义；DB 审计失败降级 WARN）
    assert resp.status_code != 403, resp.text
    # 真实环境上游可达时响应为透明包装体，可能不含 code 字段；
    # 仅在含 code 时校验其非 PERM_SERVICE_KEY_WRITE_DENIED（非 403 语义已由上一断言覆盖）
    body = resp.json()
    if isinstance(body, dict) and "code" in body:
        assert body["code"] != "PERM_SERVICE_KEY_WRITE_DENIED"


def test_k03_bypass_matcher_unit() -> None:
    """白名单匹配器：system+method+path_pattern 命中判定."""
    entry = {"system": "openllm", "method": "POST", "path_pattern": "/chat"}
    assert _k03_bypass_matches(entry, system="openllm", method="POST", path="/chat/stream")
    assert _k03_bypass_matches(entry, system="openllm", method="POST", path="/openllm/v1/chat")
    assert not _k03_bypass_matches(entry, system="openllm", method="GET", path="/chat")
    assert not _k03_bypass_matches(entry, system="openrag", method="POST", path="/chat")


def test_t2_10_bypass_write_audit_record() -> None:
    """白名单放行审计：action=proxy.bypass_write + detail 含 id/reason 写入 AuditLog."""
    from openbase.core.models import AuditLog

    added: list[AuditLog] = []

    class _RecordingSession:
        async def commit(self) -> None:
            return None

        async def rollback(self) -> None:
            return None

        def add(self, record: AuditLog) -> None:
            added.append(record)

    async def _run() -> None:
        await _record_k03_bypass_audit(
            _RecordingSession(),
            entry={"id": "wb-001", "reason": "transition", "owner": "p2-1"},
            system="openllm",
            method="POST",
            path="/chat",
            request_id="req-audit-0001",
        )

    asyncio.run(_run())
    assert len(added) == 1
    record = added[0]
    assert record.action == "proxy.bypass_write"
    assert record.detail["id"] == "wb-001"
    assert record.detail["reason"] == "transition"
    assert record.request_id == "req-audit-0001"


def test_t2_9_verdict_metrics_queryable() -> None:
    """WARN 指标可查询：get_verdict_metrics 返回四个计数键（verify-env 对账项）."""
    metrics = verification_module.get_verdict_metrics()
    for metric_key in (
        "db_degraded",
        "row_missing",
        "delegation_denied_db",
        "delegation_denied_row_missing",
    ):
        assert metric_key in metrics


def test_t2_8_bypass_scan_zero_high() -> None:
    """旁路扫描报告 0 高危未登记项（D-V6 fail-closed 保护下恒空）."""
    root = Path(__file__).resolve().parent.parent
    module_path = root / "scripts" / "bypass_scan.py"
    spec = importlib.util.spec_from_file_location("openbase_bypass_scan", module_path)
    assert spec is not None and spec.loader is not None
    scan_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scan_module)

    empty_report = scan_module.scan_service_key_write_paths([])
    assert empty_report["high"] == []
    assert empty_report["whitelist_size"] == 0
    assert empty_report["write_routes"][0]["guard"] == "d-v6-fail-closed"

    whitelisted_report = scan_module.scan_service_key_write_paths(
        [{"id": "wb-001", "system": "openllm", "method": "POST"}]
    )
    assert whitelisted_report["high"] == []
    assert whitelisted_report["whitelist_size"] == 1


def test_service_key_identity_detector() -> None:
    """ob_k_ 服务 Key 凭据 vs JWT 用户上下文判定（通用 /proxy D-V6 前置）."""
    service_credential = {"name": "svc", "scope": {"system": ["*"]}}
    assert _is_service_key_identity(service_credential) is True
    user_context = {"id": 42, "username": "alice", "role": "admin"}
    assert _is_service_key_identity(user_context) is False
