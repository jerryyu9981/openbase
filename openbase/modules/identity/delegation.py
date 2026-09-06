"""identity 模块：on_behalf_of 委托 claim 结构 + 域不变式校验器（U1 T4，K08 / OB-11）.

设计草案 §7 / §11 T4（R2 边界，立项 §3 T4/§4 验收/§7 依赖 R2）：
- **claim 结构**（§7.1）：``on_behalf_of = {subject_id, subject_type, tenant_code, role,
  iss, exp}``——U1 以 JWT claim 内嵌委托块承载，P2-1（S1b）头规范落定前的自洽形态；
- **域不变式校验器**（§7.2 R-M4-1/2）：``verify_delegation``——
  1. 仅 agent 主体可委托（user 挂 on_behalf_of → 403）；
  2. ``delegated.tenant_code == principal.tenant_code``，不等 → 403
     ``PERM_DELEGATION_CROSS_TENANT``；
  3. 委托目标存在、subject_type 相符且 active，exp 未过期（违例 403）；
  4. ``delegated.role`` 角色阶 ≤ 签发者授权域（违例 403 ``PERM_DELEGATION_ROLE``）；
  5. 嵌套链：委托目标行（users.on_behalf_of）若再嵌委托 → 递归逐跳重校验
     （每跳同 2/3/4，任意一跳跨界即拒——草案 §11 T4-4）；
- **签发链**（§7.3/R-M4-1）：``issue_delegated_token_pair`` 先跑归属校验再经
  单一签发器 ``issue_token_pair`` 签名，并写审计 detail 两层
  （``{principal:{id,tenant_code}, delegated:{id,tenant_code,role}}``，§11 T4-6）；
- **校验链**：``verify_request_delegation`` 供 ``verify_principal`` 返回快照后
  追加逐跳重校验（claim 域被篡改/替换 → 403，§11 T4-3/4）；
- **出站头取值骨架**：``delegated_claim_from_payload`` 供 dps/memory/llm proxy
  委托请求取委托域值（§7.3/§11 T4-7）。

R2 边界（不越界）：委托头（X-Proxy-Source 等）的**全局唯一签发规范 / 信任链矩阵**
留 P2-1（S1b），本模块只做 claim 结构与域校验骨架。
"""

from __future__ import annotations

import datetime as dt
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openbase.core.errors import BaseError, ErrorCode
from openbase.core.models import AuditLog, Role, User, user_role
from openbase.modules.identity.state_machine import (
    STATUS_STATE_ACTIVE,
    SUBJECT_TYPE_AGENT,
    SUBJECT_TYPE_USER,
)

logger = logging.getLogger("openbase.identity.delegation")

# ---- on_behalf_of claim 结构（草案 §7.1）----
# subject_id 以字符串 sub 形态承载（与 JWT sub 同形）；normalize 后转 int 供校验。
ON_BEHALF_OF_KEYS = frozenset(
    {"subject_id", "subject_type", "tenant_code", "role", "iss", "exp"}
)
_DELEGATED_REQUIRED_KEYS = frozenset({"subject_id", "subject_type", "tenant_code", "role"})
_DELEGATED_SUBJECT_TYPES = frozenset({SUBJECT_TYPE_USER, SUBJECT_TYPE_AGENT})

# 默认委托有效时长（秒；签发方未显式指定时使用）
DEFAULT_DELEGATION_EXPIRATION_SECONDS = 3600

# 审计 action（委托签发）
DELEGATION_ACTION_ISSUE = "identity.delegation.issue"

# 受控角色阶（与 users/identity ALLOWED_ROLES 同源；阶仅用于「不得越权代执行」比较）
ROLE_RANK: dict[str, int] = {
    "viewer": 0,
    "org_member": 1,
    "org_admin": 2,
    "admin": 3,
}

# 委托签发 token 的缺省主角色（principal 无角色绑定时的最低兜底）
_DEFAULT_ISSUER_ROLE = "viewer"


