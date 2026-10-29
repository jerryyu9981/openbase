"""时间工具：UTC aware 归一（E1-3/R12，消除 naive/aware 比较缺陷）.

SQLite 等后端读出的 ``DateTime(timezone=True)`` 常为 naive datetime；与
``datetime.now(timezone.utc)`` 直接比较会抛 ``TypeError``。统一经 :func:`as_utc`
解释为 UTC aware，避免各处重复实现。
"""

from __future__ import annotations

import datetime as dt

__all__ = ["as_utc", "utc_now"]


def utc_now() -> dt.datetime:
    """当前 UTC aware 时间."""
    return dt.datetime.now(dt.timezone.utc)


def as_utc(value: dt.datetime | None) -> dt.datetime | None:
    """把 datetime 归一为 UTC aware（naive 按 UTC 解释；None 原样返回）."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=dt.timezone.utc)
    return value.astimezone(dt.timezone.utc)
