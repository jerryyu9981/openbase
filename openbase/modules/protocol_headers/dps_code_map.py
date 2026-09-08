"""dps org/tenant code→UUID 登记式基线（P2-1 §7.2，批次 3/T7 OB-8）.

dps_code_map（settings JSON，登记式基线）承载 DPS 侧 org/tenant UUID 与 OpenBase
``tenants.code``（唯一事实源）的映射，取代早期自由形态 ``dps_org_map/dps_tenant_map``：

    {
      "schema_version": 1,
      "source_of_truth": "openbase.tenants.code",
      "last_reconciled_at": "2026-09-07",
      "entries": [
        {"tenant_code": "acme", "dps_org_id": "<uuid>", "dps_tenant_id": "<uuid>",
         "reconciled_at": "2026-09-07", "status": "verified"}
      ]
    }

- 默认无条目（空表）；``dps_default_org_id/dps_default_tenant_id`` 标记 deprecated，
  仅作显式兜底保留并在 verify-env 中 WARN（T7-6）。
- 旧 JSON（dps_org_map/dps_tenant_map）解析兼容升级到登记式基线：
  ``build_compat_value_maps`` 将基线条目折算为 org/tenant 值映射并**优先于**旧表。
- 新租户经迁移/对账工具（``scripts/audit_dps_code_map.py``，T7-7）登记入基线，
  禁止运行期隐式新增。冲突（同 code 双映射不同 DPS 值）须 S7 前清零。

与 role_map.py 同构：校验函数返回可读 error 字符串列表（无错误 = 合法）。
"""
from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger("openbase.protocol_headers.dps_code_map")

__all__ = [
    "DPS_CODE_MAP_SCHEMA_VERSION",
    "build_compat_value_maps",
    "default_dps_code_map",
    "dps_code_map_conflicts",
    "parse_dps_code_map",
    "validate_dps_code_map",
]

DPS_CODE_MAP_SCHEMA_VERSION = 1

# 唯一事实源（§7.2：以 OpenBase tenants.code 为准，R-L3-1/Q3）
SOURCE_OF_TRUTH = "openbase.tenants.code"

# 条目必需键
_REQUIRED_ENTRY_KEYS: tuple[str, ...] = ("tenant_code", "dps_org_id", "dps_tenant_id")

# 冲突/状态可解释字段
_CONFLICT_REASON_KEYS: tuple[str, ...] = ("tenant_code", "dps_org_id", "dps_tenant_id")


def default_dps_code_map() -> dict[str, Any]:
    """登记式基线空模板（schema_version + 空 entries）."""
    return {
        "schema_version": DPS_CODE_MAP_SCHEMA_VERSION,
        "source_of_truth": SOURCE_OF_TRUTH,
        "last_reconciled_at": "",
        "entries": [],
    }


def parse_dps_code_map(raw_json: str | None) -> dict[str, Any]:
    """解析 settings.dps_code_map JSON → 基线 dict（非法/空 → 空表 WARN）.

    Args:
        raw_json: JSON 字符串（settings.dps_code_map）。

    Returns:
        基线 dict（{schema_version, source_of_truth, last_reconciled_at, entries}）；
        空/非法/标量输入 → 空表（登记式语义：宁可空表不做隐式猜值）。
    """
    if not raw_json:
        return default_dps_code_map()
    try:
        data = json.loads(raw_json)
    except (TypeError, ValueError):
        logger.warning("dps_code_map invalid JSON; treated as empty baseline")
        return default_dps_code_map()
    if not isinstance(data, dict):
        logger.warning("dps_code_map must be a JSON object; treated as empty baseline")
        return default_dps_code_map()
    data.setdefault("schema_version", DPS_CODE_MAP_SCHEMA_VERSION)
    data.setdefault("source_of_truth", SOURCE_OF_TRUTH)
    data.setdefault("last_reconciled_at", "")
    data.setdefault("entries", [])
    return data


def _entries_of(data_or_raw: dict[str, Any] | str | None) -> list[dict[str, Any]]:
    """归一化输入为 entries 列表（parse 失败 → []，便于逐项校验报告）."""
    if isinstance(data_or_raw, str):
        data = parse_dps_code_map(data_or_raw)
    elif data_or_raw is None:
        return []
    else:
        data = data_or_raw
    entries = data.get("entries") or []
    return [entry for entry in entries if isinstance(entry, dict)]


