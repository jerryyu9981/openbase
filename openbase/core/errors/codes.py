"""统一错误码定义."""

from enum import Enum


class ErrorCode(str, Enum):
    """OpenBase 统一错误码.

    分段规则：AUTH_* 鉴权授权 / PARAM_* 参数 / BIZ_* 业务 / SYS_* 系统 / STORAGE_* 存储。
    """

    # ---- 成功 ----
    OK = "0"

    # ---- 鉴权/授权 ----
    AUTH_UNAUTHORIZED = "AUTH_401"
    AUTH_FORBIDDEN = "AUTH_403"
    AUTH_TOKEN_EXPIRED = "AUTH_401_EXPIRED"
    AUTH_TOKEN_INVALID = "AUTH_401_INVALID"
    AUTH_RATE_LIMITED = "AUTH_429"
    AUTH_USER_DISABLED = "AUTH_401_DISABLED"

    # ---- 参数 ----
    PARAM_VALIDATION_ERROR = "PARAM_422"
    PARAM_NOT_FOUND = "PARAM_404"

    # ---- 业务 ----
    BIZ_TENANT_EXISTS = "BIZ_TENANT_EXISTS"
    BIZ_TENANT_NOT_FOUND = "BIZ_TENANT_NOT_FOUND"
    BIZ_USER_EXISTS = "BIZ_USER_EXISTS"
    BIZ_ROLE_IN_USE = "BIZ_ROLE_IN_USE"
    BIZ_CONFIG_CONFLICT = "BIZ_CONFIG_CONFLICT"
    BIZ_NOT_FOUND = "BIZ_404"
    BIZ_MODEL_QUOTA = "BIZ_MODEL_QUOTA"

    # ---- 存储 ----
    STORAGE_FILE_NOT_FOUND = "STORAGE_404"

    # ---- 系统 ----
    SYS_INTERNAL_ERROR = "SYS_500"
    SYS_UPSTREAM_ERROR = "SYS_502"


# HTTP 状态码映射
ERROR_HTTP_MAP: dict[ErrorCode, int] = {
    ErrorCode.AUTH_UNAUTHORIZED: 401,
    ErrorCode.AUTH_FORBIDDEN: 403,
    ErrorCode.AUTH_TOKEN_EXPIRED: 401,
    ErrorCode.AUTH_TOKEN_INVALID: 401,
    ErrorCode.AUTH_RATE_LIMITED: 429,
    ErrorCode.AUTH_USER_DISABLED: 401,
    ErrorCode.PARAM_VALIDATION_ERROR: 422,
    ErrorCode.PARAM_NOT_FOUND: 404,
    ErrorCode.BIZ_TENANT_EXISTS: 409,
    ErrorCode.BIZ_TENANT_NOT_FOUND: 404,
    ErrorCode.BIZ_USER_EXISTS: 409,
    ErrorCode.BIZ_ROLE_IN_USE: 409,
    ErrorCode.BIZ_CONFIG_CONFLICT: 409,
    ErrorCode.BIZ_NOT_FOUND: 404,
    ErrorCode.BIZ_MODEL_QUOTA: 402,
    ErrorCode.STORAGE_FILE_NOT_FOUND: 404,
    ErrorCode.SYS_INTERNAL_ERROR: 500,
    ErrorCode.SYS_UPSTREAM_ERROR: 502,
}
