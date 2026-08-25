"""config 模块：配置中心（三级合并/版本管理/回滚/事件通知）.

来源：OpenRAG config_center/manager.py（复制级抽取三级配置合并与版本管理模式，
适配 openbase 统一异常与日志约定）。
"""

from __future__ import annotations

import copy
import json
import logging
import os
from collections.abc import Callable
from enum import Enum
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger("openbase.config")

router = APIRouter(prefix="/api/v1/configs", tags=["config"])

# 配置版本保留上限
MAX_VERSIONS = 10


class ConfigLevel(str, Enum):
    """配置级别（来源: OpenRAG config_center，三级配置层次）.

    高等级覆盖低等级：USER > TENANT > SYSTEM。
    """

    SYSTEM = "system"
    TENANT = "tenant"
    USER = "user"


# 级别合并优先级（高等级优先）
LEVEL_ORDER = {ConfigLevel.USER: 3, ConfigLevel.TENANT: 2, ConfigLevel.SYSTEM: 1}


class ConfigVersion:
    """单条配置的版本历史（内存实现，生产接数据库）."""

    def __init__(self, key: str, value: Any, version: int) -> None:
        self.key = key
        self.value = value
        self.version = version


class ConfigStore:
    """配置存储：三级合并（system < tenant < user）+ 版本回滚 + 变更事件.

    来源：OpenRAG config_center/manager.py（ConfigManager 三级合并与版本管理模式）。
    v1.0.0 最小实现：运行时配置存内存，默认值存代码，环境值读环境变量。
    """

    _defaults: dict[str, Any] = {}
    _runtime: dict[str, dict[str, Any]] = {}  # level -> {key: value}
    _versions: dict[str, list[ConfigVersion]] = {}
    _listeners: list[Callable[[str, Any], None]] = []

    # ---- 注册与监听 ----

    @classmethod
    def set_default(cls, key: str, value: Any) -> None:
        """注册默认配置（模块初始化时调用，SYSTEM 级）."""
        cls._defaults[key] = value

    @classmethod
    def on_change(cls, listener: Callable[[str, Any], None]) -> None:
        """注册配置变更监听器（热加载用）."""
        cls._listeners.append(listener)

    # ---- 三级合并取值 ----

    @classmethod
    def get(cls, key: str, level: ConfigLevel | None = None) -> Any:
        """三级合并取值：运行时(USER > TENANT > SYSTEM) > 环境变量 > 默认值.

        Args:
            key: 配置键。
            level: 指定级别取值（None 时按 USER > TENANT > SYSTEM 优先级合并）。

        Returns:
            配置值。
        """
        if level is not None:
            # 指定级别：取该级别运行时值或默认值
            runtime_level = cls._runtime.get(level.value, {})
            if key in runtime_level:
                return copy.deepcopy(runtime_level[key])
            return copy.deepcopy(cls._defaults.get(key))

        # 合并取值：按级别优先级返回最高级存在的值
        for lvl in (ConfigLevel.USER, ConfigLevel.TENANT, ConfigLevel.SYSTEM):
            runtime_level = cls._runtime.get(lvl.value, {})
            if key in runtime_level:
                return copy.deepcopy(runtime_level[key])

        env_key = "OPENBASE_CONFIG_" + key.upper().replace(".", "_")
        if env_key in os.environ:
            return json.loads(os.environ[env_key])
        return copy.deepcopy(cls._defaults.get(key))

    # ---- 写入与版本 ----

    @classmethod
    def set(
        cls, key: str, value: Any, level: ConfigLevel = ConfigLevel.SYSTEM
    ) -> ConfigVersion:
        """写入配置并记录版本（默认 SYSTEM 级）.

        Args:
            key: 配置键。
            value: 配置值。
            level: 配置级别（system/tenant/user）。

        Returns:
            新版本对象。
        """
        cls._runtime.setdefault(level.value, {})[key] = copy.deepcopy(value)
        history = cls._versions.setdefault(key, [])
        version_no = (history[-1].version + 1) if history else 1
        entry = ConfigVersion(key, copy.deepcopy(value), version_no)
        history.append(entry)
        # 保留最近 MAX_VERSIONS 个版本
        if len(history) > MAX_VERSIONS:
            del history[: len(history) - MAX_VERSIONS]
        logger.info(
            "config updated",
            extra={"key": key, "version": version_no, "level": level.value},
        )
        # 变更事件通知（热加载监听）
        for listener in cls._listeners:
            try:
                listener(key, copy.deepcopy(value))
            except Exception:  # noqa: BLE001
                logger.exception("config listener failed", extra={"key": key})
        return entry

    @classmethod
    def versions(cls, key: str) -> list[ConfigVersion]:
        """获取配置版本历史."""
        return list(cls._versions.get(key, []))

    @classmethod
    def rollback(cls, key: str, version: int) -> ConfigVersion | None:
        """回滚到指定版本.

        Args:
            key: 配置键。
            version: 目标版本号。

        Returns:
            回滚后的配置版本；目标版本不存在返回 None。
        """
        history = cls._versions.get(key, [])
        for entry in history:
            if entry.version == version:
                # 回滚到 SYSTEM 级（保持与 set 默认一致）
                cls._runtime.setdefault(ConfigLevel.SYSTEM.value, {})[key] = copy.deepcopy(
                    entry.value
                )
                return entry
        return None


# ---- Schemas ----


class ConfigSetRequest(BaseModel):
    """设置配置请求."""

    key: str
    value: Any
    level: ConfigLevel = ConfigLevel.SYSTEM


class ConfigOut(BaseModel):
    """配置响应."""

    key: str
    value: Any
    level: str = ConfigLevel.SYSTEM.value


class ConfigVersionOut(BaseModel):
    """版本响应."""

    key: str
    version: int
    value: Any


@router.get("/{key}", response_model=ConfigOut)
async def get_config(key: str) -> ConfigOut:
    """获取配置（三级合并）."""
    return ConfigOut(key=key, value=ConfigStore.get(key))


@router.post("", response_model=ConfigOut)
async def set_config(req: ConfigSetRequest) -> ConfigOut:
    """设置配置并记录版本（支持级别）."""
    ConfigStore.set(req.key, req.value, req.level)
    return ConfigOut(key=req.key, value=ConfigStore.get(req.key), level=req.level.value)


@router.get("/{key}/versions", response_model=list[ConfigVersionOut])
async def list_versions(key: str) -> list[ConfigVersionOut]:
    """获取配置版本历史."""
    return [
        ConfigVersionOut(key=e.key, version=e.version, value=e.value)
        for e in ConfigStore.versions(key)
    ]


@router.post("/{key}/rollback", response_model=ConfigOut)
async def rollback(key: str, version: int) -> ConfigOut:
    """回滚配置到指定版本."""
    entry = ConfigStore.rollback(key, version)
    if entry is None:
        from openbase.core.errors import BaseError, ErrorCode

        raise BaseError(ErrorCode.BIZ_CONFIG_CONFLICT, f"version {version} not found")
    return ConfigOut(key=key, value=ConfigStore.get(key))
