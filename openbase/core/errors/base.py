"""统一异常基类与 FastAPI 异常处理器."""

from __future__ import annotations

import uuid
from typing import Any

from openbase.core.errors.codes import ERROR_HTTP_MAP, ErrorCode


class BaseError(Exception):
    """OpenBase 统一异常基类.

    Attributes:
        code: 错误码（ErrorCode 枚举值）。
        message: 错误消息。
        detail: 附加详情（可选）。
        status_code: HTTP 状态码（由错误码映射）。
    """

    def __init__(
        self,
        code: ErrorCode = ErrorCode.SYS_INTERNAL_ERROR,
        message: str = "internal error",
        detail: Any = None,
    ) -> None:
        self.code = code
        self.message = message
        self.detail = detail
        self.status_code = ERROR_HTTP_MAP.get(code, 500)
        super().__init__(message)


def _new_request_id() -> str:
    return f"req-{uuid.uuid4().hex[:12]}"


def install_exception_handlers(app: Any) -> None:
    """向 FastAPI 应用注册统一异常处理器.

    覆盖 BaseError 与通用 Exception，保证响应格式统一:
    {code, message, detail, request_id}
    """

    from fastapi import Request
    from fastapi.exceptions import RequestValidationError
    from fastapi.responses import JSONResponse
    from starlette.exceptions import HTTPException as StarletteHTTPException

    @app.exception_handler(BaseError)
    async def handle_base_error(request: Request, exc: BaseError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code.value,
                "message": exc.message,
                "detail": exc.detail,
                "request_id": getattr(request.state, "request_id", _new_request_id()),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "code": ErrorCode.PARAM_VALIDATION_ERROR.value,
                "message": "parameter validation error",
                "detail": exc.errors(),
                "request_id": getattr(request.state, "request_id", _new_request_id()),
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": str(exc.status_code),
                "message": exc.detail,
                "detail": None,
                "request_id": getattr(request.state, "request_id", _new_request_id()),
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(
        request: Request, exc: Exception
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "code": ErrorCode.SYS_INTERNAL_ERROR.value,
                "message": "internal server error",
                "detail": str(exc) if getattr(request.app.state, "debug", False) else None,
                "request_id": getattr(request.state, "request_id", _new_request_id()),
            },
        )
