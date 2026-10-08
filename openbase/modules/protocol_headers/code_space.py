"""出站租户码空间登记的运行期解析（A 批 A1/A2 统一入口）.

把「各目标可接受/保留/兜底租户码」的登记从各 proxy 内散落的字面量与独立字段，
收敛为**单一登记入口**：

- 内置基线：`openbase.settings.OUTBOUND_RESERVED_TENANT_CODES_BY_TARGET`（保留码）
  与 `BUILTIN_DEFAULT_TENANT_CODE_BY_TARGET`（兜底码）；
- 覆盖：`settings.proxy_code_map`（JSON，按目标按字段覆盖）；
- 校验：与启动期同一组纯函数（`settings.resolve_target_code_space` /
  `validate_target_code_space`），本模块在其上补一层**运行期二次防线**（`BaseError`）。

语义约束（R-387 实测依据见 `doc/test/evidence/manual/r387-*.json`）：
- OpenRAG：保留码 `{default, openrag-local}`，受信入站携带即 400；
- OpenMemory：无保留码语义，但按组织策略 fail-closed，仅接受其已登记组织码；
- OpenLLM / DPS：无保留码语义且**不设兜底**（主体无租户声明时省略 X-Tenant-ID）。
"""
from __future__ import annotations

from openbase.core.errors import BaseError, ErrorCode
from openbase.settings import (
    get_settings,
    resolve_target_code_space,
    validate_target_code_space,
)

__all__ = [
    "TargetCodeSpace",
    "get_target_code_space",
    "reserved_tenant_map",
]


class TargetCodeSpace:
    """某目标域的租户码空间登记视图."""

    __slots__ = ("target", "reserved_codes", "default_tenant_code")

    def __init__(
        self, target: str, reserved_codes: frozenset[str], default_tenant_code: str | None
    ) -> None:
        self.target = target
        self.reserved_codes = reserved_codes
        self.default_tenant_code = default_tenant_code

    @property
    def has_default(self) -> bool:
        """该目标是否设兜底码（False 表示无声明时省略 X-Tenant-ID）."""
        return bool(self.default_tenant_code)

    def reserved_map(self) -> dict[str, str]:
        """保留码 → 兜底码 的归一映射；无兜底码时返回空表（不做归一）."""
        if not self.default_tenant_code:
            return {}
        return {code: self.default_tenant_code for code in self.reserved_codes}

    def __repr__(self) -> str:  # pragma: no cover - 便于排障
        return (
            f"TargetCodeSpace(target={self.target!r}, "
            f"reserved_codes={sorted(self.reserved_codes)}, "
            f"default_tenant_code={self.default_tenant_code!r})"
        )


def _resolve_all() -> dict[str, TargetCodeSpace]:
    """解析全部目标的码空间（含运行期二次防线校验）.

    Raises:
        BaseError: 登记表非法（JSON/结构）或某目标兜底码为空/命中该目标保留码。
    """
    raw = get_settings().proxy_code_map
    try:
        resolved = resolve_target_code_space(raw)
        validate_target_code_space(resolved)
    except ValueError as exc:  # 纯函数以 ValueError 表达；此处转换为统一业务错误
        raise BaseError(
            ErrorCode.PARAM_INVALID,
            f"出站租户码空间登记非法：{exc}",
            detail={"hint": "fix OPENBASE_PROXY_CODE_MAP (see settings.proxy_code_map)"},
        ) from exc

    spaces: dict[str, TargetCodeSpace] = {}
    for target, entry in resolved.items():
        default_code = entry.get("default_tenant_code")
        spaces[target] = TargetCodeSpace(
            target=target,
            reserved_codes=frozenset(entry.get("reserved_codes") or ()),
            default_tenant_code=str(default_code) if default_code is not None else None,
        )
    return spaces


def get_target_code_space(target: str) -> TargetCodeSpace:
    """取指定目标的码空间登记视图.

    Args:
        target: 目标系统键（rag / memory / llm / dps）。

    Returns:
        TargetCodeSpace；未登记的目标返回「无保留码、无兜底」的空登记视图（安全默认）。
    """
    return _resolve_all().get(target, TargetCodeSpace(target, frozenset(), None))


def reserved_tenant_map(target: str) -> dict[str, str]:
    """取指定目标的「保留码 → 兜底码」归一映射（无兜底码时为空表）."""
    return get_target_code_space(target).reserved_map()
