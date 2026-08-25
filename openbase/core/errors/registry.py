"""错误码注册机制：支持动态注册扩展错误码.

来源：DPS engines/error_code_registry.py（注册模式抽取），
适配 openbase 统一错误码体系（ErrorCode 枚举为内置基础码，本模块支持扩展）。
"""

from __future__ import annotations

from typing import Any

from openbase.core.errors.codes import ErrorCode

# 扩展错误码注册表：code -> {message, status_code}
_registry: dict[str, dict[str, Any]] = {}


def register_error_code(
    code: str, message: str, status_code: int = 400
) -> None:
    """注册扩展错误码.

    Args:
        code: 错误码字符串（如 "BIZ_CUSTOM_FAIL"）。
        message: 默认错误消息。
        status_code: 关联 HTTP 状态码。
    """
    _registry[code] = {"message": message, "status_code": status_code}


def get_error_definition(code: str) -> dict[str, Any] | None:
    """查询错误码定义（含内置 ErrorCode 枚举）.

    Args:
        code: 错误码字符串。

    Returns:
        {"message": ..., "status_code": ...}；未注册返回 None。
    """
    # 内置枚举优先
    for member in ErrorCode:
        if member.value == code:
            from openbase.core.errors.codes import ERROR_HTTP_MAP

            return {
                "message": member.name,
                "status_code": ERROR_HTTP_MAP.get(member, 500),
            }
    return _registry.get(code)


def list_error_codes() -> dict[str, dict[str, Any]]:
    """列出全部已注册错误码（内置 + 扩展）."""
    from openbase.core.errors.codes import ERROR_HTTP_MAP

    result: dict[str, dict[str, Any]] = {}
    for member in ErrorCode:
        result[member.value] = {
            "message": member.name,
            "status_code": ERROR_HTTP_MAP.get(member, 500),
        }
    result.update(_registry)
    return result
