"""服务 Key 存储边角补测（覆盖率治理 v1.4.0）.

覆盖 ``service_keys.py`` 中难以经 HTTP 触发的分支：默认有效期/轮换宽限配置
异常回落、到期提醒去重的 Redis 降级与容量兜底、轮换非 active 拒绝、
使用痕迹写入失败降级、已吊销幂等。
"""

import asyncio
import datetime as dt
import importlib
from types import SimpleNamespace

import pytest

import openbase.modules.auth.service_keys as service_keys
from openbase.core.cache import redis_client
from openbase.core.errors import BaseError, ErrorCode
from openbase.modules.auth.service_keys import (
    ServiceKeyService,
    _claim_expiring_notification,
    _default_expires_at,
    _rotate_grace_hours,
)

settings_module = importlib.import_module("openbase.settings")


def _settings(**overrides):
    defaults = {
        "service_key_ttl_days": 0,
        "service_key_rotate_grace_hours": 0,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_default_expires_at_and_rotate_grace(monkeypatch: pytest.MonkeyPatch) -> None:
    """配置非法（非整数）→ 回落 0；TTL<=0 不过期；宽限期负数按 0."""
    monkeypatch.setattr(
        settings_module,
        "get_settings",
        lambda: _settings(service_key_ttl_days="bad", service_key_rotate_grace_hours="bad"),
    )
    assert _default_expires_at() is None
    assert _rotate_grace_hours() == 0

    monkeypatch.setattr(
        settings_module,
        "get_settings",
        lambda: _settings(service_key_ttl_days=0, service_key_rotate_grace_hours=-5),
    )
    assert _default_expires_at() is None
    assert _rotate_grace_hours() == 0

    monkeypatch.setattr(
        settings_module,
        "get_settings",
        lambda: _settings(service_key_ttl_days=2, service_key_rotate_grace_hours=12),
    )
    expires = _default_expires_at()
    assert expires is not None
    assert expires > dt.datetime.now(dt.timezone.utc)
    assert _rotate_grace_hours() == 12


def test_claim_expiring_notification_redis_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Redis 可用时以 SET NX 结果为准（首次 True，重复 False）."""

    class _Redis:
        def __init__(self) -> None:
            self.keys: set[str] = set()

        def set(self, key: str, value: str, nx: bool = False, ex: int | None = None) -> bool:
            if key in self.keys:
                return False
            self.keys.add(key)
            return True

    client = _Redis()
    monkeypatch.setattr(redis_client, "get_client", lambda: client)
    assert _claim_expiring_notification("k1", "2026-11-14") is True
    assert _claim_expiring_notification("k1", "2026-11-14") is False


def test_claim_expiring_notification_local_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Redis 异常 → 进程内去重；容量上限触发清空后仍可抢占."""
    monkeypatch.setattr(service_keys, "_expiring_claimed_local", set())

    class _BrokenRedis:
        def set(self, *args, **kwargs) -> bool:
            raise RuntimeError("redis down")

    monkeypatch.setattr(redis_client, "get_client", lambda: _BrokenRedis())
    assert _claim_expiring_notification("k1", "2026-11-14") is True
    assert _claim_expiring_notification("k1", "2026-11-14") is False

    monkeypatch.setattr(
        service_keys,
        "_expiring_claimed_local",
        {("old", str(index)) for index in range(20000)},
    )
    assert _claim_expiring_notification("new", "2026-11-15") is True
    assert len(service_keys._expiring_claimed_local) == 1


def test_rotate_rejects_inactive_key() -> None:
    """非 active Key 轮换 → BIZ_CONFLICT（不签发新 Key）."""
    record = SimpleNamespace(status=service_keys.SERVICE_KEY_STATUS_REVOKED)

    class _Result:
        def scalar_one_or_none(self):
            return record

    class _Session:
        async def execute(self, *args, **kwargs):
            return _Result()

    with pytest.raises(BaseError) as exc_info:
        asyncio.run(ServiceKeyService.rotate(_Session(), "k1"))
    assert exc_info.value.code == ErrorCode.BIZ_CONFLICT


def test_touch_last_used_failure_is_swallowed() -> None:
    """使用痕迹写入与回滚均失败 → 仅告警，不向上抛出（不阻断认证）."""

    class _Session:
        async def execute(self, *args, **kwargs):
            raise RuntimeError("db down")

        async def rollback(self) -> None:
            raise RuntimeError("rollback down")

    asyncio.run(ServiceKeyService.touch_last_used(_Session(), "k1"))


def test_mark_revoked_is_idempotent() -> None:
    """已吊销 Key 再次吊销 → 直接返回，不重复写审计/事件."""
    record = SimpleNamespace(status=service_keys.SERVICE_KEY_STATUS_REVOKED)

    class _Session:
        def add(self, *args, **kwargs) -> None:
            raise AssertionError("already revoked should not write audit")

    asyncio.run(ServiceKeyService._mark_revoked(_Session(), record))
