"""统一异常模块：BaseError + ErrorCode + 异常处理器 + 错误码注册."""

from openbase.core.errors.base import BaseError, install_exception_handlers
from openbase.core.errors.codes import ERROR_HTTP_MAP, ErrorCode
from openbase.core.errors.registry import (
    get_error_definition,
    list_error_codes,
    register_error_code,
)

__all__ = [
    "BaseError",
    "ErrorCode",
    "ERROR_HTTP_MAP",
    "install_exception_handlers",
    "register_error_code",
    "get_error_definition",
    "list_error_codes",
]
