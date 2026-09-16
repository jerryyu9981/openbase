"""统一异常基类与 FastAPI 异常处理器."""

from __future__ import annotations

import re
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


_ALLOWED_SPLIT_RE = re.compile(r"\s*(?:,|\bor\b)\s*")

# pydantic ``loc`` 首段为位置类型（取决于参数来源），非业务字段名，须剔除
# （设计 §5 的 ``field`` 示例为纯字段名：``source`` / ``page_size`` / ``q``）
_LOCATION_PREFIXES = frozenset({"query", "body", "path", "header", "cookie"})


def _parse_allowed(expected: object) -> list[str]:
    """从 pydantic ``literal_error`` 的 ``ctx.expected`` 文案提取候选值清单.

    pydantic 仅以人类可读字符串给出期望字面值（如 ``"'a', 'b' or 'c'"``），
    故解析为列表供 ``detail.allowed`` 使用；解析失败返回空列表（调用方不输出该键）。
    """
    if not isinstance(expected, str):
        return []
    return [
        token.strip().strip("'\"")
        for token in _ALLOWED_SPLIT_RE.split(expected)
        if token.strip().strip("'\"")
    ]


def _validation_detail(errors: list[Any]) -> list[dict[str, Any]]:
    """把 pydantic 校验错误归一为**字段式明细**（v1.4.6 Step 4 裁定，DEF-BE-146-006）.

    契约依据：《OpenBase-API接口设计文档-v1.4.6》§5 的 ``detail`` 示例均为字段式
    （``{"field":"source","allowed":[...]}`` / ``{"field":"page_size","max":100}`` /
    ``{"field":"q","max_length":200}``），与同表「导出超限 → ``{matched,limit}``」
    口径一致。

    公开契约**不得暴露第三方库内部键**（``type``/``loc``/``ctx``/``url``）——原实现
    直接回传 ``exc.errors()``，使 pydantic 内部结构成为对外契约的一部分（库升级即可
    改变结构）。此处映射为稳定字段：``field`` / ``msg`` + 约束键 + ``allowed``；
    ``input`` 保留（C-18 响应观测的脱敏输入源，见 tests/test_audit_response_observe.py）。
    """
    items: list[dict[str, Any]] = []
    for error in errors:
        raw_location = list(error.get("loc", ()))
        if raw_location and str(raw_location[0]) in _LOCATION_PREFIXES:
            raw_location = raw_location[1:]
        item: dict[str, Any] = {
            "field": ".".join(str(part) for part in raw_location) or "<request>",
            "msg": error.get("msg", "invalid value"),
        }
        context = error.get("ctx") or {}
        for source_key, target_key in (
            ("max_length", "max_length"),
            ("min_length", "min_length"),
            ("le", "max"),
            ("ge", "min"),
        ):
            if source_key in context:
                item[target_key] = context[source_key]
        if error.get("type") == "literal_error":
            allowed = _parse_allowed(context.get("expected"))
            if allowed:
                item["allowed"] = allowed
        if "input" in error:
            item["input"] = error["input"]
        items.append(item)
    return items


def install_exception_handlers(app: Any) -> None:
    """向 FastAPI 应用注册统一异常处理器.

    覆盖 BaseError 与通用 Exception，保证响应格式统一:
    {code, message, detail, request_id}
    同时向 OpenAPI components.schemas 注册 ErrorResponse 契约（BUG-003 闭环）。

    另：各处理器把错误码写入 ``request.state.error_code``，供审计中间件
    C-15「响应级观测」带出 ``resp_error_code`` 字段（错误归因入口，方案 §11.5）。
    """

    from fastapi import Request
    from fastapi.exceptions import RequestValidationError
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, Field
    from starlette.exceptions import HTTPException as StarletteHTTPException

    class ErrorResponse(BaseModel):
        """OpenBase 统一错误响应契约（SR-003 错误码规范）."""

        code: str = Field(..., description="错误码（ErrorCode 枚举值）")
        message: str = Field(..., description="错误消息")
        detail: Any = Field(None, description="附加详情")
        request_id: str = Field(..., description="请求关联 ID")

    original_openapi = app.openapi  # 保留原始 openapi 引用，避免递归

    def custom_openapi() -> dict:
        """扩展 OpenAPI schema：注册 ErrorResponse 统一错误契约."""
        if getattr(app, "openapi_schema", None):
            return app.openapi_schema
        schema = original_openapi()
        schema.setdefault("components", {}).setdefault("schemas", {})[
            "ErrorResponse"
        ] = ErrorResponse.model_json_schema()
        app.openapi_schema = schema  # type: ignore[attr-defined]
        return schema

    app.openapi = custom_openapi  # type: ignore[method-assign]

    def _mark_error_code(request: Request, code: str) -> None:
        """标注本次请求的错误码（供 C-15 响应观测读取；不改变响应体契约）."""
        request.state.error_code = code

    @app.exception_handler(BaseError)
    async def handle_base_error(request: Request, exc: BaseError) -> JSONResponse:
        _mark_error_code(request, exc.code.value)
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
        """请求参数校验失败 → 统一 400 `PARAM_400`（v1.4.6 Step 4 裁定，DEF-BE-146-006）.

        状态码经 ``ERROR_HTTP_MAP`` 单一来源解析，避免处理器与错误码表漂移；
        ``detail`` 经 ``_validation_detail`` 归一为**字段式明细**（不暴露 pydantic
        内部键），``detail[].input`` 为 C-18 响应观测的脱敏输入源，不得移除。
        """
        code = ErrorCode.PARAM_VALIDATION_ERROR
        _mark_error_code(request, code.value)
        return JSONResponse(
            status_code=ERROR_HTTP_MAP.get(code, 400),
            content={
                "code": code.value,
                "message": "parameter validation error",
                "detail": _validation_detail(exc.errors()),
                "request_id": getattr(request.state, "request_id", _new_request_id()),
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        _mark_error_code(request, str(exc.status_code))
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
        _mark_error_code(request, ErrorCode.SYS_INTERNAL_ERROR.value)
        return JSONResponse(
            status_code=500,
            content={
                "code": ErrorCode.SYS_INTERNAL_ERROR.value,
                "message": "internal server error",
                "detail": str(exc) if getattr(request.app.state, "debug", False) else None,
                "request_id": getattr(request.state, "request_id", _new_request_id()),
            },
        )
