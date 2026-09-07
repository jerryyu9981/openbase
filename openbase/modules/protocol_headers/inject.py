"""出站身份头装配（build_outbound_headers）——全 proxy 唯一出站装配点（P2-1 §3.2/§3.5/§3.9）.

- 取值**只允许来自统一主体上下文**（get_current_user/resolve_agent_principal 返回
  dict 经 :func:`protocol_headers.identity_context.resolve_identity` 解析），
  禁止从客户端原始头 / 二次 JWT 解码 / 配置文件默认值直接取值（R-H1-1）。
- 出站恒重写 ``X-Proxy-Source`` 为本出口来源常量（防伪造 last-hop，§5.3）；
  ``X-Request-Id`` 沿用审计中间件生成值透传（D-OB13-2）。
- 委托请求：四头承载**委托有效身份**（delegated.subject_id/tenant_code/role），
  ``X-Agent-Id`` 承载执行 agent principal（§3.6 形态 A）。
- 无身份可解析（匿名/健康/服务级调用未映射）→ 不注入伪身份头（T1-9）。
- role_map（OB-12）入参预留：目标系统配置互译表时对 X-User-Role 翻译（T6 挂点）。
"""
from __future__ import annotations

import logging
import uuid
from collections.abc import Mapping
from typing import Any

from openbase.core.errors import BaseError, ErrorCode
from openbase.modules.protocol_headers.constants import (
    HEADER_AGENT_ID,
    HEADER_ORG_ID,
    HEADER_PROXY_SOURCE,
    HEADER_REQUEST_ID,
    HEADER_TENANT_ID,
    HEADER_USER_ID,
    HEADER_USER_ROLE,
    OUTBOUND_IDENTITY_TARGETS,
    SOURCE_BY_TARGET_SYSTEM,
)
from openbase.modules.protocol_headers.identity_audit import attach_outbound_identity
from openbase.modules.protocol_headers.identity_context import resolve_identity
from openbase.modules.protocol_headers.role_map import translate_role_code
from openbase.modules.protocol_headers.validate import validate_header_value

logger = logging.getLogger("openbase.protocol_headers.inject")

__all__ = ["build_outbound_headers"]


def _request_id_of(request: Any, provided: str | None) -> str:
    """X-Request-Id 取值：显式提供 > request.state.request_id > 新生成."""
    if provided:
        return provided
    if request is not None:
        request_id = getattr(getattr(request, "state", None), "request_id", None)
        if request_id:
            return str(request_id)
    return f"req-{uuid.uuid4().hex[:12]}"


def _apply_value_map(value: str | None, value_map: Mapping[str, str] | None) -> str | None:
    """目标系统值映射（dps_org_map/dps_tenant_map：OpenBase 值 → 目标值）.

    未配置/未命中返回原值（延续既有 dps/memory 映射链语义）。
    """
    if value is None or not value:
        return value
    if value_map and value in value_map:
        return str(value_map[value])
    return value


