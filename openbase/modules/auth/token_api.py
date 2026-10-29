"""E1-5A 令牌服务面：JWKS 发布、内省（RFC 7662 风格）、吊销增量快照.

职责边界：
- ``GET /.well-known/jwks.json``：公开（无鉴权），供下游/外部验证 RS256 签名；
- ``POST /api/v1/auth/introspect``：服务 Key 鉴权（scope ``system`` 含 ``auth`` 或 ``*``），
  验签 + 主体状态 / token 版本核查，返回 ``active`` 与 claims 摘要；
- ``GET /api/v1/auth/revocations``：服务 Key 鉴权，按 ``since`` 增量下发主体
  token_version / 服务 Key / agent Key 状态（下游本地缓存失效依据）。

设计取舍：内省**不做结果缓存** —— 吊销必须即时可见，缓存会让 ``active`` 结论过期；
高频批量场景应改用 revocations 增量对齐。
"""

from __future__ import annotations

import datetime as dt
import time
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openbase.core.db.session import get_db
from openbase.core.deps.auth import require_api_key
from openbase.core.errors import BaseError, ErrorCode
from openbase.core.models.base import AgentApiKey, ServiceApiKey, User
from openbase.modules.auth.jwt import decode_any_token, jwks_document
from openbase.modules.auth.service_keys import scope_allows
from openbase.settings import get_settings

router = APIRouter(tags=["auth-tokens"])

_TOKEN_TYPE_BY_HINT = {
    "access_token": "access",
    "refresh_token": "refresh",
}

# 吊销增量游标回退（秒）：覆盖同一毫秒内多行更新的边界，消费端按主键幂等去重
_CURSOR_OVERLAP_SECONDS = 0.001


class IntrospectRequest(BaseModel):
    """内省请求体（RFC 7662 字段子集）."""

    token: str = Field(min_length=1, description="待内省的 JWT")
    token_type_hint: str | None = Field(
        default=None, description="access_token / refresh_token（缺省不限定）"
    )


def _require_token_scope(credential: dict[str, Any]) -> None:
    """内省/吊销面要求服务 Key 的 system scope 含 ``auth``（或 ``*``）."""
    if not scope_allows(credential.get("scope"), "auth", credential.get("tenant_id")):
        raise BaseError(ErrorCode.PERM_API_KEY_SCOPE, "api key scope mismatch")


def _epoch(value: Any) -> float | None:
    """datetime → epoch 秒（None 透传）."""
    if value is None:
        return None
    return value.timestamp()


def _since_datetime(since: float | None) -> dt.datetime:
    """``since``（epoch 秒）→ UTC aware datetime；缺省取纪元起点（全量快照）."""
    if since is None:
        return dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)
    return dt.datetime.fromtimestamp(float(since), dt.timezone.utc)


@router.get("/.well-known/jwks.json", include_in_schema=True)
async def publish_jwks() -> JSONResponse:
    """发布 JWKS（RS256 公钥集；未配置非对称签名时为空列表）."""
    document = jwks_document()
    return JSONResponse(
        content=document, headers={"Cache-Control": "public, max-age=300"}
    )


