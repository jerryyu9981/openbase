"""OB-12 角色互译表读写与结构/语义校验（P2-1 §6.2；批次 2/T6 完整落地）.

本模块承载互译表 JSON 数据模型（schema_version/anchors/systems）的读取、
结构/语义校验与翻译函数。批次 1（T1~T3）仅提供骨架与无表透传语义；
批次 2/T6 落地：语义档 rank 校验（越档拒绝）、双向逆一致校验、起步
OpenBase↔DPS 互译（Q-D-1~Q-D-3 已确认）与出站翻译 fail-closed。

Q-D 结论（§6.4，T6-6 回写）：
- Q-D-1 起步仅 OpenBase↔DPS 两~三档语义（manage/readonly 最低可用；
  readwrite 经 org_admin 对账纳入），其余系统接入时扩展。
- Q-D-2 OpenBase 现役 code 无 ``editor``；editor（读写/域管理）语义档由
  ``org_admin`` 承担，``editor`` 码不入互译表（避免幽灵码）。
- Q-D-3 未映射角色 fail-closed：拒绝（403）优先于降级提示（默认 viewer）。
"""
from __future__ import annotations

import json
import logging
from typing import Any

from openbase.core.errors import BaseError, ErrorCode
from openbase.modules.protocol_headers.constants import (
    ALLOWED_OPENBASE_ROLE_CODES,
)

logger = logging.getLogger("openbase.protocol_headers.role_map")

__all__ = [
    "OPENBASE_ROLE_CODES",
    "ROLE_MAP_ANCHOR_RANKS",
    "ROLE_MAP_SCHEMA_VERSION",
    "default_role_intertranslate",
    "load_role_map",
    "target_role_anchors",
    "target_role_codes",
    "translate_role_code",
    "validate_role_map",
    "validate_role_map_structure",
]

ROLE_MAP_SCHEMA_VERSION = 1

# 语义档（§6.2 anchors；只读参考，rank 用于越档校验）
OPENBASE_ROLE_ANCHORS: dict[str, str] = {
    "admin": "manage",
    "org_admin": "readwrite",
    "org_member": "readonly",
    "viewer": "readonly",
}

# 现役 OpenBase 角色码集（== protocol_headers.constants.ALLOWED_OPENBASE_ROLE_CODES；
# editor 不入表，Q-D-2）
OPENBASE_ROLE_CODES: frozenset[str] = ALLOWED_OPENBASE_ROLE_CODES

# 语义档 rank（档位越高越宽；manage>readwrite>readonly）
ROLE_MAP_ANCHOR_RANKS: dict[str, int] = {
    "manage": 3,
    "readwrite": 2,
    "readonly": 1,
}

# 目标系统角色码域（起步仅 dps，§6.2；其余系统接入时扩展）
_TARGET_ROLE_CODES: dict[str, frozenset[str]] = {
    "dps": frozenset({"super_admin", "org_admin", "user"}),
}

# 目标系统角色码 → 语义档（供跨系统 rank 越档校验；按 §6.1 对账结论登记）
_TARGET_ROLE_ANCHORS: dict[str, dict[str, str]] = {
    "dps": {
        "super_admin": "manage",
        "org_admin": "readwrite",
        "user": "readonly",
    },
}


def target_role_codes(target_system: str) -> frozenset[str]:
    """目标系统已知角色码域（无登记 → 空集，语义校验对该系统放行 target 枚举）."""
    return _TARGET_ROLE_CODES.get(target_system, frozenset())


def target_role_anchors(target_system: str) -> dict[str, str]:
    """目标系统角色码 → 语义档映射（rank 校验用；未登记 → 空表）."""
    return dict(_TARGET_ROLE_ANCHORS.get(target_system, {}))


def load_role_map(raw_json: str | None) -> dict[str, Any]:
    """解析互译表 JSON（settings.role_intertranslate；批次 2 接入 settings）.

    Args:
        raw_json: JSON 字符串；None/空 → 空表（无互译配置）。

    Returns:
        互译表 dict；非法 JSON → 400 PARAM_INVALID（配置错误 fail-fast）。
    """
    if not raw_json:
        return {}
    try:
        data = json.loads(raw_json)
    except (TypeError, ValueError) as exc:
        raise BaseError(
            ErrorCode.PARAM_INVALID,
            "role_intertranslate must be valid JSON",
            detail={"error": str(exc)},
        ) from exc
    if not isinstance(data, dict):
        raise BaseError(
            ErrorCode.PARAM_INVALID,
            "role_intertranslate must be a JSON object",
        )
    return data