def build_outbound_headers(
    request: Any = None,
    user_ctx: dict[str, Any] | None = None,
    *,
    target_system: str,
    extra_headers: dict[str, str] | None = None,
    role_map: dict[str, Any] | None = None,
    default_tenant: str | None = None,
    default_org: str | None = None,
    default_role: str | None = None,
    tenant_value_map: Mapping[str, str] | None = None,
    org_value_map: Mapping[str, str] | None = None,
    request_id: str | None = None,
    include_proxy_source: bool = True,
) -> dict[str, str]:
    """装配转发上游的出站请求头（§3.5 注入矩阵唯一装配点）.

    Args:
        request: 当前 FastAPI Request（取 request.state.request_id；可 None）。
        user_ctx: 统一主体 dict（get_current_user / get_proxy_identity / 服务账号
            上下文映射）；None 表示无身份可解析（出站不注入身份头）。
        target_system: dps/llm/rag/memory/generic（决定 X-Proxy-Source 常量）。
        extra_headers: 非身份业务头（Content-Type/Accept/Authorization/X-API-Key…）。
        role_map: OB-12 互译表（可选；配置了目标系统表时翻译 X-User-Role，T6）。
        default_tenant: 目标系统显式兜底 tenant（如 dps_default_tenant_id）。
        default_org: 目标系统显式兜底 org 别名（如 memory openbase-default）。
        default_role: 角色缺省（dps 历史语义缺省 "user"）。
        tenant_value_map: 目标系统 tenant 值映射表（如 dps_tenant_map）。
        org_value_map: 目标系统 org 值映射表（如 dps_org_map）。
        request_id: X-Request-Id 显式值（缺省读 request.state / 新生成）。
        include_proxy_source: 是否注入 X-Proxy-Source（通用 proxy 服务 Key 通道
            匿名读场景按 D-V6 保留来源标注，恒 True）。

    Returns:
        完整出站请求头 dict（身份头 + 来源 + request_id + extra）。

    Raises:
        BaseError: target_system 非法 → 400 PARAM_INVALID。
    """
    if target_system not in OUTBOUND_IDENTITY_TARGETS:
        raise BaseError(
            ErrorCode.PARAM_INVALID,
            f"unknown outbound target system: {target_system}",
            detail={"allowed": sorted(OUTBOUND_IDENTITY_TARGETS)},
        )

    headers: dict[str, str] = dict(extra_headers or {})
    headers[HEADER_REQUEST_ID] = _request_id_of(request, request_id)
    source = SOURCE_BY_TARGET_SYSTEM[target_system]
    if include_proxy_source:
        headers[HEADER_PROXY_SOURCE] = source

    identity = resolve_identity(user_ctx)
    if identity is None:
        # 无身份可解析：不注入伪身份头（T1-9 匿名/健康语义）
        return headers

    # ---- 有效身份字段（委托覆盖在 resolve_identity 已完成）----
    subject_id = identity.effective_subject_id
    tenant_value = identity.effective_tenant_code or default_tenant
    role_value = identity.effective_role or default_role
    org_value = identity.org_id or default_org or tenant_value

    # X-User-ID / X-Tenant-ID / X-Org-ID（org 为退役兼容别名，值域=tenant 语义）
    headers[HEADER_USER_ID] = validate_header_value(HEADER_USER_ID, subject_id)
    mapped_tenant = _apply_value_map(tenant_value, tenant_value_map)
    if mapped_tenant:
        headers[HEADER_TENANT_ID] = validate_header_value(HEADER_TENANT_ID, mapped_tenant)
        headers[HEADER_ORG_ID] = validate_header_value(
            HEADER_ORG_ID, _apply_value_map(org_value or mapped_tenant, org_value_map)
        )

    # X-User-Role：仅对**主体解析出的有效角色**做互译（§6.3/T6 挂点）；
    # 显式默认值（如 dps 历史语义 default_role="user"）为目标侧原生码，原样透传。
    # 配置了目标系统互译表但主体角色未命中表 → translate_role_code fail-closed（403）。
    if identity.effective_role:
        translated_role = translate_role_code(
            role_map, target_system, identity.effective_role
        )
    else:
        translated_role = role_value
    if translated_role:
        headers[HEADER_USER_ROLE] = validate_header_value(
            HEADER_USER_ROLE, translated_role
        )

    # X-Agent-Id（agent/委托场景标注执行 agent principal，§3.1/§3.6）
    if identity.agent_id is not None:
        headers[HEADER_AGENT_ID] = validate_header_value(
            HEADER_AGENT_ID, identity.agent_id
        )

    # 审计 identity 块（§8.2，T5/OB-6）：出站装配即写入 request.state.identity，
    # AuditMiddleware._record 经 extra.identity 贯穿 agent/user 主体审计记录。
    attach_outbound_identity(
        request,
        user_ctx,
        proxy_source=source,
        request_id=headers.get(HEADER_REQUEST_ID),
    )

    return headers