@router.post("/api/v1/auth/introspect")
async def introspect_token(
    request: Request,
    body: IntrospectRequest,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """内省令牌：验签 + 主体状态 / token 版本核查（服务 Key 鉴权）.

    Returns:
        ``{"active": bool, ...claims 摘要}``；无效/过期/类型不符/主体被吊销一律
        ``active=False`` 且带 ``reason``（不抛 401，符合 RFC 7662 语义）。
    """
    credential = await require_api_key(request=request, session=session)
    _require_token_scope(credential)

    payload = decode_any_token(body.token)
    expected_type = _TOKEN_TYPE_BY_HINT.get(body.token_type_hint or "")
    if payload is None:
        return {"active": False, "reason": "invalid_or_expired_token"}
    if expected_type and payload.get("type") != expected_type:
        return {
            "active": False,
            "reason": "token_type_mismatch",
            "token_type": payload.get("type"),
        }

    summary: dict[str, Any] = {
        "active": True,
        "sub": payload.get("sub"),
        "sub_type": payload.get("sub_type"),
        "type": payload.get("type"),
        "username": payload.get("username"),
        "tenant_id": payload.get("tenant_id"),
        "tenant_code": payload.get("tenant_code"),
        "tvn": payload.get("tvn"),
        "iss": payload.get("iss"),
        "aud": payload.get("aud"),
        "iat": payload.get("iat"),
        "exp": payload.get("exp"),
    }

    from openbase.modules.identity import verification as principal_verification

    try:
        snapshot = await principal_verification.verify_principal(
            session,
            payload,
            request_id=getattr(request.state, "request_id", None),
            request_method=request.method,
        )
    except BaseError as exc:
        summary.update(
            {
                "active": False,
                "reason": getattr(exc.code, "value", str(exc.code)),
            }
        )
        return summary

    # snapshot=None 表示无法确认（外域 sub / DB 降级放行），签名有效即视为 active，
    # 但显式标注 principal_verified=False，供下游按策略决定是否采信。
    summary["principal_verified"] = snapshot is not None
    if snapshot is not None:
        summary["subject_status"] = snapshot.get("status_state")
        summary["token_version"] = snapshot.get("token_version")
    return summary


@router.get("/api/v1/auth/revocations")
async def list_revocations(
    request: Request,
    since: float | None = Query(default=None, ge=0, description="增量起点（epoch 秒）"),
    limit: int | None = Query(default=None, ge=1, description="单页条数（受配置上限约束）"),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """吊销/状态增量快照（服务 Key 鉴权；按各表 ``updated_at`` 升序分页）."""
    credential = await require_api_key(request=request, session=session)
    _require_token_scope(credential)

    page_limit = int(get_settings().jwt_revocations_page_limit)
    take = min(int(limit), page_limit) if limit is not None else page_limit
    since_at = _since_datetime(since)

    user_rows = (
        await session.execute(
            select(
                User.id,
                User.subject_type,
                User.status_state,
                User.token_version,
                User.tenant_code,
                User.updated_at,
            )
            .where(User.updated_at > since_at)
            .order_by(User.updated_at.asc(), User.id.asc())
            .limit(take)
        )
    ).all()
    service_key_rows = (
        await session.execute(
            select(
                ServiceApiKey.key_id,
                ServiceApiKey.status,
                ServiceApiKey.revoked_at,
                ServiceApiKey.expires_at,
                ServiceApiKey.tenant_code,
                ServiceApiKey.updated_at,
            )
            .where(ServiceApiKey.updated_at > since_at)
            .order_by(ServiceApiKey.updated_at.asc(), ServiceApiKey.id.asc())
            .limit(take)
        )
    ).all()
    agent_key_rows = (
        await session.execute(
            select(
                AgentApiKey.id,
                AgentApiKey.agent_id,
                AgentApiKey.status,
                AgentApiKey.expires_at,
                AgentApiKey.updated_at,
            )
            .where(AgentApiKey.updated_at > since_at)
            .order_by(AgentApiKey.updated_at.asc(), AgentApiKey.id.asc())
            .limit(take)
        )
    ).all()

    subjects = [
        {
            "sub": str(row.id),
            "sub_type": row.subject_type,
            "status": row.status_state,
            "token_version": row.token_version,
            "tenant_code": row.tenant_code,
            "updated_at": _epoch(row.updated_at),
        }
        for row in user_rows
    ]
    service_keys = [
        {
            "id": row.key_id,
            "status": row.status,
            "revoked_at": _epoch(row.revoked_at),
            "expires_at": _epoch(row.expires_at),
            "tenant_code": row.tenant_code,
            "updated_at": _epoch(row.updated_at),
        }
        for row in service_key_rows
    ]
    agent_keys = [
        {
            "id": str(row.id),
            "agent_id": str(row.agent_id),
            "status": row.status,
            "expires_at": _epoch(row.expires_at),
            "updated_at": _epoch(row.updated_at),
        }
        for row in agent_key_rows
    ]

    updated_marks = [
        entry["updated_at"]
        for entry in (*subjects, *service_keys, *agent_keys)
        if entry["updated_at"] is not None
    ]
    since_value = float(since) if since is not None else 0.0
    if updated_marks:
        # 游标回退 1ms：同一毫秒内批量更新的多行若恰好取到最大值，下次 `> since`
        # 会漏读其余行；回退重叠由消费端按主键幂等覆盖（宁可重复不可漏吊销）。
        next_since = max(max(updated_marks) - _CURSOR_OVERLAP_SECONDS, since_value)
    else:
        next_since = since_value
    return {
        "since": since_value,
        "next_since": next_since,
        "generated_at": time.time(),
        "limit": take,
        "subjects": subjects,
        "service_keys": service_keys,
        "agent_keys": agent_keys,
    }