def _now_epoch() -> int:
    return int(dt.datetime.now(dt.timezone.utc).timestamp())


def _new_request_id() -> str:
    return f"req-{uuid.uuid4().hex[:12]}"


def _role_rank(role_code: str | None) -> int | None:
    """角色阶查询（未知角色码返回 None，视为不可证明 ≤ 授权域）. """
    if not role_code:
        return None
    return ROLE_RANK.get(str(role_code))


def _max_role_rank(role_codes: list[str]) -> int:
    """主体已授权角色最高阶（无任何已知角色 → -1：任何委托角色都越权，fail-closed）."""
    ranks = [_role_rank(code) for code in role_codes]
    known = [rank for rank in ranks if rank is not None]
    return max(known) if known else -1


def _invalid_claim(message: str, detail: dict | None = None) -> BaseError:
    """畸形 on_behalf_of claim（缺字段/类型错误）→ 403（疑似篡改，fail-closed）."""
    return BaseError(
        ErrorCode.PERM_FORBIDDEN,
        message,
        detail=detail or {"reason": "invalid on_behalf_of claim structure"},
    )


def normalize_on_behalf_of(value: object) -> dict | None:
    """校验并归一化 on_behalf_of claim（结构见草案 §7.1）.

    Args:
        value: JWT payload / DB JSON 中的 on_behalf_of 原值。

    Returns:
        归一化 claim dict（``subject_id`` 归一为 int；``iss/exp`` 可选保留）；
        ``None`` 表示无委托块（自身域内操作）。

    Raises:
        BaseError: 结构畸形（非 dict / 缺必需字段 / subject_id 非数字 /
            subject_type 非法）→ 403（PERM_FORBIDDEN，疑似篡改）。
    """
    if value is None:
        return None
    if not isinstance(value, dict):
        raise _invalid_claim("on_behalf_of claim must be an object")
    missing = _DELEGATED_REQUIRED_KEYS - value.keys()
    if missing:
        raise _invalid_claim(
            "on_behalf_of claim missing required fields",
            detail={"missing": sorted(missing)},
        )
    subject_text = str(value["subject_id"])
    if not subject_text.isdigit():
        raise _invalid_claim(
            "delegated subject_id must be numeric",
            detail={"subject_id": subject_text[:32]},
        )
    subject_type = value["subject_type"]
    if subject_type not in _DELEGATED_SUBJECT_TYPES:
        raise _invalid_claim(
            "delegated subject_type must be user|agent",
            detail={"subject_type": str(subject_type)[:16]},
        )
    role_code = value["role"]
    if not isinstance(role_code, str) or not role_code:
        raise _invalid_claim("delegated role must be a non-empty string")
    claim: dict = {
        "subject_id": int(subject_text),
        "subject_type": subject_type,
        "tenant_code": str(value["tenant_code"]),
        "role": role_code,
    }
    if value.get("iss") is not None:
        claim["iss"] = str(value["iss"])
    if value.get("exp") is not None:
        claim["exp"] = int(value["exp"])
    return claim


def build_on_behalf_of_claim(
    *,
    subject_id: int | str,
    subject_type: str,
    tenant_code: str | None,
    role: str,
    issuer: str | None = None,
    exp_seconds: int = DEFAULT_DELEGATION_EXPIRATION_SECONDS,
) -> dict:
    """构造 on_behalf_of claim（§7.1；subject_id 以字符串 sub 形态承载）.

    Args:
        subject_id: 委托目标 sub（user/agent 的 users.id）。
        subject_type: 委托目标具象（user/agent）。
        tenant_code: 委托目标域（不变式：须等于签发者自身 tenant_code）。
        role: 以目标角色执行（≤ 签发者授权域，越权由 verify_delegation 拦截）。
        issuer: 委托签发主体（冗余说明位）。
        exp_seconds: 委托有效时长（默认 3600s）。

    Returns:
        可直接嵌入 JWT ``extra`` 的 on_behalf_of claim dict。
    """
    claim: dict[str, object] = {
        "subject_id": str(subject_id),
        "subject_type": subject_type,
        "tenant_code": tenant_code,
        "role": role,
    }
    if issuer is not None:
        claim["iss"] = str(issuer)
    claim["exp"] = _now_epoch() + int(exp_seconds)
    return claim


