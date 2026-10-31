"""统一角色字典契约（C-10；残余项 P2）.

对外提供只读契约 ``GET /api/v1/auth/roles/contract``：角色码、语义档位（
``readonly < readwrite < manage``）、权限点与本地别名映射，供下游四仓
（OpenLLM/OpenRAG/OpenMemory/DPS）替换各自硬编码的角色映射（下游替换归 K-04）。

数据来源：
- 档位锚点与角色码集合：``config/role_tier_anchors.json``（缺失/损坏时回落内置
  基线并 WARN，保持契约可用）；
- 权限点：DB ``roles → role_permission → permissions`` 只读查询（DB 不可达时返回
  空映射，契约仅含档位与角色码，不阻塞登录）。

安全边界：只输出角色码/档位/权限点等**非敏感元数据**，不含任何密钥、令牌、
证书或用户级数据。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("openbase.auth.role_contract")

CONTRACT_SCHEMA_VERSION = 1
CONTRACT_SOURCE = "openbase"
UNKNOWN_CODE_POLICY = "fail-closed"

# 内置基线（与 config/role_tier_anchors.json 对齐，作为配置不可用时的兜底）
_FALLBACK_ANCHORS: dict[str, str] = {
    "admin": "manage",
    "org_admin": "readwrite",
    "user": "readonly",
    "org_member": "readonly",
    "viewer": "readonly",
}
_FALLBACK_TIER_ORDER: dict[str, int] = {"readonly": 1, "readwrite": 2, "manage": 3}
_FALLBACK_TIER_MEANING: dict[str, str] = {
    "readonly": "只读：允许读类方法（GET/HEAD/OPTIONS）",
    "readwrite": "读写：在读类基础上允许写类方法（POST/PUT/PATCH/DELETE）",
    "manage": "管理：读写 + 管理类操作（角色/权限/生命周期/豁免）",
}
_FALLBACK_CANONICAL: tuple[str, ...] = (
    "admin",
    "org_admin",
    "org_member",
    "user",
    "viewer",
)
_FALLBACK_ALIASES: dict[str, dict[str, str]] = {
    "member": {"canonical": "org_member", "tier": "readonly"}
}
_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "role_tier_anchors.json"


def _load_anchor_config() -> dict[str, Any]:
    """读取档位锚点配置（不可读/非法 JSON → 空 dict，调用方回落内置基线）."""
    try:
        parsed = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning(
            "role tier anchors unavailable; contract uses builtin baseline",
            extra={"error": str(exc) or exc.__class__.__name__},
        )
        return {}
    if not isinstance(parsed, dict):
        logger.warning("role tier anchors malformed; contract uses builtin baseline")
        return {}
    return parsed


def build_role_contract(
    role_permissions: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """构建统一角色字典契约（纯函数，便于下游快照比对与单测）.

    Args:
        role_permissions: 角色码 → 权限点列表（DB 查询结果；``None`` 表示不可达）。

    Returns:
        契约字典：schema_version/source/unknown_code_policy/tiers/anchors/
        canonical_role_codes/local_role_aliases/roles。
    """
    config = _load_anchor_config()
    configured_anchors = config.get("anchors")
    anchors = {
        **_FALLBACK_ANCHORS,
        **(configured_anchors if isinstance(configured_anchors, dict) else {}),
    }
    tiers = config.get("tiers") if isinstance(config.get("tiers"), dict) else {}
    order = tiers.get("order") if isinstance(tiers.get("order"), dict) else _FALLBACK_TIER_ORDER
    meaning = (
        tiers.get("meaning")
        if isinstance(tiers.get("meaning"), dict)
        else _FALLBACK_TIER_MEANING
    )
    canonical_codes = config.get("canonical_role_codes")
    canonical = (
        canonical_codes.get("set")
        if isinstance(canonical_codes, dict)
        and isinstance(canonical_codes.get("set"), list)
        and canonical_codes.get("set")
        else list(_FALLBACK_CANONICAL)
    )
    aliases = config.get("local_role_aliases")
    local_aliases = aliases if isinstance(aliases, dict) else _FALLBACK_ALIASES

    permissions = {
        str(code): [str(item) for item in items]
        for code, items in (role_permissions or {}).items()
    }
    codes = list(dict.fromkeys([*canonical, *permissions.keys()]))
    roles = [
        {
            "code": code,
            "tier": anchors.get(code),
            "mapped": code in anchors,
            "permissions": permissions.get(code, []),
        }
        for code in codes
    ]
    return {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "source": CONTRACT_SOURCE,
        "unknown_code_policy": UNKNOWN_CODE_POLICY,
        "tiers": {"order": dict(order), "meaning": dict(meaning)},
        "anchors": dict(anchors),
        "canonical_role_codes": [str(code) for code in canonical],
        "local_role_aliases": dict(local_aliases),
        "roles": roles,
    }


async def load_role_permissions(session: Any) -> dict[str, list[str]] | None:
    """读取「角色码 → 权限点」映射（只读；DB 不可达返回 None，由契约回落基线）."""
    from sqlalchemy import select

    from openbase.core.models import Permission, Role, role_permission

    try:
        result = await session.execute(
            select(Role.code, Permission.code)
            .join(role_permission, role_permission.c.role_id == Role.id)
            .join(Permission, Permission.id == role_permission.c.permission_id)
        )
    except Exception as exc:  # noqa: BLE001 - DB 不可达不阻塞契约可读性
        logger.warning(
            "role permission query failed; contract falls back to canonical baseline",
            extra={"error": str(exc) or exc.__class__.__name__},
        )
        return None
    mapping: dict[str, list[str]] = {}
    for role_code, permission_code in result.all():
        mapping.setdefault(str(role_code), []).append(str(permission_code))
    return mapping
