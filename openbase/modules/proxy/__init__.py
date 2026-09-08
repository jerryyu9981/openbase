"""proxy 模块：四系统特色 API 代理（v1.2.0）.

统一前端只与 openbase 后端通信；本模块提供 /api/v1/proxy/{system}/{path}
代理转发到四系统（OpenLLM/OpenRAG/OpenMemory/DPS）原生 API。
后端校验 JWT 后按路由表转发，响应统一包装为 ErrorResponse 契约。

system 映射与 base_url 可通过 config 模块配置覆盖（默认指向 Dev 示例端口）。
"""

from __future__ import annotations

import logging
import uuid

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from openbase.core.deps.auth import get_proxy_identity
from openbase.core.errors import BaseError, ErrorCode
from openbase.core.models import AuditLog
from openbase.modules.protocol_headers import TARGET_SYSTEM_GENERIC, build_outbound_headers
from openbase.modules.proxy.memory_proxy import router as memory_proxy_router

logger = logging.getLogger("openbase.proxy")

router = APIRouter(prefix="/api/v1/proxy", tags=["proxy"])

# v1.4.2 R-378：OpenMemory 双层认证转发路由（/api/v1/memory-proxy/*）
# 通过 extra_routers 由 init_app 单独挂载（避免 include_router 前缀嵌套）
extra_routers = [memory_proxy_router]

__all__ = ["PROXY_SYSTEMS", "router", "extra_routers"]

# P2（DPS 对接任务书）：dps base_url 与 dps-proxy 收敛到同一事实源 settings.dps_upstream_base
# （默认 8000 = DPS 源码默认；编排经 OPENBASE_DPS_UPSTREAM_BASE 覆盖为 8030）。
from openbase.settings import get_settings  # noqa: E402

_settings = get_settings()

# 四系统代理路由表（base_url 可由 config 模块覆盖；此处为 Dev 默认）
PROXY_SYSTEMS: dict[str, dict] = {
    "openllm": {"base_url": "http://127.0.0.1:8001", "timeout": 10.0},
    "openrag": {"base_url": "http://127.0.0.1:8010", "timeout": 10.0},
    "openmemory": {"base_url": "http://127.0.0.1:8020", "timeout": 10.0},
    "dps": {"base_url": _settings.dps_upstream_base, "timeout": 10.0},
}


def _resolve_base_url(system: str) -> str:
    """解析系统 base_url（优先 config 模块配置，其次默认表）.

    配置键：proxy.{system}.base_url（system 级）。
    """
    try:
        from openbase.modules.config import ConfigStore

        value = ConfigStore.get(f"proxy.{system}.base_url")
        if value:
            return str(value)
    except Exception:  # noqa: BLE001
        pass
    return PROXY_SYSTEMS[system]["base_url"]


def _timeout(system: str) -> float:
    return PROXY_SYSTEMS[system]["timeout"]


# K03 D-V6：匿名业务写（ob_k_ 服务 Key 写路径）白名单外的 HTTP 方法
_WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def _is_service_key_identity(identity: dict) -> bool:
    """判定 /proxy 通道认证结果是否为 ob_k_ 服务 Key（含 scope/name，无主体 id）."""
    return bool(identity) and "scope" in identity and "id" not in identity