def validate_dps_code_map(
    data_or_raw: dict[str, Any] | str | None,
    *,
    known_tenant_codes: set[str] | None = None,
) -> list[str]:
    """登记式基线校验（§7.2）：结构/键/无重复/命中 tenants.code/冲突.

    Args:
        data_or_raw: 基线 dict 或原始 JSON 字符串；None/空 → 空表（默认合法）。
        known_tenant_codes: ``tenants.code`` 唯一事实源集合（None = 跳过 code 命中
            校验，供无 DB 上下文调用/脚本 DB 位关闭时使用）。

    Returns:
        可读错误消息列表；[] = 校验通过（0 未决为门禁）。
    """
    errors: list[str] = []

    def _require(payload: dict[str, Any] | str | None) -> dict[str, Any] | None:
        if isinstance(payload, str):
            if not payload:
                return default_dps_code_map()
            try:
                loaded = json.loads(payload)
            except (TypeError, ValueError) as exc:
                errors.append(f"invalid JSON: {exc}")
                return None
            if not isinstance(loaded, dict):
                errors.append("dps_code_map must be a JSON object")
                return None
            return loaded
        if payload is None:
            return default_dps_code_map()
        return payload if isinstance(payload, dict) else None

    data = _require(data_or_raw)
    if data is None:
        return errors
    if data.get("schema_version") != DPS_CODE_MAP_SCHEMA_VERSION:
        errors.append(
            f"schema_version must be {DPS_CODE_MAP_SCHEMA_VERSION}"
        )
    entries = data.get("entries") or []
    if not isinstance(entries, list):
        errors.append("entries must be a JSON array")
        return errors

    seen_codes: dict[str, list[dict[str, Any]]] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"entries[{index}] must be an object")
            continue
        for key in _REQUIRED_ENTRY_KEYS:
            if key not in entry or entry.get(key) in (None, ""):
                errors.append(f"entries[{index}].{key} is required and non-empty")
        tenant_code = str(entry.get("tenant_code") or "")
        if not tenant_code:
            continue
        if known_tenant_codes is not None and tenant_code not in known_tenant_codes:
            errors.append(
                f"entries[{index}].tenant_code {tenant_code!r} not in "
                f"tenants.code (source_of_truth)"
            )
        seen_codes.setdefault(tenant_code, []).append(entry)

    for tenant_code, dupes in seen_codes.items():
        if len(dupes) > 1:
            errors.append(
                f"duplicate tenant_code {tenant_code!r} in dps_code_map entries "
                f"(count={len(dupes)})"
            )
    return errors


def dps_code_map_conflicts(
    entries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """冲突检测（R-L3-1 形态，T7-5）：同 code 双映射且 DPS org/tenant 值不同.

    同一 ``tenant_code`` 出现多行时构成"双映射"；值不同即冲突项（须对账清零，
    S7 门禁）。冲突报告字段含可定位的 tenant_code/dps_org_id/dps_tenant_id。

    Args:
        entries: 基线 entries 列表（已按 dict 归一化）。

    Returns:
        冲突项列表（[] = 0 未决冲突）。
    """
    by_code: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        tenant_code = str(entry.get("tenant_code") or "")
        if not tenant_code:
            continue
        by_code.setdefault(tenant_code, []).append(entry)

    conflicts: list[dict[str, Any]] = []
    for tenant_code, dupes in by_code.items():
        if len(dupes) < 2:
            continue
        signatures = {
            (
                str(entry.get("dps_org_id") or ""),
                str(entry.get("dps_tenant_id") or ""),
            )
            for entry in dupes
        }
        if len(signatures) > 1:
            conflicts.append(
                {
                    "tenant_code": tenant_code,
                    "mappings": [
                        {key: entry.get(key) for key in _CONFLICT_REASON_KEYS}
                        for entry in dupes
                    ],
                    "reason": "same tenant_code maps different dps org/tenant ids",
                }
            )
    return conflicts


def build_compat_value_maps(
    legacy_org_map: dict[str, Any],
    legacy_tenant_map: dict[str, Any],
    entries: list[dict[str, Any]],
) -> tuple[dict[str, str], dict[str, str]]:
    """旧 JSON 兼容升级 → 登记式基线（§11.2 迁移提示）.

    基线条目（dps_code_map）折算为 org/tenant 值映射并**优先于**旧 dps_org_map/
    dps_tenant_map；未登记 code 回落旧表（兼容读取）。

    Args:
        legacy_org_map: 旧 dps_org_map JSON 解析值。
        legacy_tenant_map: 旧 dps_tenant_map JSON 解析值。
        entries: 登记式基线 entries（dps_code_map）。

    Returns:
        (org_value_map, tenant_value_map)：OpenBase code → DPS 目标值映射
        （供 build_outbound_headers org/tenant 值映射消费）。
    """
    org_map = {str(key): str(value) for key, value in (legacy_org_map or {}).items() if value}
    tenant_map = {str(key): str(value) for key, value in (legacy_tenant_map or {}).items() if value}
    for entry in entries:
        tenant_code = str(entry.get("tenant_code") or "")
        dps_org_id = str(entry.get("dps_org_id") or "")
        dps_tenant_id = str(entry.get("dps_tenant_id") or "")
        if not tenant_code:
            continue
        if dps_org_id:
            org_map[tenant_code] = dps_org_id
        if dps_tenant_id:
            tenant_map[tenant_code] = dps_tenant_id
    return org_map, tenant_map
