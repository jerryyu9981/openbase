"""出站/请求审计身份块构建（P2-1 §8.2 identity schema，批次 2/T5 供 OB-6 agent 审计）.

设计 §8.2 `audit_identity` v1（audit_logs.detail / APICallRecord.extra 共用形态）：

    identity = {
        "principal":  {subject_id, subject_type, tenant_code, role, auth_method},
        "delegated":   {...} | None,
        "effective":   {subject_id, subject_type, tenant_code, role},
        "proxy_source": "openbase-*",
        "proxy_chain": [...] | None,
        "request_id":  "req-...",
        "org_alias":   tenant_code,
    }

本模块为**纯 schema/落库辅助**：不引入模块路由、不注册 enable_module；
批次 3/T8（OB-13 审计贯穿）接线完整链路：
- :func:`build_identity_detail`：统一主体 dict → §8.2 identity 块（纯函数）；
- :func:`attach_outbound_identity`：出站装配（build_outbound_headers）写入
  ``request.state.identity``（AuditMiddleware._record 消费）并标注
  ``request.state.outbound_assembled``（T8：AuditMiddleware 响应后经
  :func:`record_proxy_hop` 落 DB 审计，action=proxy.outbound，同 request_id）；
- :func:`enqueue_proxy_outbound_audit`：proxy 出站审计落库（action=proxy.outbound），
  供 proxy 族/测试以同 request_id 串联审计；
- :func:`record_proxy_hop`：T8 DB 出站钩子（每次出站装配落 proxy_chain 全链）；
- :func:`build_identity_section`：lifecycle/delegation/purge 既有 DB 审计 detail
  并入 §8.2 identity 块结构（principal+delegated+effective+proxy_source+
  proxy_chain+request_id，T8-1）。
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from openbase.core.models import AuditLog
from openbase.modules.protocol_headers.constants import SOURCE_BY_TARGET_SYSTEM

logger = logging.getLogger("openbase.protocol_headers.identity_audit")

__all__ = [
    "ACTION_PROXY_OUTBOUND",
    "attach_outbound_identity",
    "build_effective_block",
    "build_identity_detail",
    "build_identity_section",
    "build_principal_block",
    "enqueue_proxy_outbound_audit",
    "record_proxy_hop",
]

ACTION_PROXY_OUTBOUND = "proxy.outbound"

# proxy_source（X-Proxy-Source 值）→ target_system 反向索引（供 DB resource 落位）
_SYSTEM_BY_PROXY_SOURCE: dict[str, str] = {
    source: system for system, source in SOURCE_BY_TARGET_SYSTEM.items()
}


def _subject_id_of(user_ctx: dict[str, Any]) -> str | None:
    """主体 sub（统一主体 dict 的 id；无 id = 服务 Key 未绑定/无身份可解析）. """
    subject_id = user_ctx.get("id")
    if subject_id is None:
        return None
    return str(subject_id)


def _first_role(user_ctx: dict[str, Any]) -> str | None:
    """主角色（JWT role 单值；agent roles 列表取首，与 resolve_identity 同构）. """
    role = user_ctx.get("role")
    if role:
        return str(role)
    roles = user_ctx.get("roles") or []
    if roles:
        return str(roles[0])
    return None


def _tenant_code_of(user_ctx: dict[str, Any]) -> str | None:
    tenant_code = str(user_ctx.get("tenant_code") or user_ctx.get("tenant_id") or "")
    return tenant_code or None


def build_principal_block(user_ctx: dict[str, Any]) -> dict[str, Any] | None:
    """主体块（§8.2 principal：含 subject_type/auth_method，agent 面可审计识别）."""
    subject_id = _subject_id_of(user_ctx)
    if subject_id is None:
        return None
    return {
        "subject_id": subject_id,
        "subject_type": user_ctx.get("subject_type") or "user",
        "tenant_code": _tenant_code_of(user_ctx),
        "role": _first_role(user_ctx),
        "auth_method": user_ctx.get("auth_method") or "jwt",
    }


def _delegated_of(user_ctx: dict[str, Any]) -> dict[str, Any] | None:
    """归一化 delegated 块（统一主体 dict 的 delegated/on_behalf_of 字段）."""
    delegated = user_ctx.get("delegated") or user_ctx.get("on_behalf_of")
    if not isinstance(delegated, dict) or delegated.get("subject_id") is None:
        return None
    return {
        "subject_id": str(delegated.get("subject_id")),
        "subject_type": delegated.get("subject_type") or "user",
        "tenant_code": delegated.get("tenant_code"),
        "role": delegated.get("role"),
    }


def build_effective_block(
    principal: dict[str, Any] | None,
    delegated: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """有效身份块（§3.2：委托时 = delegated 目标；无委托 = principal 自身）."""
    if delegated is not None:
        return {key: delegated.get(key) for key in ("subject_id", "subject_type", "tenant_code", "role")}
    if principal is None:
        return None
    return {
        "subject_id": principal.get("subject_id"),
        "subject_type": principal.get("subject_type"),
        "tenant_code": principal.get("tenant_code"),
        "role": principal.get("role"),
    }


def build_identity_detail(
    user_ctx: dict[str, Any] | None,
    *,
    proxy_source: str | None = None,
    request_id: str | None = None,
    org_alias: str | None = None,
    proxy_chain: list[str] | None = None,
) -> dict[str, Any]:
    """统一主体 dict → §8.2 ``identity`` 审计块（含 principal/delegated/effective）.

    Args:
        user_ctx: 统一主体 dict（get_current_user / resolve_agent_principal /
            服务账号映射）；None 或无可解析主体 → 空 principal（调用方自行裁剪）。
        proxy_source: 出口来源标识（如 openbase-dps-proxy）。
        request_id: X-Request-Id（缺省生成）。
        org_alias: X-Org-ID 别名值（默认取 effective tenant_code）。
        proxy_chain: 完整来源链（§5.3；批次 3/T8 落全链）。

    Returns:
        §8.2 identity 审计块 dict。
    """
    principal = build_principal_block(user_ctx) if isinstance(user_ctx, dict) else None
    delegated = _delegated_of(user_ctx) if isinstance(user_ctx, dict) else None
    effective = build_effective_block(principal, delegated)
    tenant_code = (effective or {}).get("tenant_code") if effective else None
    return {
        "principal": principal,
        "delegated": delegated,
        "effective": effective,
        "proxy_source": proxy_source,
        "proxy_chain": proxy_chain,
        "request_id": request_id or f"req-{uuid.uuid4().hex[:12]}",
        "org_alias": org_alias or tenant_code,
    }


def _new_request_id() -> str:
    return f"req-{uuid.uuid4().hex[:12]}"


def build_identity_section(
    *,
    subject_id: int | str | None,
    subject_type: str | None = None,
    tenant_code: str | None = None,
    role: str | None = None,
    auth_method: str | None = None,
    delegated: dict[str, Any] | None = None,
    proxy_source: str | None = None,
    request_id: str | None = None,
    proxy_chain: list[str] | None = None,
) -> dict[str, Any]:
    """构造最小 §8.2 identity 审计块（DB 审计 detail 并入用，T8-1）.

    lifecycle/delegation/purge 既有 DB 审计 detail 并入同一 identity 块结构
    （principal/delegated/effective/proxy_source/proxy_chain/request_id 六键恒有）。

    Args:
        subject_id: principal subject id（None → principal 空块）。
        subject_type: 主体具象（user/agent；缺省 user）。
        tenant_code: 主体 tenant_code。
        role: 主体粗粒度角色。
        auth_method: 认证方式（jwt/sk-agent/internal）。
        delegated: 委托 dict（§8.2 delegated 形态；可选）。
        proxy_source: 出口来源标识（DB 审计写路径通常无，传 None）。
        request_id: 请求 ID（缺省生成）。
        proxy_chain: 完整来源链（可选）。

    Returns:
        §8.2 identity 审计块（六键完整）。
    """
    if subject_id is None:
        user_ctx: dict[str, Any] = {}
    else:
        user_ctx = {
            "id": subject_id,
            "subject_type": subject_type or "user",
            "tenant_code": tenant_code,
            "role": role,
            "auth_method": auth_method or "internal",
        }
    if delegated is not None:
        user_ctx["delegated"] = delegated
    return build_identity_detail(
        user_ctx,
        proxy_source=proxy_source,
        request_id=request_id,
        proxy_chain=proxy_chain,
    )


async def record_proxy_hop(
    session: Any,
    *,
    identity: dict[str, Any],
    system: str,
    method: str,
    path: str,
    request_id: str,
    proxy_chain: list[str] | None = None,
) -> AuditLog:
    """T8 出站 DB 审计钩子：每次出站装配落 proxy_chain 全链（action=proxy.outbound）.

    - ``identity`` 为 §8.2 identity 审计块（request.state.identity / build_identity_detail
      产物）；principal/delegated/effective/proxy_source/proxy_chain/request_id 落 detail。
    - user_id 兼容位 = principal.subject_id（§8.1）；request_id 与入站一致（T8-3）。
    - 提交由调用方负责（AuditMiddleware 响应后 best-effort 会话 / 测试 recording session）。

    Args:
        session: 数据库会话（add 后由调用方 commit/flush）。
        identity: §8.2 identity 审计块。
        system: 目标系统键（dps/llm/rag/memory/generic）。
        method: 出站 HTTP 方法。
        path: 出站上游路径。
        request_id: X-Request-Id（与入站一致）。
        proxy_chain: 完整来源链（覆盖 identity.proxy_chain，§5.3/T1-7）。

    Returns:
        已写入（未提交）的 AuditLog 行。
    """
    effective_chain = proxy_chain if proxy_chain is not None else identity.get("proxy_chain")
    if effective_chain is not None:
        identity = dict(identity)
        identity["proxy_chain"] = effective_chain
    principal = identity.get("principal") or {}
    subject_text = str(principal.get("subject_id") or "")
    record = AuditLog(
        user_id=int(subject_text) if subject_text.isdigit() else None,
        tenant_id=None,
        action=ACTION_PROXY_OUTBOUND,
        resource=system,
        resource_id=str(path)[:64] or None,
        request_id=request_id,
        detail={
            "identity": identity,
            "system": system,
            "method": method,
            "path": path,
        },
    )
    session.add(record)
    await session.flush()
    logger.info(
        "proxy outbound hop audited",
        extra={
            "system": system,
            "subject_id": principal.get("subject_id"),
            "subject_type": principal.get("subject_type"),
            "request_id": request_id,
        },
    )
    return record


async def enqueue_proxy_outbound_audit(
    session: Any,
    *,
    user_ctx: dict[str, Any],
    target_system: str,
    method: str,
    path: str,
    request_id: str | None = None,
    proxy_source: str | None = None,
    proxy_chain: list[str] | None = None,
) -> AuditLog:
    """proxy 出站审计落库（action=proxy.outbound，detail 含 §8.2 identity 块）.

    - 记录 agent（及 user）出站主体：``detail.identity.principal.subject_type`` 显式
      可辨识 agent；``proxy_source``/``tenant_code``/``request_id`` 贯穿同一请求；
      ``proxy_chain``（§5.3 全链）一并落库（T8）。
    - user_id 兼容位 = principal.subject_id（agent 亦以其 users.id 落列，§8.1）；
      tenant_id 为 None 时以审计块 tenant_code 不进结构列（避免 type 迁移）。
    - 提交由调用方负责（与请求事务同提交或独立会话 best-effort，参照 K03 白名单审计）。

    Args:
        session: 数据库会话（AuditLog.add 后由调用方 commit）。
        user_ctx: 统一主体 dict（须可解析 subject_id）。
        target_system: 目标系统键（dps/llm/rag/memory/generic）。
        method: 出站 HTTP 方法。
        path: 出站上游路径。
        request_id: X-Request-Id（缺省生成）。
        proxy_source: 出口来源标识（缺省按 target_system 常量映射）。
        proxy_chain: 完整来源链（§5.3/T1-7；可选）。

    Returns:
        已写入（未提交）的 AuditLog 行。
    """
    request_id = request_id or _new_request_id()
    source = proxy_source or SOURCE_BY_TARGET_SYSTEM.get(target_system)
    identity = build_identity_detail(
        user_ctx,
        proxy_source=source,
        request_id=request_id,
        proxy_chain=proxy_chain,
    )
    return await record_proxy_hop(
        session,
        identity=identity,
        system=target_system,
        method=method,
        path=path,
        request_id=request_id,
        proxy_chain=proxy_chain,
    )


def attach_outbound_identity(
    request: Any,
    user_ctx: dict[str, Any] | None,
    *,
    proxy_source: str | None,
    request_id: str | None = None,
) -> None:
    """出站装配钩子：将 §8.2 identity 审计块写入 ``request.state.identity``.

    AuditMiddleware._record 消费该 state 并入审计记录 detail/extra；仅当请求对象
    可用且主体可解析时写入（匿名/健康/服务 Key 未绑定场景跳过，避免伪主体标注）。
    T8（OB-13）：同时标注 ``request.state.outbound_assembled=True`` 与
    ``request.state.outbound_system``，供 AuditMiddleware 响应后经
    :func:`record_proxy_hop` 落 DB 审计（action=proxy.outbound，同 request_id）。
    """
    if request is None:
        return
    if not isinstance(user_ctx, dict):
        return
    state = getattr(request, "state", None)
    if state is None:
        return
    if _subject_id_of(user_ctx) is None:
        return
    effective_request_id = request_id
    if effective_request_id is None:
        effective_request_id = str(getattr(state, "request_id", "") or "")
    proxy_chain = user_ctx.get("proxy_chain")
    if not isinstance(proxy_chain, list):
        proxy_chain = getattr(state, "proxy_chain", None)
    if not isinstance(proxy_chain, list):
        proxy_chain = None
    state.identity = build_identity_detail(
        user_ctx,
        proxy_source=proxy_source,
        request_id=effective_request_id or None,
        proxy_chain=proxy_chain,
    )
    state.outbound_assembled = True
    state.outbound_system = _SYSTEM_BY_PROXY_SOURCE.get(proxy_source)
