"""C1-d / C2 码值规范化（通用能力）：组织/租户标识的「码 ↔ UUID」双形态解析与回填.

照搬 DPS 既有语义（`src/middleware/tenant_middleware.py:287-319`：`_looks_uuid` 选列 →
存在/启停校验 → **统一回填库内 UUID**），并抽为**纯函数**供各系统复用。

设计边界：本模块**零依赖**（仅标准库），不绑定数据源；查询与校验由调用方经 `resolver` 注入，
故可被 OpenBase 与四仓共用而不引入跨层耦合。
"""
from __future__ import annotations

import re
import uuid
from collections.abc import Callable

_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

LOOKUP_BY_ID = "id"
LOOKUP_BY_CODE = "code"


def is_uuid_like(value: str | None) -> bool:
    """是否 UUID 形态（与 DPS `_looks_uuid` 同语义：正则判定，不做版本/变体校验）."""
    if not value:
        return False
    return bool(_UUID_RE.match(str(value).strip()))


def pick_lookup_column(value: str | None) -> str:
    """按形态选择查询列：UUID 形态 → ``id``；其余 → ``code``."""
    return LOOKUP_BY_ID if is_uuid_like(value) else LOOKUP_BY_CODE


def canonical_uuid(value: str | None) -> str | None:
    """UUID 形态规范化为标准小写连字符形式；非 UUID 形态 → ``None``."""
    if not is_uuid_like(value):
        return None
    return str(uuid.UUID(str(value).strip()))


def normalize_code_or_id(
    value: str | None,
    resolver: Callable[[str, str], str | None],
) -> str | None:
    """双形态解析并**回填 canonical UUID**（C1-d 核心能力）.

    Args:
        value: 请求携带的组织/租户标识（code 或 UUID）。
        resolver: ``(column, value) -> canonical_id | None``；``column`` ∈ ``{"id","code"}``。
            由调用方注入（DB 查询 / 注册表查找），本模块不绑定数据源。

    Returns:
        canonical UUID 字符串；不存在或无法解析 → ``None``（调用方据此 fail-closed）。
    """
    if not value:
        return None
    column = pick_lookup_column(value)
    resolved = resolver(column, str(value).strip())
    if not resolved:
        return None
    return canonical_uuid(resolved) or str(resolved)