"""B4 安全收紧 TDD 用例（吊销强制 + 主体验证 fail-closed + 显式白名单）.

人工裁定口径（2026-10-08）：**选项 A —— fail-closed + 显式白名单**。

覆盖场景（对齐交付要求 4）：
- ① DB 不可达 + 未命中白名单 → 拒绝（503 ``SYS_SOURCE_UNAVAILABLE``）；
- ② DB 不可达 + 命中显式白名单 → 放行（None）且留痕（结构化日志 + 审计 ContextVar）；
- ③ DB 正常 → 行为与收紧前一致（回归：active 放行 / suspended 401 / 行缺失无墓碑放行 /
     带委托仍 403）；
- ④ 生产环境 + ``enforce_token_version=False`` → Settings 构造（启动校验）被拒；
- ⑤ 生产环境 + ``enforce_token_version=True`` → 通过；
- ⑥ 吊销（claim tvn 落后）→ 旧 token 被拒（``AUTH_TOKEN_STALE``，enforce 生效）；
- ⑦ 环境门控（2026-10-09 修复）：生产默认 reject / 非生产默认 allow（必留痕）/
     显式 policy 覆盖 / 生产误配 allow 启动 fail-fast。deny 路径用例一律**显式钉死**
     ``policy=reject`` 或生产环境，确保安全语义仍被测到。
"""

from __future__ import annotations

import asyncio
import importlib
import logging
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import ValidationError

from openbase.core.errors import BaseError, ErrorCode
from openbase.modules.identity import verification as verification_module
from openbase.settings import Settings

_SECRET = "b4-test-secret-0123456789abcdef0123456789abcdef"
_DELEGATION_BLOCK = {
    "subject_id": "88",
    "subject_type": "user",
    "tenant_code": "acme",
    "role": "viewer",
}


# ---------------------------------------------------------------------------
# 会话/主体桩（与 test_verdict_k03 同构，隔离 DB）
# ---------------------------------------------------------------------------


class _GetResultStub:
    """session.execute(...).first() 桩（无墓碑命中 = 返回 None）."""

    def __init__(self, row: Any = None) -> None:
        self._row = row

    def first(self) -> Any:
        return self._row


class _HealthySession:
    """DB 可用：get 返回主体行（或 None 模拟行缺失）."""

    def __init__(self, row: Any = None) -> None:
        self._row = row

    async def get(self, _model: Any, _subject_id: int) -> Any:
        return self._row

    async def execute(self, _stmt: Any) -> _GetResultStub:
        return _GetResultStub(None)

    async def rollback(self) -> None:
        return None


class _DownSession:
    """DB 不可达：get 抛异常（无法证明主体状态）."""

    async def get(self, _model: Any, _subject_id: int) -> Any:
        raise RuntimeError("database connection refused")

    async def rollback(self) -> None:
        return None


def _user_row(status_state: str = "active", token_version: int = 0) -> SimpleNamespace:
    return SimpleNamespace(
        is_deleted=False,
        subject_type="user",
        status_state=status_state,
        token_version=token_version,
        username="alice",
        tenant_id=None,
        tenant_code="acme",
    )


def _apply_settings(monkeypatch: pytest.MonkeyPatch, **overrides: Any) -> Settings:
    """构造并装载 settings 单例（monkeypatch 自动复原）."""
    settings = Settings(jwt_secret=_SECRET, **overrides)
    module = importlib.import_module("openbase.settings")
    monkeypatch.setattr(module, "_settings", settings)
    return settings


@pytest.fixture(autouse=True)
def _reset_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    """每用例重置进程级共享 WARN 指标（隔离）."""
    monkeypatch.setattr(
        verification_module,
        "_VERDICT_METRICS",
        {
            "db_degraded": 0,
            "db_degraded_allowlisted": 0,
            "db_degraded_policy_allow": 0,
            "db_degraded_denied": 0,
            "row_missing": 0,
            "delegation_denied_db": 0,
            "delegation_denied_row_missing": 0,
        },
    )


# ---------------------------------------------------------------------------
# ① DB 不可达 + 未命中白名单 → 拒绝
# ---------------------------------------------------------------------------


