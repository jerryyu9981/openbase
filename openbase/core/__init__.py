"""OpenBase 框架内核.

core 层为强绑定基础：models / db / deps / errors / settings。
所有模块依赖 core，core 不依赖任何模块。
"""

from openbase.core.errors import BaseError, ErrorCode, install_exception_handlers

__all__ = ["BaseError", "ErrorCode", "install_exception_handlers"]