def default_role_intertranslate() -> dict[str, Any]:
    """示范默认互译表（草案 §6.2 起步值；生产经 .env/配置覆盖）."""
    return {
        "schema_version": ROLE_MAP_SCHEMA_VERSION,
        "reconciled_at": "2026-09-07",
        "anchors": {name: {"rank": ROLE_MAP_ANCHOR_RANKS[name]} for name in ROLE_MAP_ANCHOR_RANKS},
        "systems": {
            "dps": {
                "openbase_to_target": {
                    "admin": {"target": "super_admin", "anchor": "manage"},
                    "org_admin": {"target": "org_admin", "anchor": "readwrite"},
                    "org_member": {"target": "user", "anchor": "readonly"},
                    "viewer": {"target": "user", "anchor": "readonly"},
                },
                "target_to_openbase": {
                    "super_admin": {"source": ["admin"]},
                    "org_admin": {"source": ["org_admin"]},
                    "user": {"source": ["org_member", "viewer"]},
                },
            }
        },
    }


def validate_role_map_structure(data: dict[str, Any]) -> list[str]:
    """结构校验（schema_version/systems 骨架；语义校验见 :func:`validate_role_map`）.

    Args:
        data: load_role_map 产出的互译表 dict。

    Returns:
        结构错误信息列表（空 = 通过）。
    """
    errors: list[str] = []
    if not isinstance(data, dict) or not data:
        return ["role_intertranslate empty"]
    if data.get("schema_version") != ROLE_MAP_SCHEMA_VERSION:
        errors.append(f"schema_version must be {ROLE_MAP_SCHEMA_VERSION}")
    systems = data.get("systems")
    if not isinstance(systems, dict):
        return errors + ["systems section missing"]
    for system_name, section in systems.items():
        if not isinstance(section, dict):
            errors.append(f"system {system_name} section invalid")
            continue
        if "openbase_to_target" not in section:
            errors.append(f"system {system_name} missing openbase_to_target")
        if "target_to_openbase" not in section:
            errors.append(f"system {system_name} missing target_to_openbase")
    return errors