def test_b4_1_db_down_without_allowlist_denied(monkeypatch: pytest.MonkeyPatch) -> None:
    """DB 不可达且未命中白名单 + 显式 policy=reject → 503 SYS_SOURCE_UNAVAILABLE.

    环境门控（2026-10-09）：非生产默认「兼容放行」，故 deny 路径须**显式钉死**
    ``principal_db_degraded_policy=reject``（生产默认亦为 reject）。
    """
    _apply_settings(monkeypatch, principal_db_degraded_policy="reject")
    with pytest.raises(BaseError) as exc_info:
        asyncio.run(
            verification_module.verify_principal(_DownSession(), {"sub": "42", "tvn": 0})
        )
    assert exc_info.value.code == ErrorCode.SYS_SOURCE_UNAVAILABLE
    assert exc_info.value.status_code == 503
    metrics = verification_module.get_verdict_metrics()
    assert metrics["db_degraded_denied"] == 1
    assert metrics["db_degraded_allowlisted"] == 0
    assert metrics["db_degraded_policy_allow"] == 0


# ---------------------------------------------------------------------------
# ② DB 不可达 + 命中白名单 → 放行 + 留痕
# ---------------------------------------------------------------------------


def test_b4_2_db_down_allowlisted_passthrough_with_trace(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """DB 不可达但命中显式白名单 → 放行（None）且留痕（日志 + 审计 ContextVar）.

    显式钉死 ``policy=reject``：证明**显式白名单优先于 reject 裁定**（生产应急通道）。
    """
    _apply_settings(
        monkeypatch,
        principal_db_degraded_policy="reject",
        principal_db_degraded_allowlist="42",
    )

    async def _run() -> tuple[Any, dict[str, Any] | None]:
        # 留痕经 ContextVar 承载：须在同一任务内消费（生产请求即中间件/依赖同任务）
        result = await verification_module.verify_principal(
            _DownSession(), {"sub": "42", "tvn": 0}, request_id="req-b4-2"
        )
        return result, verification_module.consume_degraded_allowlist_trace()

    with caplog.at_level(logging.WARNING, logger="openbase.identity.verification"):
        result, trace = asyncio.run(_run())
    assert result is None
    metrics = verification_module.get_verdict_metrics()
    assert metrics["db_degraded_allowlisted"] == 1
    assert metrics["db_degraded_denied"] == 0

    records = [
        record
        for record in caplog.records
        if "allowlisted pass-through" in record.getMessage()
    ]
    assert records, "白名单放行必须产生结构化日志留痕"
    record = records[0]
    assert record.subject == "42"
    assert record.reason == "db_unavailable_allowlisted"
    assert record.request_id == "req-b4-2"

    assert trace == {
        "subject": "42",
        "reason": "db_unavailable_allowlisted",
        "request_id": "req-b4-2",
    }
    # 消费即清除（避免跨请求串读）
    assert verification_module.consume_degraded_allowlist_trace() is None


def test_b4_2b_malformed_allowlist_entry_not_matched(monkeypatch: pytest.MonkeyPatch) -> None:
    """非法白名单项（通配/前缀/非数字）不作为命中 → 显式 policy=reject 下拒绝."""
    _apply_settings(
        monkeypatch,
        principal_db_degraded_policy="reject",
        principal_db_degraded_allowlist="42*,user:42,abc",
    )
    with pytest.raises(BaseError) as exc_info:
        asyncio.run(
            verification_module.verify_principal(_DownSession(), {"sub": "42", "tvn": 0})
        )
    assert exc_info.value.code == ErrorCode.SYS_SOURCE_UNAVAILABLE


def test_b4_2c_allowlist_parsing_only_decimal_ids() -> None:
    """白名单解析：仅保留十进制主体 id；空/非法项被丢弃（fail-closed）."""
    assert Settings(
        principal_db_degraded_allowlist=" 1 , 2 , 3 "
    ).principal_db_degraded_allowlist_set == frozenset({"1", "2", "3"})
    assert Settings(
        principal_db_degraded_allowlist="1,*,user,42x"
    ).principal_db_degraded_allowlist_set == frozenset({"1"})
    assert Settings(principal_db_degraded_allowlist="").principal_db_degraded_allowlist_set == frozenset()


# ---------------------------------------------------------------------------
# ③ DB 正常 → 行为零变化（回归）
# ---------------------------------------------------------------------------


def test_b4_3_db_healthy_active_passthrough(monkeypatch: pytest.MonkeyPatch) -> None:
    """DB 正常 + active → 返回主体快照（与收紧前一致）."""
    _apply_settings(monkeypatch)
    snapshot = asyncio.run(
        verification_module.verify_principal(
            _HealthySession(_user_row("active", 0)), {"sub": "42", "tvn": 0}
        )
    )
    assert snapshot is not None
    assert snapshot["status_state"] == "active"
    assert verification_module.get_verdict_metrics()["db_degraded"] == 0


def test_b4_3_db_healthy_suspended_401(monkeypatch: pytest.MonkeyPatch) -> None:
    """DB 正常 + suspended → 401 AUTH_PRINCIPAL_DISABLED（状态门禁不变）."""
    _apply_settings(monkeypatch)
    with pytest.raises(BaseError) as exc_info:
        asyncio.run(
            verification_module.verify_principal(_HealthySession(_user_row("suspended")), {"sub": "42"})
        )
    assert exc_info.value.code == ErrorCode.AUTH_PRINCIPAL_DISABLED
    assert exc_info.value.status_code == 401


def test_b4_3_db_healthy_row_missing_still_failopen(monkeypatch: pytest.MonkeyPatch) -> None:
    """行缺失 + 无墓碑 + 无委托 → 保持既有 fail-open（DB 正常，不在本次收紧范围）."""
    _apply_settings(monkeypatch)
    result = asyncio.run(
        verification_module.verify_principal(_HealthySession(None), {"sub": "42", "tvn": 0})
    )
    assert result is None
    assert verification_module.get_verdict_metrics()["db_degraded"] == 0
    assert verification_module.get_verdict_metrics()["row_missing"] == 1


def test_b4_3_db_down_with_delegation_still_403(monkeypatch: pytest.MonkeyPatch) -> None:
    """DB 不可达 + 带委托 → 仍 fail-closed 403（委托分支优先级最高，行为不变）."""
    _apply_settings(monkeypatch, principal_db_degraded_allowlist="42")
    with pytest.raises(BaseError) as exc_info:
        asyncio.run(
            verification_module.verify_principal(
                _DownSession(), {"sub": "42", "on_behalf_of": _DELEGATION_BLOCK}
            )
        )
    assert exc_info.value.code == ErrorCode.PERM_DELEGATION_VERIFY_UNAVAILABLE
    assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# ④⑤ 生产门禁：吊销强制
# ---------------------------------------------------------------------------


def test_b4_4_production_requires_token_version_enforcement() -> None:
    """生产环境 + enforce_token_version=False → Settings 构造（启动）被拒."""
    strong = "b4-" + "x" * 40
    with pytest.raises(ValidationError) as exc_info:
        Settings(env="production", jwt_secret=strong, enforce_token_version=False)
    assert "ENFORCE_TOKEN_VERSION" in str(exc_info.value)


def test_b4_5_production_with_enforcement_ok() -> None:
    """生产环境 + enforce_token_version=True → 通过（启动放行）."""
    strong = "b4-" + "x" * 40
    settings = Settings(env="production", jwt_secret=strong, enforce_token_version=True)
    assert settings.env == "production"
    assert settings.enforce_token_version is True


# ---------------------------------------------------------------------------
# ⑥ 吊销强制：tvn 落后 → 旧 token 被拒
# ---------------------------------------------------------------------------


def test_b4_6_stale_token_rejected_when_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    """enforce 开启：claim tvn=1 而服务端 token_version=2 → 401 AUTH_TOKEN_STALE."""
    _apply_settings(monkeypatch, enforce_token_version=True)
    with pytest.raises(BaseError) as exc_info:
        asyncio.run(
            verification_module.verify_principal(
                _HealthySession(_user_row("active", token_version=2)), {"sub": "42", "tvn": 1}
            )
        )
    assert exc_info.value.code == ErrorCode.AUTH_TOKEN_STALE
    assert exc_info.value.status_code == 401


def test_b4_6b_current_token_accepted_when_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    """enforce 开启：claim tvn 与主体版本一致 → 放行（不误杀当前令牌）."""
    _apply_settings(monkeypatch, enforce_token_version=True)
    snapshot = asyncio.run(
        verification_module.verify_principal(
            _HealthySession(_user_row("active", token_version=2)), {"sub": "42", "tvn": 2}
        )
    )
    assert snapshot is not None


# ---------------------------------------------------------------------------
# ⑦ 环境门控（2026-10-09 修复）：降级策略环境相关 + 显式 policy 覆盖
# ---------------------------------------------------------------------------


def test_b4_7_development_default_allows_with_trace(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """非生产（development）默认：DB 不可达 + 未命中白名单 → 兼容放行 + WARN + 留痕.

    安全语义不变项：**不得静默** —— 结构化 WARN 日志（reason=db_unavailable_env_allow）
    + 审计 ContextVar 留痕 + 指标 ``db_degraded_policy_allow`` 计数必须齐全。
    """
    settings = _apply_settings(monkeypatch, env="development")
    assert settings.env != "production"

    async def _run() -> tuple[Any, dict[str, Any] | None]:
        result = await verification_module.verify_principal(
            _DownSession(), {"sub": "42", "tvn": 0}, request_id="req-b4-7"
        )
        return result, verification_module.consume_degraded_allowlist_trace()

    with caplog.at_level(logging.WARNING, logger="openbase.identity.verification"):
        result, trace = asyncio.run(_run())
    assert result is None
    metrics = verification_module.get_verdict_metrics()
    assert metrics["db_degraded"] == 1
    assert metrics["db_degraded_policy_allow"] == 1
    assert metrics["db_degraded_denied"] == 0

    records = [
        record
        for record in caplog.records
        if "environment/policy allow pass-through" in record.getMessage()
    ]
    assert records, "非生产兼容放行必须产生结构化 WARN 留痕（不得静默）"
    record = records[0]
    assert record.subject == "42"
    assert record.reason == "db_unavailable_env_allow"
    assert record.decision == "allow"
    assert record.policy_source == "env_nonproduction"

    assert trace == {
        "subject": "42",
        "reason": "db_unavailable_env_allow",
        "request_id": "req-b4-7",
    }


def test_b4_8_explicit_policy_allow_non_production(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """非生产 + 显式 policy=allow → 放行 + 留痕（reason=db_unavailable_policy_allow）."""
    _apply_settings(monkeypatch, principal_db_degraded_policy="allow")

    async def _run() -> tuple[Any, dict[str, Any] | None]:
        result = await verification_module.verify_principal(
            _DownSession(), {"sub": "42"}, request_id="req-b4-8"
        )
        return result, verification_module.consume_degraded_allowlist_trace()

    with caplog.at_level(logging.WARNING, logger="openbase.identity.verification"):
        result, trace = asyncio.run(_run())
    assert result is None
    assert verification_module.get_verdict_metrics()["db_degraded_policy_allow"] == 1
    assert trace == {
        "subject": "42",
        "reason": "db_unavailable_policy_allow",
        "request_id": "req-b4-8",
    }


def test_b4_9_production_default_rejects(monkeypatch: pytest.MonkeyPatch) -> None:
    """生产（env=production，policy 默认空）→ 按环境推导为 reject：503 拒绝."""
    _apply_settings(monkeypatch, env="production", enforce_token_version=True)
    with pytest.raises(BaseError) as exc_info:
        asyncio.run(
            verification_module.verify_principal(_DownSession(), {"sub": "42", "tvn": 0})
        )
    assert exc_info.value.code == ErrorCode.SYS_SOURCE_UNAVAILABLE
    assert exc_info.value.status_code == 503


def test_b4_10_production_allowlist_still_overrides_reject(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """生产 + 显式白名单 → 仍放行（应急通道，优先于生产 reject）."""
    _apply_settings(
        monkeypatch,
        env="production",
        enforce_token_version=True,
        principal_db_degraded_allowlist="42",
    )
    result = asyncio.run(
        verification_module.verify_principal(_DownSession(), {"sub": "42", "tvn": 0})
    )
    assert result is None


def test_b4_11_production_policy_allow_rejected_at_startup() -> None:
    """生产 + policy=allow → Settings 构造（启动）fail-fast 拒绝（防生产误配回退 fail-open）."""
    strong = "b4-" + "x" * 40
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            env="production",
            jwt_secret=strong,
            enforce_token_version=True,
            principal_db_degraded_policy="allow",
        )
    assert "PRINCIPAL_DB_DEGRADED_POLICY" in str(exc_info.value)


def test_b4_12_invalid_policy_value_rejected_at_startup() -> None:
    """policy 取值非法（非 reject/allow/空）→ 启动 fail-fast 拒绝."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(principal_db_degraded_policy="maybe")
    assert "PRINCIPAL_DB_DEGRADED_POLICY" in str(exc_info.value)
