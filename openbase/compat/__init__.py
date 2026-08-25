"""openbase 回灌兼容层：四系统旧 API 别名与字段映射（TD-11-07，BL-101）.

设计要点：
- 旧实现不删除（Git 历史保留），兼容层提供别名/映射桥接
- 配置驱动：映射表可扩展，默认空（四系统回灌时按需注册）
- 使用方：OpenLLM/OpenRAG/OpenMemory/DPS 回灌时 import 本层替代旧函数
"""

from __future__ import annotations

import logging

logger = logging.getLogger("openbase.compat")

# 字段映射注册表：{系统: {旧字段: 新字段}}
_FIELD_MAPS: dict[str, dict[str, str]] = {}

# 函数别名注册表：{系统: {旧名: 新可调用对象}}
_FUNC_ALIASES: dict[str, dict[str, object]] = {}


def register_field_map(system: str, mapping: dict[str, str]) -> None:
    """注册系统字段映射（旧字段 → openbase 标准字段）.

    Args:
        system: 系统名（openllm/openrag/openmemory/dps）。
        mapping: {旧字段名: 新字段名}。
    """
    _FIELD_MAPS.setdefault(system, {}).update(mapping)
    logger.info("field map registered", extra={"system": system, "count": len(mapping)})


def map_fields(system: str, data: dict) -> dict:
    """按系统映射表转换字段名（未知字段原样保留）.

    Args:
        system: 系统名。
        data: 原始数据。

    Returns:
        字段映射后的数据。
    """
    mapping = _FIELD_MAPS.get(system, {})
    if not mapping:
        return data
    return {mapping.get(k, k): v for k, v in data.items()}


def register_func_alias(system: str, old_name: str, func: object) -> None:
    """注册旧函数别名（旧名 → openbase 实现）.

    Args:
        system: 系统名。
        old_name: 旧函数名。
        func: openbase 实现（可调用对象）。
    """
    _FUNC_ALIASES.setdefault(system, {})[old_name] = func
    logger.info("func alias registered", extra={"system": system, "old": old_name})


def get_alias(system: str, old_name: str):
    """获取旧函数别名对应的 openbase 实现（未注册返回 None）.

    Args:
        system: 系统名。
        old_name: 旧函数名。

    Returns:
        对应实现或 None。
    """
    return _FUNC_ALIASES.get(system, {}).get(old_name)


# ---- 通用回滚提示 ----
ROLLBACK_HINT = (
    "回滚：任一系统灰度验证失败时 git revert 对应 commit，"
    "旧实现保留于 Git 历史；详见 doc/guides/OpenBase-四系统接入指南-v1.1.0.md"
)


def rollback_hint() -> str:
    """返回回滚提示文本."""
    return ROLLBACK_HINT


__all__ = [
    "register_field_map",
    "map_fields",
    "register_func_alias",
    "get_alias",
    "rollback_hint",
]