def delegated_claim_from_payload(payload: dict) -> dict | None:
    """安全提取 payload 中的 on_behalf_of 委托块（代理族出站头取值用）.

    与逐跳重校验不同：此处只做「读」且不抛错（畸形/缺失 → None），
    因为请求经主体验证器先行拦截后才可能到达代理族（畸形 claim 已在 403 层拦住）。
    """
    if not isinstance(payload, dict):
        return None
    try:
        return normalize_on_behalf_of(payload.get("on_behalf_of"))
    except BaseError:
        logger.debug("malformed on_behalf_of ignored for header extraction")
        return None


async def _load_roles(session: AsyncSession, user_id: int) -> list[str]:
    """查询主体已授权角色码列表（users → user_role → roles）."""
    result = await session.execute(
        select(Role.code)
        .join(user_role, user_role.c.role_id == Role.id)
        .where(user_role.c.user_id == user_id)
    )
    return list(result.scalars().all())


async def verify_delegation(
    session: AsyncSession,
    principal: dict,
    delegated: dict,
    _visited: set[int] | None = None,
) -> None:
    """域不变式校验器（§7.2 R-M4-1/2）：单跳 + 嵌套链逐跳重校验.

    Args:
        session: 数据库会话（委托目标存在/active 校验需要读主行）。
        principal: 签发/执行主体上下文
            {id, subject_type, tenant_code, roles}（roles 为主体已授权角色码）。
        delegated: on_behalf_of claim（原值或已归一化均可）。

    Raises:
        BaseError:
            - 403 PERM_FORBIDDEN：主体非 agent / 委托目标缺失或 subject_type 不符
              或非 active / claim 过期 / 嵌套链成环；
            - 403 PERM_DELEGATION_CROSS_TENANT：委托域 ≠ 主体域（含目标行实际域不符）；
            - 403 PERM_DELEGATION_ROLE：代理角色越权。
    """
    claim = normalize_on_behalf_of(delegated)
    if claim is None:
        return
    visited: set[int] = set(_visited) if _visited is not None else set()

    principal_type = principal.get("subject_type") or SUBJECT_TYPE_USER
    if principal_type != SUBJECT_TYPE_AGENT:
        raise BaseError(
            ErrorCode.PERM_FORBIDDEN,
            "delegation requires an agent principal",
            detail={"principal_subject_type": principal_type},
        )

    principal_tenant = principal.get("tenant_code")
    delegated_tenant = claim["tenant_code"]
    if principal_tenant != delegated_tenant:
        raise BaseError(
            ErrorCode.PERM_DELEGATION_CROSS_TENANT,
            "delegation target tenant differs from principal tenant",
            detail={
                "principal_tenant": principal_tenant,
                "delegated_tenant": delegated_tenant,
            },
        )

    claim_exp = claim.get("exp")
    if claim_exp is not None and _now_epoch() > int(claim_exp):
        raise BaseError(
            ErrorCode.PERM_FORBIDDEN,
            "delegation claim expired",
            detail={"exp": int(claim_exp)},
        )

    delegated_role = claim["role"]
    delegated_rank = _role_rank(delegated_role)
    principal_rank = _max_role_rank(principal.get("roles") or [])
    if delegated_rank is None or delegated_rank > principal_rank:
        raise BaseError(
            ErrorCode.PERM_DELEGATION_ROLE,
            "delegated role exceeds principal grant",
            detail={
                "principal_roles": principal.get("roles") or [],
                "delegated_role": delegated_role,
            },
        )

    target_id = claim["subject_id"]
    if target_id in visited:
        raise BaseError(
            ErrorCode.PERM_FORBIDDEN,
            "delegation cycle detected",
            detail={"chain": sorted(visited)},
        )
    visited.add(target_id)

    target = await session.get(User, target_id)
    if target is None or target.is_deleted:
        raise BaseError(
            ErrorCode.PERM_FORBIDDEN,
            "delegation target not found",
            detail={"subject_id": target_id},
        )
    target_type = target.subject_type or SUBJECT_TYPE_USER
    if target_type != claim["subject_type"]:
        raise BaseError(
            ErrorCode.PERM_FORBIDDEN,
            "delegation target subject_type mismatch",
            detail={"expected": claim["subject_type"], "actual": target_type},
        )
    target_state = target.status_state or STATUS_STATE_ACTIVE
    if target_state != STATUS_STATE_ACTIVE:
        raise BaseError(
            ErrorCode.PERM_FORBIDDEN,
            "delegation target is not active",
            detail={"subject_id": target_id, "status_state": target_state},
        )
    if (target.tenant_code or "") != delegated_tenant:
        # 目标行实际域与 claim 域不符（claim 被换域/挂错对象）→ 视同跨界
        raise BaseError(
            ErrorCode.PERM_DELEGATION_CROSS_TENANT,
            "delegation target belongs to another tenant",
            detail={
                "delegated_tenant": delegated_tenant,
                "target_tenant": target.tenant_code,
            },
        )

    # 嵌套链（§7.2-5/R-M4-2）：目标主体自身若配置了默认委托（users.on_behalf_of），
    # 则以目标主体为新一跳 principal 递归逐跳重校验（每跳同 2/3/4）。
    nested = normalize_on_behalf_of(target.on_behalf_of)
    if nested is not None:
        nested_roles = await _load_roles(session, target.id)
        await verify_delegation(
            session,
            {
                "id": target.id,
                "subject_type": target_type,
                "tenant_code": target.tenant_code,
                "roles": nested_roles,
            },
            nested,
            visited,
        )