def validate_role_map(data: dict[str, Any]) -> list[str]:
    """互译表语义校验（§6.2）：JSON 合法、code 集合法、无重复源、无越档、双向逆一致.

    规则（对每个 systems.<system> 段）：
    1. 结构骨架：schema_version / openbase_to_target / target_to_openbase（结构函数）；
    2. 源 code 集合法：openbase_to_target 源码必须在现役 OpenBase 码集（editor/幽灵码拒绝）；
    3. 目标 code 集合法：登记了目标枚举的系统（dps）中 target/回译目标码必须在枚举内；
    4. 无重复源：回译单目标 source 列表不得重复 code；
    5. 语义档越档校验：源角色语义档 rank < 目标角色语义档 rank（如 org_member→
       super_admin）→ 非法（升档）；降档/同档允许（rank 单调不减即合）；
    6. 双向逆一致：target_to_openbase 与 openbase_to_target 逐目标互逆。

    Args:
        data: load_role_map 产出的互译表 dict。

    Returns:
        语义错误信息列表（空 = 通过）。调用方（settings 装配/verify-env）对非空
        errors 应 fail-fast（配置错误拒绝启动），避免互译表带病上生产。
    """
    errors = validate_role_map_structure(data)
    if errors:
        return errors

    systems = data.get("systems")
    if not isinstance(systems, dict):
        return errors

    for system_name, section in systems.items():
        system_label = f"system {system_name}"
        forward = section.get("openbase_to_target")
        reverse = section.get("target_to_openbase")
        if not isinstance(forward, dict):
            errors.append(f"{system_label}: openbase_to_target must be an object")
            continue
        if not isinstance(reverse, dict):
            errors.append(f"{system_label}: target_to_openbase must be an object")
            continue

        target_enum = target_role_codes(system_name)
        target_anchor_by_code = target_role_anchors(system_name)

        # ---- 前向表语义 ----
        forward_by_target: dict[str, set[str]] = {}
        for source_code, entry in forward.items():
            if source_code not in OPENBASE_ROLE_CODES:
                errors.append(
                    f"{system_label}: unknown source role {source_code!r} "
                    "(must be current OpenBase role; editor not in table)"
                )
                continue
            if not isinstance(entry, dict):
                errors.append(
                    f"{system_label}: mapping for {source_code} must be an object"
                )
                continue
            target_code = entry.get("target")
            anchor = entry.get("anchor")
            canonical_anchor = OPENBASE_ROLE_ANCHORS.get(source_code)
            if anchor is not None and anchor != canonical_anchor:
                errors.append(
                    f"{system_label}: {source_code} anchor {anchor!r} != canonical "
                    f"{canonical_anchor!r}"
                )
            if not isinstance(target_code, str) or not target_code:
                errors.append(
                    f"{system_label}: {source_code} missing target role"
                )
                continue
            if target_enum and target_code not in target_enum:
                errors.append(
                    f"{system_label}: target role {target_code!r} not in "
                    f"{system_name} role enumeration"
                )
            forward_by_target.setdefault(target_code, set()).add(source_code)

            # ---- 越档校验（升档拒绝）----
            if canonical_anchor is not None and target_code in target_anchor_by_code:
                source_rank = ROLE_MAP_ANCHOR_RANKS.get(canonical_anchor)
                target_rank = ROLE_MAP_ANCHOR_RANKS.get(
                    target_anchor_by_code[target_code]
                )
                if (
                    source_rank is not None
                    and target_rank is not None
                    and source_rank < target_rank
                ):
                    errors.append(
                        f"{system_label}: uprank forbidden {source_code} "
                        f"({canonical_anchor}/{source_rank}) -> {target_code} "
                        f"({target_anchor_by_code[target_code]}/{target_rank})"
                    )

        # ---- 回译表语义 + 双向逆一致 ----
        known_sources = set(forward)
        reverse_sources_by_target: dict[str, set[str]] = {}
        for target_code, entry in reverse.items():
            if target_enum and target_code not in target_enum:
                errors.append(
                    f"{system_label}: reverse target {target_code!r} not in "
                    f"{system_name} role enumeration"
                )
            if not isinstance(entry, dict):
                errors.append(
                    f"{system_label}: reverse entry for {target_code} must be an object"
                )
                continue
            source_list = entry.get("source")
            if not isinstance(source_list, list):
                errors.append(
                    f"{system_label}: reverse {target_code} missing source list"
                )
                continue
            seen: set[str] = set()
            for source_code in source_list:
                if source_code not in OPENBASE_ROLE_CODES:
                    errors.append(
                        f"{system_label}: reverse source {source_code!r} not in "
                        "current OpenBase role set"
                    )
                    continue
                if source_code in seen:
                    errors.append(
                        f"{system_label}: duplicate reverse source {source_code!r} "
                        f"under {target_code}"
                    )
                seen.add(source_code)
                if source_code not in known_sources:
                    errors.append(
                        f"{system_label}: reverse source {source_code!r} has no "
                        "forward mapping"
                    )
            reverse_sources_by_target[target_code] = seen

        # 逆一致：前向目标集合 == 有效回译目标集合（空源回译条目视为未启用），
        # 且逐目标源集合相等
        effective_reverse_targets = {
            target_code for target_code, sources in reverse_sources_by_target.items() if sources
        }
        if set(forward_by_target) != effective_reverse_targets:
            missing_forward = set(forward_by_target) - effective_reverse_targets
            missing_reverse = effective_reverse_targets - set(forward_by_target)
            if missing_forward:
                errors.append(
                    f"{system_label}: forward targets without reverse entry: "
                    f"{sorted(missing_forward)}"
                )
            if missing_reverse:
                errors.append(
                    f"{system_label}: reverse targets without forward mapping: "
                    f"{sorted(missing_reverse)}"
                )
        for target_code, forward_sources in forward_by_target.items():
            reverse_sources = reverse_sources_by_target.get(target_code)
            if reverse_sources is None:
                continue
            if forward_sources != reverse_sources:
                errors.append(
                    f"{system_label}: inverse inconsistent for {target_code}: "
                    f"forward={sorted(forward_sources)} reverse={sorted(reverse_sources)}"
                )
    return errors


def translate_role_code(
    role_map: dict[str, Any] | None,
    target_system: str,
    role_code: str | None,
) -> str | None:
    """出站角色翻译挂点（§6.3/§3.2-4；批次 2 挂 dps 互译表）.

    - 未配置互译表 / 目标系统无表 → 原样透传 OpenBase 角色码（无互译系统语义）。
    - 配置了目标系统 openbase_to_target 表：命中 → 目标码；未命中（未知源 code）
      → **fail-closed**（不静默降 viewer，§6.4 Q-D-3，403 由装配层转出站错误）。

    Args:
        role_map: 互译表 dict；None/空 → 无表透传。
        target_system: 目标系统键（dps/llm/rag/memory）。
        role_code: OpenBase 角色码。

    Returns:
        目标角色码；无表/空码返回原值。

    Raises:
        BaseError: 目标系统配置了表但 role_code 无映射 → 403（fail-closed）。
    """
    if not role_code:
        return None
    if not isinstance(role_map, dict) or not role_map.get("systems"):
        return role_code
    systems = role_map.get("systems") or {}
    section = systems.get(target_system)
    if not isinstance(section, dict):
        return role_code
    openbase_to_target = section.get("openbase_to_target")
    if not isinstance(openbase_to_target, dict) or not openbase_to_target:
        return role_code
    entry = openbase_to_target.get(role_code)
    if entry is None:
        raise BaseError(
            ErrorCode.PERM_FORBIDDEN,
            f"role {role_code} has no mapping for target system {target_system}",
            detail={"role": role_code, "target_system": target_system},
        )
    if isinstance(entry, dict):
        return str(entry.get("target") or entry)
    return str(entry)
