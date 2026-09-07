"""identity 模块：共享主体验证器（U1 T3，K04 / OB-2 吊销，方案 a token 版本号）.

设计草案 §5.1/§5.2/§12.1 风险 1/2 落点：
- ``verify_principal`` 供 AuthMiddleware / get_current_user / 依赖层共用（同一验证器，
  消灭「仅验签不验状态」路径，R-H2-3）；
- 每请求主体校验三步：① 主体存在 ② ``status_state == active``（默认即生效）③
  ``tvn == users.token_version``（受 ``settings.enforce_token_version`` 开关控制，默认关）；
- v0 兼容（草案 §6.2）：payload 无 ``tvn`` 的存量令牌过渡期放行（刷新后已升级）；
- OIDC 直签 / 外域主体（sub 非数字）无本地主体行 → 放行（降级直签与迁移前语义一致）；
- DB 不可达 → 无法确认状态：**无委托** WARN 后放行（fail-open 过渡窗口，D-V1）；
  **携带 on_behalf_of → 403 ``PERM_DELEGATION_VERIFY_UNAVAILABLE``**（D-V3 fail-closed）；
- 主体行不存在：以 ``purge_records`` 墓碑区分「曾存在后被 purge」→ 401 拒绝（T6
  purge 收口：purged 主体存量 token 一律拒），「无本地行（OIDC 直签/降级内存用户）」→
  保持 T3 遗留 fail-open 放行（deactivated 保留行，suspend/restore/deactivate 均
  即时命中新状态）；**行缺失 + on_behalf_of → 403**（D-V2：委托目标存在性不可证即拒）；
- WARN 指标（§5.1 D-V1/T2-1）：``principal.verify.db_degraded``/``row_missing`` 计数，
  供 verify-env 报告对账（批次 2/T9 消费）；
- 性能（风险 2）：进程经 Redis 短缓存 ``principal:{id}``（TTL ≤60s）避免每请求 DB 读，
  状态/版本变更由写路径失效该键（tvn+1 清键，与 lifecycle T2 清键收敛到本模块）。
  **D-V4**：缓存仅是加速，非信任源——Redis 不可达 = 未命中直读 DB（静默降级）。

注意：本模块只允许依赖 core.models / core.errors / state_machine / redis_client /
identity.delegation，不反向依赖 deps.auth 或 auth.jwt，避免循环导入。
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from sqlalchemy import select

from openbase.core.cache import redis_client as cache_client
from openbase.core.errors import BaseError, ErrorCode
from openbase.core.models import PurgeRecord, User
from openbase.modules.identity.delegation import verify_request_delegation
from openbase.modules.identity.state_machine import (
    STATUS_STATE_ACTIVE,
    STATUS_STATE_PURGED,
    SUBJECT_TYPE_USER,
)

logger = logging.getLogger("openbase.identity.verification")

# principal 快照缓存 TTL（设计 §12.1 风险 2：≤60s 兜底）
PRINCIPAL_CACHE_TTL_SECONDS = 60
PRINCIPAL_CACHE_PREFIX = "principal:"

# P2-1 T2 WARN 指标计数（§5.1 D-V1/D-V2/T2-1/T2-9：verify-env 报告对账项）
_VERDICT_METRICS: dict[str, int] = {
    "db_degraded": 0,
    "row_missing": 0,
    "delegation_denied_db": 0,
    "delegation_denied_row_missing": 0,
}
_VERDICT_METRICS_LOCK = threading.Lock()


def _metric_increment(metric_key: str) -> None:
    """线程安全 WARN 计数（AGENTS.md 并发：共享可变状态加锁）."""
    with _VERDICT_METRICS_LOCK:
        _VERDICT_METRICS[metric_key] = _VERDICT_METRICS.get(metric_key, 0) + 1


def get_verdict_metrics() -> dict[str, int]:
    """读取信任链裁定 WARN 指标快照（verify-env 雏形对账，T2-9/T9）."""
    with _VERDICT_METRICS_LOCK:
        return dict(_VERDICT_METRICS)


def _payload_has_delegation(payload: dict[str, Any]) -> bool:
    """payload 是否携带 on_behalf_of 委托块（用于 fail-closed 判定）."""
    if not isinstance(payload, dict):
        return False
    delegated = payload.get("on_behalf_of")
    return delegated is not None and isinstance(delegated, dict)


def _principal_cache_key(subject_id: int) -> str:
    return f"{PRINCIPAL_CACHE_PREFIX}{subject_id}"


def invalidate_principal_cache(subject_id: int, username: str | None = None) -> None:
    """失效 principal/user 缓存键（状态/版本变更后调用，Redis 不可用静默降级）."""
    try:
        keys = [_principal_cache_key(subject_id)]
        if username:
            keys.append(f"user:{username}")
        cache_client.cache_delete(*keys)
    except Exception as exc:  # noqa: BLE001 - 缓存降级不阻断状态迁移/认证
        logger.debug("principal cache invalidate skipped: %s", exc)


def _cache_get_snapshot(subject_id: int) -> dict[str, Any] | None:
    """读 principal 快照缓存（缓存值结构校验，脏数据视同未命中）."""
    try:
        cached = cache_client.cache_get(_principal_cache_key(subject_id))
    except Exception:  # noqa: BLE001 - Redis 不可用视同未命中
        return None
    if not isinstance(cached, dict):
        return None
    if "status_state" not in cached or "token_version" not in cached:
        return None
    return cached


def _cache_set_snapshot(subject_id: int, snapshot: dict[str, Any]) -> None:
    """写 principal 快照缓存（TTL 60s）."""
    try:
        cache_client.cache_set(
            _principal_cache_key(subject_id),
            snapshot,
            ttl=PRINCIPAL_CACHE_TTL_SECONDS,
        )
    except Exception:  # noqa: BLE001 - Redis 不可用静默跳过
        logger.debug("principal cache set skipped: %s", subject_id)


async def _subject_was_purged(session: Any, subject_id: int) -> bool:
    """墓碑判定：主体是否曾存在后被 purge（purge_records 终态台账命中）.

    Args:
        session: 数据库会话。
        subject_id: 主体 id。

    Returns:
        已 purge 返回 True；未知/未 purge 返回 False（调用方维持 fail-open 过渡语义）。
    """
    try:
        result = await session.execute(
            select(PurgeRecord.subject_id)
            .where(PurgeRecord.subject_id == subject_id)
            .limit(1)
        )
        return result.first() is not None
    except Exception:  # noqa: BLE001 - 墓碑读失败不阻断既有 fail-open 过渡语义
        logger.debug("purge record lookup skipped", extra={"subject_id": subject_id})
        return False


def assert_principal_active(status_state: str | None) -> None:
    """主体状态门禁（user/agent 共用）：非 active 一律 401 AUTH_PRINCIPAL_DISABLED.

    Args:
        status_state: users.status_state（存量 NULL 视作 active，迁移前兼容）。

    Raises:
        BaseError: 主体非 active → AUTH_PRINCIPAL_DISABLED。
    """
    current_state = status_state or STATUS_STATE_ACTIVE
    if current_state != STATUS_STATE_ACTIVE:
        raise BaseError(
            ErrorCode.AUTH_PRINCIPAL_DISABLED,
            "principal is not active",
            detail={"status_state": current_state},
        )


async def load_principal_snapshot(
    session: Any, subject_id: int
) -> dict[str, Any] | None:
    """读取主体验证快照（缓存优先，未命中读库并回填，TTL 60s）.

    Args:
        session: 数据库会话（AuthMiddleware 专用会话或请求级 get_db 会话）。
        subject_id: 本地主体 id（users.id）。

    Returns:
        dict: {subject_type, status_state, token_version, username, tenant_id,
        tenant_code}；主体行不存在（已 purge/软删）返回 None。
    """
    cached = _cache_get_snapshot(subject_id)
    if cached is not None:
        return cached

    user = await session.get(User, subject_id)
    if user is None or user.is_deleted:
        # 主体已物理清除（purged）/软删 → 无行可验；顺带清可能的脏缓存
        invalidate_principal_cache(subject_id)
        return None
    snapshot = {
        "subject_type": user.subject_type or SUBJECT_TYPE_USER,
        "status_state": user.status_state or STATUS_STATE_ACTIVE,
        "token_version": user.token_version or 0,
        "username": user.username,
        "tenant_id": user.tenant_id,
        "tenant_code": user.tenant_code,
    }
    _cache_set_snapshot(subject_id, snapshot)
    return snapshot


def _version_enforcement_enabled() -> bool:
    """版本强校验开关（两段式发布第二段；默认关，草案 §6.2/§12.1 风险 1）."""
    from openbase.settings import get_settings

    return bool(get_settings().enforce_token_version)


async def verify_principal(session: Any, payload: dict[str, Any]) -> dict[str, Any] | None:
    """共享主体验证器：主体存在 + 状态 active +（开关开时）tvn 与版本一致.

    AuthMiddleware.dispatch / get_current_user / 依赖层共用本函数（草案 §5.1），
    消除「仅验签不验状态」路径。

    Args:
        session: 数据库会话。
        payload: 已验签解码的 access JWT payload。

    Returns:
        主体快照 dict（本地主体校验通过）；以下情形返回 None（调用方放行，过渡兼容）：
        - sub 非数字（OIDC 直签 / 外域主体，无本地主体行）；
        - DB 读不可达（fail-open，与 login 内存降级语义一致）；
        - 主体行不存在（purged/降级内存用户，WARN 告警后放行，T6 purge 收口）。
        注意：返回 None 不代表校验通过，仅表示「无法确认状态」。

    Raises:
        BaseError: AUTH_TOKEN_INVALID（缺 sub）；AUTH_PRINCIPAL_DISABLED
            （主体非 active）；AUTH_TOKEN_STALE（enforce 开启且 claim tvn 落后）。
    """
    subject = payload.get("sub")
    if subject is None:
        raise BaseError(ErrorCode.AUTH_TOKEN_INVALID, "token missing subject")

    subject_text = str(subject)
    if not subject_text.isdigit():
        # OIDC 直签 / 非本地主体（如 IdP sub 字符串）：无本地主体行可校验，放行
        return None

    try:
        snapshot = await load_principal_snapshot(session, int(subject_text))
    except Exception as exc:  # noqa: BLE001 - DB 不可达
        # P2-1 T2 D-V1/D-V3（§5.1）：无委托 → fail-open + WARN（login 同语义）；
        # 携带 on_behalf_of → fail-closed 403（无法证明委托不变式即拒绝）。
        logger.warning(
            "principal verify db read failed; degrade pass-through",
            extra={"subject": subject_text, "error": str(exc) or exc.__class__.__name__},
        )
        try:
            await session.rollback()
        except Exception:  # noqa: BLE001 - rollback 失败不阻断裁定
            pass
        if _payload_has_delegation(payload):
            _metric_increment("delegation_denied_db")
            raise BaseError(
                ErrorCode.PERM_DELEGATION_VERIFY_UNAVAILABLE,
                "delegation verification unavailable: database degraded",
                detail={"subject": subject_text, "reason": "db_unavailable"},
            ) from exc
        _metric_increment("db_degraded")
        return None

    if snapshot is None:
        # P2-1 T2 D-V2（§5.1）：主体行缺失（无墓碑）。
        # - 携带 on_behalf_of → 403（委托目标存在性不可证即拒，fail-closed）；
        # - 无委托：区分「曾存在后被 purge」与「无本地行（OIDC 直签/降级内存用户）」：
        #   purge_records 墓碑命中（T6 收口）→ 401 AUTH_PRINCIPAL_DISABLED；
        #   无墓碑 → T3 遗留 fail-open 过渡窗口保持（WARN 计数）。
        if _payload_has_delegation(payload):
            _metric_increment("delegation_denied_row_missing")
            raise BaseError(
                ErrorCode.PERM_DELEGATION_VERIFY_UNAVAILABLE,
                "delegation verification unavailable: principal row missing",
                detail={
                    "subject": subject_text,
                    "reason": "row_missing_with_on_behalf_of",
                },
            )
        if await _subject_was_purged(session, int(subject_text)):
            raise BaseError(
                ErrorCode.AUTH_PRINCIPAL_DISABLED,
                "principal has been purged",
                detail={"status_state": STATUS_STATE_PURGED, "subject_id": int(subject_text)},
            )
        _metric_increment("row_missing")
        logger.warning(
            "principal row missing; unverifiable token pass-through",
            extra={"subject": subject_text},
        )
        return None

    # ① 主体状态门禁（默认即生效，不依赖开关）：非 active → 401 AUTH_PRINCIPAL_DISABLED
    assert_principal_active(snapshot["status_state"])

    # ② token 版本强校验（enforce_token_version 开关，默认 False）：
    #    - claim 无 tvn（v0 存量形态）→ 兼容放行（草案 §5.2/§6.2，刷新后已升级）；
    #    - claim tvn 与主体版本不一致（落后任意整数）→ 401 AUTH_TOKEN_STALE。
    if _version_enforcement_enabled():
        claim_tvn = payload.get("tvn")
        if claim_tvn is not None and int(claim_tvn) != int(snapshot["token_version"]):
            raise BaseError(
                ErrorCode.AUTH_TOKEN_STALE,
                "token version is stale; re-login required",
                detail={
                    "claim_tvn": claim_tvn,
                    "expected_token_version": snapshot["token_version"],
                },
            )

    # ③ 委托链逐跳重校验（U1 T4，草案 §7.3/§11 T4-3/4）：返回快照后追加校验——
    #    若 token 携带 on_behalf_of，其域不变式/委托目标状态每请求与 DB 对账
    #    （claim 域被篡改/替换或委托目标停用 → 403，R-M4-2 逐跳重校验骨架）。
    await verify_request_delegation(session, payload, snapshot)
    return snapshot


__all__ = [
    "PRINCIPAL_CACHE_TTL_SECONDS",
    "assert_principal_active",
    "get_verdict_metrics",
    "invalidate_principal_cache",
    "load_principal_snapshot",
    "verify_principal",
]
