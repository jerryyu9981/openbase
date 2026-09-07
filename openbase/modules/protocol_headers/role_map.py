"""OB-12 角色互译表读写与结构校验（P2-1 §6.2；批次 2/T6 完整落地）.

本模块承载互译表 JSON 数据模型（schema_version/anchors/systems）的读取、
结构校验与翻译函数；P2-1 批次 1（T1~T3）内仅提供骨架与无表透传语义，
完整语义档 rank/双向逆一致校验与起步映射随批次 2/T6 落地。
"""
from __future__ import annotations

import json
import logging
from typing import Any

from openbase.core.errors import BaseError, ErrorCode

logger = logging.getLogger("openbase.protocol_headers.role_map")

__all__ = [
    "ROLE_MAP_SCHEMA_VERSION",
    "default_role_intertranslate",
    "load_role_map",
    "translate_role_code",
    "validate_role_map_structure",
]

ROLE_MAP_SCHEMA_VERSION = 1

# 语义档（只读参考，§6.2 anchors；批次 2 用于越档校验）
_ANCHORS = {
    "manage": {"rank": 3},
    "readwrite": {"rank": 2},
    "readonly": {"rank": 1},
}


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
        "anchors": dict(_ANCHORS),
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
    """结构校验骨架（批次 2/T6 完整语义校验：越档/重复源/双向逆一致）.

    Args:
        data: load_role_map 产出的互译表 dict。

    Returns:
        结构错误信息列表（空 = 通过）。仅检查 schema_version/systems 骨架；
        越档与逆一致语义校验随批次 2/T6 的 validate_role_map 落地。
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
