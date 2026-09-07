"""统一身份上下文（IdentityCtx）与解析（P2-1 §3.2/§3.9）.

将认证依赖（``get_current_user`` / ``get_proxy_identity``）返回的统一主体 dict
（含 tenant_code/subject_type/role/on_behalf_of/delegated，auth.py L214-233）解析为
出站头装配所需的有效身份上下文：

- **委托覆盖**（§3.2-2）：上下文含 delegated → 有效身份 = 委托目标
  （X-User-ID=delegated.subject_id、tenant=delegated.tenant_code、role=delegated.role）；
  执行者 principal（agent）作为 ``agent_id``。
- **无委托**（§3.2-3）：有效身份 = principal 自身；subject_type=agent 时 agent_id=principal。
- **服务账号/匿名**（无身份可解析）→ 返回 None（出站不注入伪身份头，T1-9）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# 本地常量（不依赖 modules.identity 包，避免循环导入；与 state_machine 内联值一致）
SUBJECT_TYPE_USER = "user"
SUBJECT_TYPE_AGENT = "agent"

__all__ = ["IdentityCtx", "resolve_identity"]


def _first_role(user_ctx: dict[str, Any]) -> str | None:
    """从统一主体 dict 提取主角色（JWT 路径 role 单值；agent 路径 roles 列表取首）."""
    role = user_ctx.get("role")
    if role:
        return str(role)
    roles = user_ctx.get("roles") or []
    if roles:
        return str(roles[0])
    return None


@dataclass
class IdentityCtx:
    """出站装配所需的统一身份上下文（§3.2 解析链产物）.

    Attributes:
        principal_id: 执行者 principal sub（user 时 = 有效身份；agent 委托时 = 执行 agent）。
        principal_subject_type: 执行者具象（user/agent）。
        subject_id: **有效主体** sub（委托时 = delegated.subject_id）。
        subject_type: 有效主体具象（user/agent）。
        tenant_code: **唯一隔离键** tenant_code（委托时 = 委托域）。
        role: 有效主体粗粒度角色码。
        org_id: 退役兼容别名值（默认=tenant_code；兼容期显式别名可覆盖，OB-8/T7）。
        agent_id: subject_type=agent（或委托场景）时的执行 agent users.id。
        auth_method: 认证方式（jwt / sk-agent / service-key / trusted-orchestrator）。
        proxy_chain: 完整来源链（受信编排 → 本出口，§5.3/T1-7；T8 落审计）。
    """

    principal_id: str
    principal_subject_type: str = SUBJECT_TYPE_USER
    subject_id: str | None = None
    subject_type: str = SUBJECT_TYPE_USER
    tenant_code: str | None = None
    role: str | None = None
    org_id: str | None = None
    agent_id: str | None = None
    auth_method: str = "jwt"
    proxy_chain: list[str] = field(default_factory=list)

    @property
    def effective_subject_id(self) -> str:
        """有效主体 sub（委托时 = 委托目标；否则 = principal 自身）."""
        return self.subject_id or self.principal_id

    @property
    def effective_tenant_code(self) -> str | None:
        """有效隔离键 tenant_code（委托时 = 委托域）."""
        return self.tenant_code

    @property
    def effective_role(self) -> str | None:
        """有效角色（委托时 = 委托角色阶，不得越过签发者授权域——U1 已拦截）."""
        return self.role


def resolve_identity(user_ctx: dict[str, Any] | None) -> IdentityCtx | None:
    """从统一主体 dict 解析出站身份上下文（§3.2 解析链实现）.

    Args:
        user_ctx: ``get_current_user`` / ``resolve_agent_principal`` / 服务账号映射
            返回的主体 dict；None 表示无身份可解析（匿名/健康 → 出站不注入身份头）。

    Returns:
        :class:`IdentityCtx`；无身份可解析返回 None。
    """
    if not isinstance(user_ctx, dict):
        return None
    principal_id = user_ctx.get("id")
    if principal_id is None:
        return None
    principal_subject_type = user_ctx.get("subject_type") or SUBJECT_TYPE_USER

    delegated = user_ctx.get("delegated") or user_ctx.get("on_behalf_of")
    delegated_id: str | None = None
    delegated_tenant: str | None = None
    delegated_role: str | None = None
    delegated_subject_type: str | None = None
    if isinstance(delegated, dict):
        delegated_id = str(delegated.get("subject_id") or "")
        delegated_tenant = delegated.get("tenant_code")
        delegated_role = delegated.get("role")
        delegated_subject_type = delegated.get("subject_type") or SUBJECT_TYPE_USER
        if delegated_id in ("", "None"):
            delegated = None
            delegated_id = None

    tenant_code = str(user_ctx.get("tenant_code") or user_ctx.get("tenant_id") or "")
    tenant_code = tenant_code or None
    role = _first_role(user_ctx)

    agent_id: str | None = None
    if principal_subject_type == SUBJECT_TYPE_AGENT:
        agent_id = str(principal_id)

    if delegated is not None and delegated_id is not None:
        # 委托覆盖（§3.2-2）：X-User-ID/X-Tenant/X-Role 取委托目标；X-Agent-Id=执行 agent
        return IdentityCtx(
            principal_id=str(principal_id),
            principal_subject_type=principal_subject_type,
            subject_id=delegated_id,
            subject_type=delegated_subject_type or SUBJECT_TYPE_USER,
            tenant_code=str(delegated_tenant or "") or None,
            role=delegated_role or None,
            org_id=str(delegated_tenant or "") or None,
            agent_id=agent_id,
            auth_method=str(user_ctx.get("auth_method") or "jwt"),
        )

    return IdentityCtx(
        principal_id=str(principal_id),
        principal_subject_type=principal_subject_type,
        subject_type=principal_subject_type,
        tenant_code=tenant_code,
        role=role,
        org_id=str(user_ctx.get("org_id") or "") or tenant_code,
        agent_id=agent_id,
        auth_method=str(user_ctx.get("auth_method") or "jwt"),
    )
