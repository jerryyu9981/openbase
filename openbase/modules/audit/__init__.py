"""audit 模块：审计中间件 + 健康检查.

来源：OpenLLM backend/app/middleware/audit.py（路径排除/敏感信息脱敏/客户端 IP 提取/
请求体记录模式抽取）+ DPS engines/audit_log_engine.py（审计记录结构化字段），
适配 openbase 统一 request_id 与日志约定。
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Optional  # noqa: F401 - future annotations 字符串注解求值

from fastapi import APIRouter, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from openbase.core.deps.auth import IdentityContext  # noqa: F401 - build_audit_record 类型注解
from openbase.core.mask import digest_of, observe_payload
from openbase.modules.protocol_headers.constants import (
    HEADER_TEST_CASE_ID,
    HEADER_TEST_RUN_ID,
    HEADER_TEST_STEP_ID,
)
from openbase.settings import get_settings

logger = logging.getLogger("openbase.audit")

router = APIRouter(tags=["health"])
api_router = APIRouter(prefix="/api/v1", tags=["audit"])

# 供 init_app 挂载：audit 记录走 /api/v1 前缀，与前端 baseURL 对齐（R-380 走查修复）；
# 根路径 /health 保留在 router 上
extra_routers = [api_router]

# run_id 缺省来源（人工轮次）：请求头优先，其次进程环境变量（运维/测试者启动时注入）
ENV_TEST_RUN_ID = "OPENBASE_TEST_RUN_ID"

# C-4 落库开关（默认开；测试环境由 tests/conftest.py 置 0，避免请求期访问 DB）
ENV_AUDIT_DB_PERSIST = "OPENBASE_AUDIT_DB_PERSIST"

# 审计动作码（C-4：请求级审计行；与 L1 日志事件名一致）
ACTION_API_REQUEST = "api.request"

# 请求级记录通道标识（C-3）：OpenBase 网关编排路径 = B 通道（A 通道为子系统直连，不经网关）
CHANNEL_GATEWAY = "B"

# 响应观测字段（C-15）：结构性字段（恒有）+ 摘要字段（仅开关开启时产出）
RESP_FIELD_NAMES: tuple[str, ...] = (
    "resp_status",
    "resp_bytes",
    "resp_content_type",
    "resp_error_code",
    "resp_digest",
    "resp_summary",
    "resp_keys",
)

# 上游观测字段（C-16）：由 proxy 模块经 ``request.state.upstream_observation`` 注入
UPSTREAM_FIELD_NAMES: tuple[str, ...] = (
    "upstream_system",
    "upstream_status",
    "upstream_content_type",
    "upstream_error_code",
    "upstream_duration_ms",
    "upstream_digest",
    "upstream_body_summary",
    "upstream_keys",
    "upstream_calls",
    "upstream_error",
)

# 落库 detail 保留的**结构性**观测字段（摘要类不入库，避免 detail JSON 膨胀与隐私面扩大）
STRUCTURAL_DETAIL_FIELDS: tuple[str, ...] = (
    "resp_status",
    "resp_bytes",
    "resp_content_type",
    "resp_error_code",
    "resp_digest",
    "upstream_system",
    "upstream_status",
    "upstream_content_type",
    "upstream_error_code",
    "upstream_duration_ms",
    "upstream_digest",
    "upstream_calls",
)

# 不读响应体的内容类型（流式与二进制：读取会破坏透传语义）
_NON_CAPTURABLE_CONTENT_TYPES: tuple[str, ...] = ("text/event-stream",)


def should_capture_body(content_type: str | None) -> bool:
    """是否允许读取响应体以生成摘要（C-15 采集判定）.

    仅 ``application/json`` 且非 SSE 流式时允许读取——流式（``text/event-stream``）
    与二进制/HTML 一律不读，避免破坏透传语义与拖慢大响应。

    Args:
        content_type: 响应 ``Content-Type`` 头（可空）。

    Returns:
        是否允许读取响应体。
    """
    if not content_type:
        return False
    lowered = content_type.lower()
    if any(marker in lowered for marker in _NON_CAPTURABLE_CONTENT_TYPES):
        return False
    return "application/json" in lowered


def build_response_observation(
    *,
    status_code: int,
    content_type: str | None,
    content_length: int | None,
    error_code: str | None,
    payload: bytes | None = None,
    allowlist: Sequence[str] = (),
) -> dict[str, Any]:
    """构造网关响应观测字段（C-15；默认关 → 只产出结构性字段）.

    口径（方案 §11.2）：

    - ``payload is None``（默认关，未读取响应体）→ ``resp_bytes`` 取 ``Content-Length``，
      ``resp_digest`` 为**结构性摘要**（状态码/类型/长度/错误码的组合），无 ``resp_summary``；
    - ``payload`` 非空（开关开启且已读取）→ 以**真实字节数**与**内容摘要**为准，并产出
      经 :func:`openbase.core.mask.mask_sensitive` 脱敏的 ``resp_summary``（超限只留键名清单）。

    Args:
        status_code: 网关返回状态码。
        content_type: 响应 ``Content-Type``。
        content_length: 响应 ``Content-Length``（未读取响应体时的字节数来源）。
        error_code: 统一错误码（``AUTH_401``/``PERM_*`` 等；来自统一异常处理器）。
        payload: 已读取的响应体字节（None 表示未采集）。
        allowlist: 允许保留原值的字段路径清单（``OPENBASE_CAPTURE_FIELD_ALLOWLIST``）。

    Returns:
        仅含非空字段的观测字典（键名见 :data:`RESP_FIELD_NAMES`）。
    """
    if payload is None:
        fields: dict[str, Any] = {
            "resp_status": status_code,
            "resp_bytes": content_length,
            "resp_content_type": content_type,
            "resp_error_code": error_code,
            "resp_digest": digest_of(f"{status_code}|{content_type}|{content_length}|{error_code}"),
        }
    else:
        observed = observe_payload(payload, allowlist=allowlist)
        fields = {
            "resp_status": status_code,
            "resp_bytes": observed["bytes"],
            "resp_content_type": content_type,
            "resp_error_code": error_code,
            "resp_digest": observed["digest"],
        }
        if observed["summary"] is not None:
            fields["resp_summary"] = observed["summary"]
        if observed["keys"]:
            fields["resp_keys"] = observed["keys"]
    return {key: value for key, value in fields.items() if value is not None}


def _parse_content_length(raw: str | None) -> int | None:
    """解析 ``Content-Length``（非法/缺失 → None，不臆造字节数）."""
    if not raw:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _normalize_step_id(raw: str | None) -> int | str | None:
    """步骤序号归一化：纯数字 → int（便于聚合排序），否则保留原字符串。"""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    return int(text) if text.isdigit() else text


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
    def records(
        cls, limit: int = 100, case_id: str | None = None, run_id: str | None = None
    ) -> list[dict]:
        """查询审计记录（调试/管理用，最新在前；C-8 支持按 case_id/run_id 过滤）.

        Args:
            limit: 返回条数上限。
            case_id: 仅返回该用例号的记录（None 表示不过滤）。
            run_id: 仅返回该测试轮次的记录（None 表示不过滤）。

        Returns:
            记录 dict 列表（含 C-3 用例上下文字段 case_id/step_id/run_id/channel；
            C-15/C-16 观测字段 resp_*/upstream_* 存在时一并带出）。
        """
        rows: list[dict] = []
        for record in reversed(cls._records):
            extra = record.extra or {}
            if case_id is not None and extra.get("case_id") != case_id:
                continue
            if run_id is not None and extra.get("run_id") != run_id:
                continue
            row = {
                "request_id": record.request_id,
                "method": record.method,
                "path": record.path,
                "status_code": record.status_code,
                "duration_ms": record.duration_ms,
                "operator_id": record.operator_id,
                "tenant_id": record.tenant_id,
                "ip_address": record.ip_address,
                "error": record.error,
                "case_id": extra.get("case_id"),
                "step_id": extra.get("step_id"),
                "run_id": extra.get("run_id"),
                "channel": extra.get("channel"),
            }
            # C-15/C-16：观测字段仅在存在时带出（默认关 → 无 resp_summary/upstream_body_summary）
            for name in (*RESP_FIELD_NAMES, *UPSTREAM_FIELD_NAMES):
                if name in extra:
                    row[name] = extra[name]
            rows.append(row)
            if len(rows) >= limit:
                break
        return rows


# ---------------------------------------------------------------------------
# 审计落库异步化（TT-056 性能整改）
# ---------------------------------------------------------------------------
#
# 实测依据（``doc/test/evidence/manual/t4-perf-tt056-verdict.json``）：
# ``INSERT+COMMIT`` 6.43 ms/行，代理请求落 2 行 → 请求路径内同步 await ≈12.9 ms，
# 超过方案 §6「P99 增量 <5ms」。
#
# 整改口径：请求路径**只做入队**（µs 级，零 await DB），由 writer 协程
# 按批（默认 ≤50 条）**单次提交**落库；保留「尽力留痕 + 失败降级不阻断 +
# 既有 WARN 文案」语义；进程内队列有界（默认 10000），满则丢弃并 WARN。

DEFAULT_PERSIST_QUEUE_MAXSIZE = 10000
DEFAULT_PERSIST_BATCH_SIZE = 50
DEFAULT_PERSIST_STOP_TIMEOUT = 5.0


async def _write_batch_records(items: list[tuple[str, dict[str, Any]]]) -> int:
    """批量落库（按 ``api_request`` / ``proxy_hop`` 分类，**单会话单次提交**）.

    Args:
        items: ``[(kind, payload)]``；kind ∈ {``api_request``, ``proxy_hop``}。

    Returns:
        成功落库的条目数（失败条目计入队列 ``failed`` 统计，不抛出）。
    """
    if os.getenv(ENV_AUDIT_DB_PERSIST, "1") == "0":
        return 0
    api_items = [payload for kind, payload in items if kind == "api_request"]
    hop_items = [payload for kind, payload in items if kind == "proxy_hop"]
    if not api_items and not hop_items:
        return 0

    from openbase.core.db.session import get_session_factory
    from openbase.core.models import AuditLog

    session = None
    try:
        async with get_session_factory()() as session:
            for payload in api_items:
                operator_text = str(payload.get("operator_id") or "")
                session.add(
                    AuditLog(
                        user_id=int(operator_text) if operator_text.isdigit() else None,
                        tenant_id=None,
                        action=ACTION_API_REQUEST,
                        resource=(payload.get("path") or "")[:128] or None,
                        resource_id=None,
                        ip=payload.get("ip_address"),
                        user_agent=(payload.get("user_agent") or "")[:255] or None,
                        request_id=payload.get("request_id"),
                        detail=payload.get("detail") or {},
                    )
                )
            if hop_items:
                from openbase.modules.protocol_headers.identity_audit import (
                    record_proxy_hop,
                )

                for payload in hop_items:
                    await record_proxy_hop(
                        session,
                        identity=payload["identity"],
                        system=str(payload["system"]),
                        method=payload["method"],
                        path=payload["path"],
                        request_id=payload["request_id"],
                    )
            await session.commit()
        return len(api_items) + len(hop_items)
    except Exception:  # noqa: BLE001 - 审计尽力留痕，不阻断请求
        if api_items:
            logger.warning(
                "audit db persist failed (degraded)",
                extra={"request_id": api_items[0].get("request_id"), "batch_size": len(items)},
            )
        if hop_items:
            logger.warning(
                "proxy outbound audit persist failed (degraded)",
                extra={
                    "system": hop_items[0].get("system"),
                    "request_id": hop_items[0].get("request_id"),
                    "batch_size": len(items),
                },
            )
        if session is not None:
            try:
                await session.rollback()
            except Exception:  # noqa: BLE001
                pass
        raise


class AuditPersistQueue:
    """进程内审计落库队列（请求路径零 await DB + writer 协程批量提交）.

    设计要点：
    - ``submit`` 为**同步**方法（``put_nowait``），请求路径不等待 DB；
    - writer 协程由应用生命周期显式启动（``start_audit_persist_worker``），
      ``stop`` 时**排空在途条目**（避免丢失最近审计行）；
    - 队列有界：满则丢弃最新条目并 WARN（``stats().dropped`` 可观测）；
    - 落库失败：不计入成功数、``failed`` 计数 + WARN（沿用既有降级文案）。
    """

    def __init__(
        self,
        *,
        maxsize: int = DEFAULT_PERSIST_QUEUE_MAXSIZE,
        batch_size: int = DEFAULT_PERSIST_BATCH_SIZE,
    ) -> None:
        self._queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue(maxsize=maxsize)
        self._batch_size = batch_size
        self._task: asyncio.Task[None] | None = None
        self._submitted = 0
        self._persisted = 0
        self._dropped = 0
        self._failed = 0

    # ---- 提交侧（请求路径） ----

    def submit(self, kind: str, payload: dict[str, Any]) -> bool:
        """入队（同步、零 DB）；返回是否成功入队。"""
        if os.getenv(ENV_AUDIT_DB_PERSIST, "1") == "0":
            return False
        try:
            self._queue.put_nowait((kind, payload))
        except asyncio.QueueFull:
            self._dropped += 1
            logger.warning(
                "audit persist queue full; record dropped",
                extra={"queue_size": self._queue.qsize(), "request_id": payload.get("request_id")},
            )
            return False
        self._submitted += 1
        return True

    # ---- writer 侧 ----

    def start(self) -> None:
        """启动 writer 协程（幂等；无运行中的事件循环时静默跳过）。"""
        if self._task is not None and not self._task.done():
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        self._task = loop.create_task(self._run(), name="audit-persist-worker")

    async def stop(self, timeout: float = DEFAULT_PERSIST_STOP_TIMEOUT) -> None:
        """停止 writer 并**排空在途条目**（超时则放弃剩余并登记 dropped）。"""
        task, self._task = self._task, None
        if task is not None and not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        try:
            await asyncio.wait_for(self.drain_once(), timeout=timeout)
        except Exception:  # noqa: BLE001 - 收尾尽力，不阻断关闭
            remaining = self._queue.qsize()
            if remaining:
                self._dropped += remaining
                logger.warning("audit persist drain on shutdown timed out", extra={"pending": remaining})

    async def drain_once(self) -> int:
        """处理当前队列中的全部条目（批次内单次提交）；返回**已处理条目数**（含失败项）.

        成功/失败分别计入 ``stats().persisted`` / ``stats().failed``。
        """
        processed = 0
        while True:
            batch: list[tuple[str, dict[str, Any]]] = []
            while len(batch) < self._batch_size:
                try:
                    batch.append(self._queue.get_nowait())
                except asyncio.QueueEmpty:
                    break
            if not batch:
                break
            processed += len(batch)
            try:
                self._persisted += await _write_batch_records(batch)
            except Exception:  # noqa: BLE001 - 降级已 WARN，跳过该批
                self._failed += len(batch)
        return processed

    async def _run(self) -> None:
        try:
            while True:
                item = await self._queue.get()
                batch = [item]
                while len(batch) < self._batch_size:
                    try:
                        batch.append(self._queue.get_nowait())
                    except asyncio.QueueEmpty:
                        break
                try:
                    self._persisted += await _write_batch_records(batch)
                except Exception:  # noqa: BLE001 - 降级已 WARN，继续消费
                    self._failed += len(batch)
        except asyncio.CancelledError:
            raise

    # ---- 可观测 ----

    def stats(self) -> dict[str, int]:
        """队列统计（提交/落库/丢弃/失败/在途 + writer 状态）."""
        return {
            "submitted": self._submitted,
            "persisted": self._persisted,
            "dropped": self._dropped,
            "failed": self._failed,
            "pending": self._queue.qsize(),
            "writer_running": int(self._task is not None and not self._task.done()),
        }


audit_persist_queue = AuditPersistQueue()


def submit_audit_persist(kind: str, payload: dict[str, Any]) -> bool:
    """模块级提交入口（供中间件调用；同步、零 DB）."""
    return audit_persist_queue.submit(kind, payload)


def start_audit_persist_worker() -> None:
    """应用启动时启动 writer 协程."""
    audit_persist_queue.start()


async def stop_audit_persist_worker() -> None:
    """应用关闭时排空并停止 writer."""
    await audit_persist_queue.stop()


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

    def _extract_test_context(self, request: Request) -> dict[str, Any]:
        """解析人工测试用例上下文（C-3）.

        取值口径（方案 §3.3/§4.2）：``X-Test-Case-Id`` / ``X-Test-Step-Id`` 为非身份头
        （不触发信任链门禁）；``X-Test-Run-Id`` 缺省回退环境变量 ``OPENBASE_TEST_RUN_ID``
        （便于测试者启动时统一注入，无需逐个改前端请求）。

        Args:
            request: 当前请求。

        Returns:
            ``{"case_id": str|None, "step_id": int|str|None, "run_id": str|None}``。
        """
        case_id = request.headers.get(HEADER_TEST_CASE_ID) or None
        step_id = _normalize_step_id(request.headers.get(HEADER_TEST_STEP_ID))
        run_id = request.headers.get(HEADER_TEST_RUN_ID) or os.getenv(ENV_TEST_RUN_ID) or None
        return {
            "case_id": str(case_id) if case_id else None,
            "step_id": step_id,
            "run_id": str(run_id) if run_id else None,
        }

    def _test_context_fields(self, request: Request) -> dict[str, Any]:
        """从 request.state 读回用例上下文并渲染为记录字段（缺省不产生任何字段）."""
        case_id = getattr(request.state, "test_case_id", None)
        step_id = getattr(request.state, "test_step_id", None)
        run_id = getattr(request.state, "test_run_id", None)
        fields: dict[str, Any] = {}
        if case_id:
            fields["case_id"] = case_id
            fields["channel"] = CHANNEL_GATEWAY
        if step_id is not None:
            fields["step_id"] = step_id
        if run_id:
            fields["run_id"] = run_id
        return fields

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

        # C-3：解析人工测试用例上下文（非身份头）→ request.state，供 L1 日志与出站透传复用
        test_context = self._extract_test_context(request)
        request.state.test_case_id = test_context["case_id"]
        request.state.test_step_id = test_context["step_id"]
        request.state.test_run_id = test_context["run_id"]

        start = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception as exc:
            logger.error(
                "request failed",
                extra={"request_id": request_id, "path": request.url.path, "method": request.method},
            )
            audit_record = self._record(
                request, 500, int((time.perf_counter() - start) * 1000), request_id, error=str(exc)
            )
            await self._persist_audit_record(request, audit_record)
            raise

        duration_ms = int((time.perf_counter() - start) * 1000)
        # C-15：响应观测（默认关 → 不读响应体；开启 → 读取 JSON 响应体并脱敏摘要）
        response, observation = await self._observe_response(request, response)
        audit_record = self._record(
            request, response.status_code, duration_ms, request_id, observation=observation
        )
        response.headers["X-Request-Id"] = request_id
        await self._persist_audit_record(request, audit_record)
        await self._persist_outbound_proxy_hop(request, request_id)
        return response

    async def _observe_response(
        self, request: Request, response: Response
    ) -> tuple[Response, dict[str, Any]]:
        """构造响应观测并（仅开关开启时）读取响应体（C-15）.

        红线（方案 §11.2）：开关默认关 → **不读取响应体**（零采集），仅产出结构性字段；
        开关开启且内容类型为 JSON（非 SSE）时读取并重建响应，摘要经 C-18 脱敏。

        Args:
            request: 当前请求（错误码取自统一异常处理器写入的 ``state.error_code``）。
            response: 下游返回的响应。

        Returns:
            ``(可能被重建的响应, 观测字段字典)``。
        """
        settings = get_settings()
        allowlist = tuple(settings.capture_field_allowlist_list)
        content_type = response.headers.get("content-type")
        content_length = _parse_content_length(response.headers.get("content-length"))
        error_code = getattr(request.state, "error_code", None)

        payload: bytes | None = None
        if settings.capture_response_enabled and should_capture_body(content_type):
            response, payload = await self._read_response_body(response)

        observation = build_response_observation(
            status_code=response.status_code,
            content_type=content_type,
            content_length=content_length,
            error_code=error_code,
            payload=payload,
            allowlist=allowlist,
        )
        return response, observation

    async def _read_response_body(self, response: Response) -> tuple[Response, bytes | None]:
        """读取响应体并重建同内容响应（读取失败回退原响应，绝不影响业务）."""
        try:
            chunks = [chunk async for chunk in response.body_iterator]
            raw = b"".join(
                chunk if isinstance(chunk, bytes) else str(chunk).encode("utf-8") for chunk in chunks
            )
        except Exception:  # noqa: BLE001 - 采集失败不影响响应透传
            logger.warning("response body capture failed; fallback to metadata-only observation")
            return response, None

        headers = {
            key: value
            for key, value in response.headers.items()
            if key.lower() not in ("content-length", "content-type")
        }
        rebuilt = Response(
            content=raw,
            status_code=response.status_code,
            headers=headers,
            media_type=response.media_type,
            background=response.background,
        )
        return rebuilt, raw

    async def _persist_audit_record(
        self, request: Request, record: APICallRecord | None
    ) -> None:
        """C-4：审计记录 **入队**（TT-056 整改：请求路径零 await DB）.

        设计口径（方案 §5 批 1 C-4 / D-2=①；v1.6.0 TT-056 性能整改）：请求路径只做
        「构造 payload + 入队」（µs 级），落库由 ``AuditPersistQueue`` 的 writer 协程
        批量提交（``_write_batch_records``）；失败仅 WARN 且回滚，**绝不阻断请求**；
        生产可用 ``OPENBASE_AUDIT_DB_PERSIST=0`` 关闭。

        Args:
            request: 当前请求（取操作者兜底来源）。
            record: 待落库的审计记录；None 表示本次未产生记录（跳过）。
        """
        if record is None or os.getenv(ENV_AUDIT_DB_PERSIST, "1") == "0":
            return

        operator_id = record.operator_id or getattr(request.state, "user_id", None)
        detail: dict[str, Any] = {
            "status_code": record.status_code,
            "duration_ms": record.duration_ms,
            "method": record.method,
            "path": record.path,
            "channel": record.extra.get("channel"),
            "case_id": record.extra.get("case_id"),
            "step_id": record.extra.get("step_id"),
            "run_id": record.extra.get("run_id"),
        }
        identity = record.extra.get("identity")
        if isinstance(identity, dict) and identity.get("principal"):
            detail["identity"] = identity
        if record.error:
            detail["error"] = record.error
        # C-15/C-16：结构性观测字段入库（摘要类不入库，避免 detail 膨胀与隐私面扩大）
        for name in STRUCTURAL_DETAIL_FIELDS:
            value = (record.extra or {}).get(name)
            if value is not None:
                detail[name] = value
        detail = {key: value for key, value in detail.items() if value is not None}

        submit_audit_persist(
            "api_request",
            {
                "request_id": record.request_id,
                "operator_id": operator_id,
                "method": record.method,
                "path": record.path,
                "ip_address": record.ip_address,
                "user_agent": record.user_agent,
                "detail": detail,
            },
        )

    async def _persist_outbound_proxy_hop(
        self, request: Request, request_id: str
    ) -> None:
        """T8（OB-13 §8.3）：proxy 出站审计**入队**（TT-056 整改：请求路径零 await DB）.

        入站请求在出站装配（build_outbound_headers→attach_outbound_identity）时已标注
        ``request.state.outbound_assembled`` 与 ``request.state.outbound_system``；
        本钩子把出站审计项入队，由 writer 协程以同一 request_id 落 ``audit_logs``
        （detail.identity §8.2 全链 proxy_chain），供 OpenBase 侧与子系统侧审计经
        request_id 串联（U4 前置）。

        失败仅 WARN（尽力留痕不阻断响应），参照 K03 白名单审计降级语义。
        """
        if not getattr(request.state, "outbound_assembled", False):
            return
        system = getattr(request.state, "outbound_system", None)
        identity = getattr(request.state, "identity", None)
        if not system or not isinstance(identity, dict) or not identity.get("principal"):
            return
        submit_audit_persist(
            "proxy_hop",
            {
                "identity": identity,
                "system": system,
                "method": request.method,
                "path": request.url.path,
                "request_id": request_id,
            },
        )

    def _observation_fields(
        self, request: Request, observation: dict[str, Any] | None
    ) -> dict[str, Any]:
        """汇总观测字段：网关响应（C-15）+ 上游响应（C-16）.

        上游字段由 proxy 模块经 ``request.state.upstream_observation`` 注入（同一请求内
        多次上游调用时取最近一次，并累计 ``upstream_calls``），使「网关 → 上游」两级
        响应落在**同一条** L1 记录上（错误归因不需要跨行 join）。

        Args:
            request: 当前请求。
            observation: C-15 网关侧观测字段（可为空）。

        Returns:
            合并后的观测字段字典。
        """
        fields: dict[str, Any] = dict(observation or {})
        upstream = getattr(request.state, "upstream_observation", None)
        if isinstance(upstream, dict):
            fields.update(upstream)
        return fields

    def _record(
        self,
        request: Request,
        status_code: int,
        duration_ms: int,
        request_id: str,
        error: str | None = None,
        observation: dict[str, Any] | None = None,
    ) -> APICallRecord | None:
        """记录审计条目（异步语义：不阻塞主请求）+ L1 请求级结构化日志（C-3/C-15/C-16）.

        Args:
            request: 当前请求。
            status_code: 网关返回状态码。
            duration_ms: 网关耗时毫秒。
            request_id: 请求 ID。
            error: 异常文本（可空）。
            observation: 响应观测字段（C-15/C-16；默认关时仅含结构性字段）。

        Returns:
            已入内存缓冲的审计记录；记录失败（异常吞掉）时返回 None。
        """
        try:
            user_id, user_name = self._extract_user_info(request)
            # P2-1 §8.2/§8.3（批次 2/T5 OB-6）：request.state.identity（认证依赖/
            # 出站装配写入）并入审计记录 extra.identity——agent/user 主体审计贯穿，
            # principal.subject_type=agent 可由 detail/extra 直接识别（T8 全链沿用）。
            identity = getattr(request.state, "identity", None)
            extra = {"query_params": str(request.query_params), "safe_headers": self._safe_headers(request)}
            if isinstance(identity, dict) and identity.get("principal"):
                extra["identity"] = identity
            # C-3：用例上下文（case_id/step_id/run_id/channel）并入 extra，供 C-4 落库与 C-8 查询
            extra.update(self._test_context_fields(request))
            # C-15/C-16：响应观测字段并入 extra（默认关 → 无摘要字段，零合规暴露）
            extra.update(self._observation_fields(request, observation))
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
            self._emit_request_log(
                request, status_code, duration_ms, request_id, user_id, error, observation
            )
            return record
        except Exception:  # noqa: BLE001
            logger.exception("failed to record audit log", extra={"request_id": request_id})
            return None

    def _emit_request_log(
        self,
        request: Request,
        status_code: int,
        duration_ms: int,
        request_id: str,
        operator_id: str | None,
        error: str | None = None,
        observation: dict[str, Any] | None = None,
    ) -> None:
        """L1 请求级结构化日志（C-3 + C-15/C-16；字段口径 = 方案 §4.1 必填 + §4.2 场景扩展）.

        经 root logger 输出：C-1 装配后同时落 JSONL 文件（``logs/<service>/…jsonl``）
        与控制台（由 C-6 重定向采集）；未装配时为空操作（测试环境零副作用）。

        说明：``error_code``（AUTH/PERM/… 前缀码）由统一异常处理器写入
        ``request.state.error_code``，经 C-15 观测字段 ``resp_error_code`` 带出。

        Args:
            request: 当前请求。
            status_code: 网关返回状态码。
            duration_ms: 网关耗时毫秒。
            request_id: 请求 ID。
            operator_id: 操作者 ID。
            error: 异常文本（可空）。
            observation: 响应观测字段（可空）。
        """
        payload: dict[str, Any] = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "actor": operator_id,
            "tenant": self._extract_tenant(request),
        }
        payload.update(self._test_context_fields(request))
        payload.update(self._observation_fields(request, observation))
        if error:
            payload["error"] = error
        logger.info("api.request", extra=payload)

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
async def audit_records(
    limit: int = 100, case_id: str | None = None, run_id: str | None = None
) -> dict:
    """查询审计记录（调试/管理用；C-8 支持按 case_id/run_id 过滤）.

    Args:
        limit: 返回条数上限。
        case_id: 人工测试用例号过滤（None = 不过滤）。
        run_id: 人工测试轮次过滤（None = 不过滤）。

    Returns:
        ``{"records": [...]}``（含 case_id/step_id/run_id/channel 字段）。
    """
    return {"records": AuditService.records(limit=limit, case_id=case_id, run_id=run_id)}

async def query_audit_logs_by_case(
    session: Any,
    *,
    case_id: str | None = None,
    run_id: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """按用例上下文查询 ``audit_logs``（C-4：跨重启持久化检索口）.

    过滤走 SQLAlchemy JSON 路径表达式（``detail->>'case_id'``），由方言编译为
    SQLite 的 ``JSON_EXTRACT`` / PostgreSQL 的 ``->>``，**参数化查询**，不拼接 SQL。

    Args:
        session: 异步会话。
        case_id: 用例号过滤（None = 不过滤）。
        run_id: 测试轮次过滤（None = 不过滤）。
        limit: 返回条数上限（按 id 倒序）。

    Returns:
        ``[{"id", "request_id", "action", "detail", "created_at"}]``。
    """
    from sqlalchemy import select

    from openbase.core.models import AuditLog

    statement = select(AuditLog).where(AuditLog.action == ACTION_API_REQUEST)
    if case_id is not None:
        statement = statement.where(AuditLog.detail["case_id"].as_string() == case_id)
    if run_id is not None:
        statement = statement.where(AuditLog.detail["run_id"].as_string() == run_id)
    statement = statement.order_by(AuditLog.id.desc()).limit(limit)

    result = await session.execute(statement)
    return [
        {
            "id": row.id,
            "request_id": row.request_id,
            "action": row.action,
            "detail": row.detail or {},
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in result.scalars().all()
    ]


__version__ = "1.1.0"