async def verify_request_delegation(
    session: AsyncSession,
    payload: dict,
    snapshot: dict | None,
) -> dict | None:
    """每请求重校验（草案 §7.3）：verify_principal 返回快照后追加委托链校验.

    Args:
        session: 数据库会话。
        payload: 已验签解码的 access JWT payload。
        snapshot: verify_principal 返回的主体验证快照（未通过/降级时为 None）。

    Returns:
        原样返回 snapshot（校验通过或无需校验）；委托校验失败抛 403。

    Raises:
        BaseError: 委托域不变式被破坏（claim 域被篡改/替换 → 403）。
    """
    if not isinstance(snapshot, dict):
        return snapshot
    delegated = normalize_on_behalf_of(payload.get("on_behalf_of") if isinstance(payload, dict) else None)
    if delegated is None:
        return snapshot

    principal_roles: list[str] = []
    if isinstance(payload, dict) and payload.get("role"):
        principal_roles = [str(payload["role"])]
    subject_text = str(payload.get("sub", "")) if isinstance(payload, dict) else ""
    subject_id: int | None = int(subject_text) if subject_text.isdigit() else None
    principal = {
        "id": subject_id,
        "subject_type": snapshot.get("subject_type") or SUBJECT_TYPE_USER,
        "tenant_code": snapshot.get("tenant_code"),
        "roles": principal_roles,
    }
    await verify_delegation(session, principal, delegated)
    return snapshot