def _resolve_service_account_subject(identity: dict) -> dict | None:
    """ob_k_ 服务 Key → 服务账号主体上下文（P2-1 §3.7 例 3 / §5.2 D-V6）.

    服务 Key 凭据（{name, scope}）命中 settings.service_account_subject_map（按 name
    精确 / name_prefix 前缀）→ 返回可装配出站身份头的服务账号主体上下文
    （X-User-ID=subject_id、X-Tenant-ID/X-Org-ID=tenant_code、X-User-Role=role）；
    未绑定/未命中 → None（出站维持仅来源标注，不构造伪主体身份头）。

    Args:
        identity: get_proxy_identity 服务 Key 凭据 dict。

    Returns:
        服务账号主体上下文 dict；无绑定返回 None。
    """
    if not _is_service_key_identity(identity):
        return None
    name = str(identity.get("name") or "")
    settings = get_settings()
    for entry in settings.parse_service_account_subject_map():
        subject_id = entry.get("subject_id")
        tenant_code = entry.get("tenant_code")
        if subject_id is None or not tenant_code:
            continue
        exact_name = entry.get("name")
        name_prefix = entry.get("name_prefix")
        matched = bool(
            (exact_name and name == str(exact_name))
            or (name_prefix and name.startswith(str(name_prefix)))
        )
        if not matched:
            continue
        return {
            "id": subject_id,
            "username": name or str(exact_name or ""),
            "subject_type": "user",
            "tenant_code": str(tenant_code),
            "org_id": str(tenant_code),
            "role": str(entry.get("role") or "viewer"),
            "permissions": [],
            "auth_method": "service-key",
        }
    return None


def _k03_bypass_matches(entry: dict, *, system: str, method: str, path: str) -> bool:
    """K03 过渡豁免白名单条目匹配（system+method+path_pattern 三者命中）."""
    if entry.get("system") not in (None, "*", system):
        return False
    if entry.get("method") not in (None, "*", method):
        return False
    path_pattern = entry.get("path_pattern")
    if not path_pattern or path_pattern in ("*", "/"):
        return True
    # path 形如 "chat"（路由 {path:path} 捕获相对路径），规范化为带前导 / 比对
    canonical_path = "/" + str(path).lstrip("/")
    pattern = "/" + str(path_pattern).lstrip("/")
    return (
        canonical_path == pattern
        or canonical_path.startswith(pattern)
        or canonical_path.endswith(pattern)
    )


async def _record_k03_bypass_audit(
    session: object,
    *,
    entry: dict,
    system: str,
    method: str,
    path: str,
    request_id: str | None,
) -> None:
    """白名单内匿名写放行逐条审计（action=proxy.bypass_write，detail 含 id/reason）.

    DB 不可达/不可写时降级 WARN（放行不因审计失败而阻断——过渡期语义），
    保证业务可继续而审计尽力留痕。
    """
    try:
        detail = {
            "id": entry.get("id"),
            "system": system,
            "method": method,
            "path": path,
            "reason": entry.get("reason"),
            "owner": entry.get("owner"),
            "audit": entry.get("audit"),
        }
        record = AuditLog(
            user_id=None,
            tenant_id=None,
            action="proxy.bypass_write",
            resource=system,
            resource_id=str(entry.get("id") or "")[:64] or None,
            request_id=request_id or f"req-{uuid.uuid4().hex[:12]}",
            detail=detail,
        )
        session.add(record)
        await session.commit()
        logger.info(
            "k03 bypass write audited",
            extra={"id": entry.get("id"), "system": system, "path": path},
        )
    except Exception:  # noqa: BLE001 - 审计尽力留痕，不阻断放行
        logger.warning(
            "k03 bypass audit write failed (degraded)",
            extra={"system": system, "path": path},
        )
        try:
            await session.rollback()
        except Exception:  # noqa: BLE001
            pass


