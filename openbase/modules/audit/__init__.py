"""audit 模块：审计中间件 + 健康检查.

来源：OpenLLM backend/app/middleware/audit.py（路径排除/敏感信息脱敏/客户端 IP 提取/
请求体记录模式抽取）+ DPS engines/audit_log_engine.py（审计记录结构化字段），
适配 openbase 统一 request_id 与日志约定。
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional  # noqa: F401 - future annotations 字符串注解求值

from fastapi import APIRouter, Request
from starlette.middleware.base import BaseHTTPMiddleware

from openbase.core.deps.auth import IdentityContext  # noqa: F401 - build_audit_record 类型注解

logger = logging.getLogger("openbase.audit")

router = APIRouter(tags=["health"])
api_router = APIRouter(prefix="/api/v1", tags=["audit"])

# 供 init_app 挂载：audit 记录走 /api/v1 前缀，与前端 baseURL 对齐（R-380 走查修复）；
# 根路径 /health 保留在 router 上
extra_routers = [api_router]


@dataclass
class APICallRecord:
    """API 调用审计记录（来源: OpenLLM AuditService.APICallRecord 模式）.

    v1.0.0 最小实现：内存环形缓冲；生产接数据库 audit_logs 表。
    """

    method: str
    path: str
    status_code: int
    duration_ms: int
    request_id: str
    operator_id: str | None = None
    operator_name: str | None = None
    tenant_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    request_body: str | None = None
    error: str | None = None
    extra: dict = field(default_factory=dict)


def build_audit_record(
    method: str,
    path: str,
    status_code: int,
    duration_ms: int,
    request_id: str,
    identity: IdentityContext | None = None,
    operator_name: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    error: str | None = None,
) -> APICallRecord:
    """构造审计记录（v1.4.1 R-370：绑定四维身份上下文）.

    从 IdentityContext 注入 tenant_id 与 operator_id（user_id 转字符串），
    支撑跨租户审计追溯（完整方案 2.7 安全边界④）。

    Args:
        method: HTTP 方法。
        path: 请求路径。
        status_code: 响应状态码。
        duration_ms: 耗时毫秒。
        request_id: 请求 ID。
        identity: 四维身份上下文（可空）。
        operator_name: 操作者名称（可空）。
        ip_address: 客户端 IP（可空）。
        user_agent: 客户端 UA（可空）。
        error: 错误信息（可空）。

    Returns:
        APICallRecord。
    """
    return APICallRecord(
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=duration_ms,
        request_id=request_id,
        operator_id=str(identity.user_id) if identity and identity.user_id is not None else None,
        operator_name=operator_name,
        tenant_id=identity.tenant_id if identity else None,
        ip_address=ip_address,
        user_agent=user_agent,
        error=error,
        extra={"team_id": identity.team_id, "agent_id": identity.agent_id} if identity else {},
    )


class AuditService:
    """审计日志服务（来源: DPS engines/audit_log_engine.py 结构化记录模式）."""

    # 内存环形缓冲（保留最近 5000 条；生产接数据库）
    MAX_RECORDS = 5000
    _records: list[APICallRecord] = []

    @classmethod
    def record_api_call(cls, record: APICallRecord) -> None:
        """记录审计条目（超限时淘汰最旧）."""
        cls._records.append(record)
        if len(cls._records) > cls.MAX_RECORDS:
            del cls._records[: len(cls._records) - cls.MAX_RECORDS]

    @classmethod
    def records(cls, limit: int = 100) -> list[dict]:
        """查询审计记录（调试/管理用，最新在前）."""
        return [
            {
                "request_id": r.request_id,
                "method": r.method,
                "path": r.path,
                "status_code": r.status_code,
                "duration_ms": r.duration_ms,
                "operator_id": r.operator_id,
                "tenant_id": r.tenant_id,
                "ip_address": r.ip_address,
                "error": r.error,
            }
            for r in reversed(cls._records[-limit:])
        ]


class AuditMiddleware(BaseHTTPMiddleware):
    """审计中间件.

    为每个请求生成 request_id、记录耗时与状态码，
    自动记录 API 调用审计日志（排除健康检查/文档等路径，脱敏敏感头）。
    来源：OpenLLM backend/app/middleware/audit.py。
    """

    # 排除记录的路径（健康检查、文档、静态资源等）
    EXCLUDED_PATHS: set[str] = {
        "/health",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/static",
        "/favicon.ico",
    }

    # 敏感请求头（不记录）
    SENSITIVE_HEADERS = {
        "authorization",
        "cookie",
        "x-api-key",
        "x-auth-token",
        "x-csrf-token",
    }

    # 敏感路径（记录但脱敏请求体）
    SENSITIVE_PATHS = {"/api/v1/auth/login", "/api/v1/auth/refresh"}

    # 请求体记录大小上限
    MAX_BODY_SIZE = 1024 * 1024  # 1MB

    def _should_skip_logging(self, request: Request) -> bool:
        """是否跳过记录（精确 + 前缀匹配）."""
        path = request.url.path
        if path in self.EXCLUDED_PATHS:
            return True
        for excluded in self.EXCLUDED_PATHS:
            if path.startswith(excluded):
                return True
        return False

    def _extract_client_ip(self, request: Request) -> str:
        """提取客户端 IP（支持 X-Forwarded-For / X-Real-IP）. """
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        if request.client is not None and request.client.host:
            return request.client.host
        return "unknown"

    def _extract_user_info(self, request: Request) -> tuple[str | None, str | None]:
        """从请求 state 提取用户信息（由认证中间件设置）."""
        user_id = getattr(request.state, "user_id", None)
        user_name = getattr(request.state, "user_name", None)
        return user_id, user_name

    def _extract_tenant(self, request: Request) -> str | None:
        """提取租户上下文."""
        return getattr(request.state, "tenant_id", None)

    async def _read_request_body(self, request: Request) -> str:
        """读取请求体（限 1MB，二进制返回标记）."""
        content_type = request.headers.get("Content-Type", "")
        if not any(ct in content_type for ct in ("application/json", "application/x-www-form-urlencoded")):
            return ""
        try:
            body = await request.body()
            if len(body) > self.MAX_BODY_SIZE:
                return f"[Body too large: {len(body)} bytes]"
            return body.decode("utf-8")
        except UnicodeDecodeError:
            return "[Binary content]"
        except Exception:  # noqa: BLE001
            return ""

    def _safe_headers(self, request: Request) -> dict:
        """提取请求头（过滤敏感字段）."""
        return {
            k: v for k, v in request.headers.items()
            if k.lower() not in self.SENSITIVE_HEADERS
        }

    async def dispatch(self, request: Request, call_next):
        # 排除健康检查/文档等路径（来源: OpenLLM AuditMiddleware）
        if self._should_skip_logging(request):
            return await call_next(request)

        request_id = getattr(request.state, "request_id", f"req-{uuid.uuid4().hex[:12]}")
        request.state.request_id = request_id
        start = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception as exc:
            logger.error(
                "request failed",
                extra={"request_id": request_id, "path": request.url.path, "method": request.method},
            )
            self._record(request, 500, int((time.perf_counter() - start) * 1000), request_id, error=str(exc))
            raise

        duration_ms = int((time.perf_counter() - start) * 1000)
        self._record(request, response.status_code, duration_ms, request_id)
        response.headers["X-Request-Id"] = request_id
        return response

    def _record(self, request: Request, status_code: int, duration_ms: int, request_id: str, error: str | None = None) -> None:
        """记录审计条目（异步语义：不阻塞主请求）. """
        try:
            user_id, user_name = self._extract_user_info(request)
            # P2-1 §8.2/§8.3（批次 2/T5 OB-6）：request.state.identity（认证依赖/
            # 出站装配写入）并入审计记录 extra.identity——agent/user 主体审计贯穿，
            # principal.subject_type=agent 可由 detail/extra 直接识别（T8 全链沿用）。
            identity = getattr(request.state, "identity", None)
            extra = {"query_params": str(request.query_params), "safe_headers": self._safe_headers(request)}
            if isinstance(identity, dict) and identity.get("principal"):
                extra["identity"] = identity
            record = APICallRecord(
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                duration_ms=duration_ms,
                request_id=request_id,
                operator_id=user_id,
                operator_name=user_name,
                tenant_id=self._extract_tenant(request),
                ip_address=self._extract_client_ip(request),
                user_agent=request.headers.get("User-Agent"),
                request_body=self._sanitize_body(request),
                error=error,
                extra=extra,
            )
            AuditService.record_api_call(record)
        except Exception:  # noqa: BLE001
            logger.exception("failed to record audit log", extra={"request_id": request_id})

    def _sanitize_body(self, request: Request) -> str | None:
        """敏感路径请求体脱敏（不记录明文密码等）. """
        if request.url.path in self.SENSITIVE_PATHS:
            return "[sensitive]"
        return ""


@router.get("/health")
async def health() -> dict:
    """健康检查接口.

    Returns:
        {"status": "ok"}；服务存活即返回 200。
    """
    return {"status": "ok"}


@api_router.get("/audit/records")
async def audit_records(limit: int = 100) -> dict:
    """查询审计记录（调试/管理用）."""
    return {"records": AuditService.records(limit=limit)}

__version__ = "1.1.0"
