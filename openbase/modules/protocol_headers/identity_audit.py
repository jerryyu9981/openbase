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
完整入站链路（AuthMiddleware→AuditMiddleware schema 贯穿）与 record_proxy_hop
DB 钩子随批次 3/T8（OB-13 审计贯穿）继续接线，本批次先落地主体出站审计面：
- :func:`build_identity_detail`：统一主体 dict → §8.2 identity 块（纯函数）；
- :func:`attach_outbound_identity`：出站装配（build_outbound_headers）写入
  ``request.state.identity``（AuditMiddleware._record 消费）；
- :func:`enqueue_proxy_outbound_audit`：proxy 出站审计落库（action=proxy.outbound），
  供 proxy 族/测试以同 request_id 串联审计（T8 全链钩子复用同一 detail 形态）。
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
    "build_principal_block",
    "enqueue_proxy_outbound_audit",
]

ACTION_PROXY_OUTBOUND = "proxy.outbound"


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


async def enqueue_proxy_outbound_audit(
    session: Any,
    *,
    user_ctx: dict[str, Any],
    target_system: str,
    method: str,
    path: str,
    request_id: str | None = None,
    proxy_source: str | None = None,
) -> AuditLog:
    """proxy 出站审计落库（action=proxy.outbound，detail 含 §8.2 identity 块）.

    - 记录 agent（及 user）出站主体：``detail.identity.principal.subject_type`` 显式
      可辨识 agent；``proxy_source``/``tenant_code``/``request_id`` 贯穿同一请求。
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

    Returns:
        已写入（未提交）的 AuditLog 行。
    """
    request_id = request_id or _new_request_id()
    source = proxy_source or SOURCE_BY_TARGET_SYSTEM.get(target_system)
    identity = build_identity_detail(
        user_ctx, proxy_source=source, request_id=request_id
    )
    principal = identity["principal"] or {}
    subject_text = str(principal.get("subject_id") or "")
    record = AuditLog(
        user_id=int(subject_text) if subject_text.isdigit() else None,
        tenant_id=None,
        action=ACTION_PROXY_OUTBOUND,
        resource=target_system,
        resource_id=str(path)[:64] or None,
        request_id=request_id,
        detail={
            "identity": identity,
            "system": target_system,
            "method": method,
            "path": path,
        },
    )
    session.add(record)
    await session.flush()
    logger.info(
        "proxy outbound audited",
        extra={
            "target_system": target_system,
            "subject_id": principal.get("subject_id"),
            "subject_type": principal.get("subject_type"),
            "request_id": request_id,
        },
    )
    return record


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
    state.identity = build_identity_detail(
        user_ctx,
        proxy_source=proxy_source,
        request_id=effective_request_id or None,
    )