@router.api_route("/{system}/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy(
    system: str,
    path: str,
    request: Request,
    identity: dict = Depends(get_proxy_identity),
) -> JSONResponse:
    """代理转发：JWT 优先 + 服务 Key 回退双通道认证（R-367 AC-367-2）后转发四系统原生 API.

    P2-1 T1/K01（§3.5 通用 proxy 行）：出站身份头经 ``build_outbound_headers`` 唯一
    装配——JWT 通道注入主体身份头；ob_k_ 服务 Key 通道注入 X-Proxy-Source/X-Request-Id
    （服务账号主体映射随批次 2/T5）。P2-1 T2 D-V6（K03）：ob_k_ 匿名**业务写**
    fail-closed——白名单（settings.k03_bypass_whitelist）内放行且逐条审计，
    白名单外一律 403 ``PERM_SERVICE_KEY_WRITE_DENIED``。

    支持路径参数透传；上游不可达时返回统一 SYS_502 错误包装。
    """
    if system not in PROXY_SYSTEMS:
        raise BaseError(ErrorCode.PARAM_NOT_FOUND, f"unknown proxy system: {system}")

    method = request.method
    settings = get_settings()
    is_service_key = _is_service_key_identity(identity)
    # K03 D-V6：未登记 ob_k_ 业务写 → 403 PERM_SERVICE_KEY_WRITE_DENIED
    if is_service_key and method in _WRITE_METHODS:
        bypass_entry = next(
            (
                entry
                for entry in settings.parse_k03_bypass_whitelist()
                if _k03_bypass_matches(entry, system=system, method=method, path=path)
            ),
            None,
        )
        if bypass_entry is None:
            logger.warning(
                "anonymous service-key write denied (k03)",
                extra={"system": system, "method": method, "path": path},
            )
            raise BaseError(
                ErrorCode.PERM_SERVICE_KEY_WRITE_DENIED,
                "anonymous service-key business write denied; "
                "register in k03_bypass_whitelist or migrate to sk-agent-* service account",
                detail={"system": system, "method": method, "path": path},
            )
        # 白名单内放行 + 逐条审计
        from openbase.core.db.session import get_session_factory

        async with get_session_factory()() as bypass_session:
            await _record_k03_bypass_audit(
                bypass_session,
                entry=bypass_entry,
                system=system,
                method=method,
                path=path,
                request_id=getattr(request.state, "request_id", None),
            )

    base_url = _resolve_base_url(system)
    target_url = f"{base_url.rstrip('/')}/{path}"
    headers = {
        "Content-Type": request.headers.get("Content-Type", "application/json"),
        "Accept": request.headers.get("Accept", "application/json"),
    }
    # 出站身份头唯一装配点（JWT 通道 = 主体身份；ob_k_ 通道 = 服务账号映射或仅来源标注）
    # P2-1 §3.7 例 3 / §5.2 D-V6：服务 Key 命中 service_account_subject_map → 以映射
    # 服务账号主体上下文补头；未绑定服务 Key → None（维持来源标注，不构造伪主体头）。
    if is_service_key:
        outbound_user = _resolve_service_account_subject(identity)
    else:
        outbound_user = identity
    headers = build_outbound_headers(
        request,
        outbound_user,
        target_system=TARGET_SYSTEM_GENERIC,
        extra_headers=headers,
        enforce_org_alias=settings.enforce_org_alias,
    )
    body = await request.body() if method in ("POST", "PUT", "PATCH") else None

    try:
        async with httpx.AsyncClient(timeout=_timeout(system)) as client:
            upstream = await client.request(
                method, target_url, headers=headers, content=body,
            )
    except httpx.HTTPError as exc:
        logger.warning("proxy upstream unreachable", extra={"system": system, "path": path, "error": str(exc)})
        raise BaseError(ErrorCode.SYS_UPSTREAM_ERROR, f"upstream {system} unreachable") from exc

    # 上游 402（模型提供商余额不足）→ 统一包装 BIZ_MODEL_QUOTA，不暴露上游原始响应
    if upstream.status_code == 402:
        logger.info(
            "proxy upstream payment required",
            extra={"system": system, "path": path, "status": upstream.status_code},
        )
        return JSONResponse(
            status_code=402,
            content={
                "code": ErrorCode.BIZ_MODEL_QUOTA.value,
                "message": "模型服务余额不足，请联系管理员充值",
                "detail": "upstream payment required",
                "request_id": getattr(request.state, "request_id", ""),
            },
        )

    # 透传上游状态码与数据（响应体保持 JSON 透传，错误已由上游契约保证）
    try:
        payload = upstream.json()
    except ValueError:
        payload = {"raw": upstream.text[:2000]}
    return JSONResponse(status_code=upstream.status_code, content=payload)


__version__ = "1.4.0"