async def enqueue_delegation_audit(
    session: AsyncSession,
    *,
    principal_id: int,
    principal_tenant_code: str | None,
    principal_tenant_id: int | None,
    delegated: dict,
    request_id: str | None = None,
) -> AuditLog:
    """写委托签发审计（§7.3/§11 T4-6）：detail 记两层 principal+delegated.

    Args:
        session: 数据库会话（提交由调用方负责，与 token 签发同事务）。
        principal_id: 签发主体 id（agent users.id）。
        principal_tenant_code: 签发主体 tenant_code。
        principal_tenant_id: 签发主体 tenant_id（audit_logs.tenant_id）。
        delegated: 已归一化 on_behalf_of claim。
        request_id: 透传 request_id（缺省生成）。

    Returns:
        已写入（未提交）的 AuditLog 行。
    """
    delegated_id = int(delegated["subject_id"])
    detail = {
        "principal": {"id": principal_id, "tenant_code": principal_tenant_code},
        "delegated": {
            "id": delegated_id,
            "tenant_code": delegated["tenant_code"],
            "role": delegated["role"],
        },
    }
    record = AuditLog(
        user_id=principal_id,
        tenant_id=principal_tenant_id,
        action=DELEGATION_ACTION_ISSUE,
        resource="users",
        resource_id=str(delegated_id),
        request_id=request_id or _new_request_id(),
        detail=detail,
    )
    session.add(record)
    await session.flush()
    logger.info(
        "delegation audited",
        extra={
            "principal_id": principal_id,
            "delegated_id": delegated_id,
            "delegated_tenant": delegated["tenant_code"],
        },
    )
    return record


async def issue_delegated_token_pair(
    session: AsyncSession,
    *,
    principal_id: int,
    delegated_claim: dict | None,
    request_id: str | None = None,
) -> tuple[str, str]:
    """委托签发链（草案 §7.3/R-M4-1）：归属校验通过后经单一签发器签名.

    先装载签发主体（agent 行）→ 跑 ``verify_delegation``（含嵌套链逐跳重校验）→
    以单一签发器 ``issue_token_pair`` 签发 access/refresh（on_behalf_of 入 claim）→
    写两层审计。

    Args:
        session: 数据库会话（提交由调用方负责）。
        principal_id: 签发主体 users.id（必须为 agent 主体）。
        delegated_claim: on_behalf_of claim（草案 §7.1 结构）。
        request_id: 透传 request_id（审计用）。

    Returns:
        (access_token, refresh_token)。

    Raises:
        BaseError: 主体不存在 404；委托校验失败 403（跨界/非 agent/目标非 active/
            角色越权）。
    """
    if delegated_claim is None:
        raise BaseError(
            ErrorCode.PARAM_INVALID,
            "delegated_claim is required for delegated token issuance",
        )
    delegated = normalize_on_behalf_of(delegated_claim)
    principal = await session.get(User, principal_id)
    if principal is None or principal.is_deleted:
        raise BaseError(ErrorCode.BIZ_NOT_FOUND, f"principal not found: {principal_id}")
    principal_roles = await _load_roles(session, principal.id)
    principal_ctx = {
        "id": principal.id,
        "subject_type": principal.subject_type or SUBJECT_TYPE_USER,
        "tenant_code": principal.tenant_code,
        "roles": principal_roles,
    }
    await verify_delegation(session, principal_ctx, delegated)

    from openbase.modules.auth.jwt import issue_token_pair

    issuer_role = principal_roles[0] if principal_roles else _DEFAULT_ISSUER_ROLE
    access, refresh = issue_token_pair(
        subject=str(principal.id),
        username=principal.username,
        tenant_id=str(principal.tenant_id) if principal.tenant_id else None,
        tenant_code=principal.tenant_code,
        token_version=principal.token_version or 0,
        role=issuer_role,
        subject_type=principal.subject_type or SUBJECT_TYPE_USER,
        delegated=delegated_claim,
    )
    await enqueue_delegation_audit(
        session,
        principal_id=principal.id,
        principal_tenant_code=principal.tenant_code,
        principal_tenant_id=principal.tenant_id,
        delegated=delegated,
        request_id=request_id,
    )
    return access, refresh


__all__ = [
    "DEFAULT_DELEGATION_EXPIRATION_SECONDS",
    "DELEGATION_ACTION_ISSUE",
    "ON_BEHALF_OF_KEYS",
    "ROLE_RANK",
    "build_on_behalf_of_claim",
    "delegated_claim_from_payload",
    "enqueue_delegation_audit",
    "issue_delegated_token_pair",
    "normalize_on_behalf_of",
    "verify_delegation",
    "verify_request_delegation",
]
