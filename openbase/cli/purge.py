"""openbase-cli identity purge 运维子命令（U1 T6，L1-2；设计草案 §9.2 CLI 入口）.

设计草案 §9.2 入口：CLI 子命令 ``identity purge``（显式合规触发 purge 任务）。
授权码属罕见合规操作的二次授权凭证，由 CLI/服务层签发（短 TTL 单次有效），
执行 purge 时携带授权码 + 影响范围报告确认哈希。

子命令（``openbase-cli identity ...`` 或 ``python -m openbase.cli.main identity ...``）：
- ``purge-authorize --subject-id <id> [--subject-type user|agent]
  [--tenant-code <code>] [--ttl-seconds <s>]`` —— 对 deactivated 主体签发一次性
  purge 授权码并输出影响范围报告（code / scope_report_hash / expires_at）；
- ``purge --subject-id <id> [--subject-type user|agent]
  --authorization-code <code> --scope-report-hash <hash> [--tenant-code <code>]
  [--idempotency-key <key>]`` —— 执行 purge（物理清除 + 终态台账 + 审计留痕）。

本模块不导入任何 DB 单例（会话在命令执行时才懒初始化），import 期零副作用。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

PURGE_SUBJECT_CHOICES = ("user", "agent")


def _default_ttl() -> int:
    from openbase.modules.identity.purge import PURGE_AUTHORIZATION_TTL_SECONDS

    return PURGE_AUTHORIZATION_TTL_SECONDS


def _print_result(payload: dict[str, Any]) -> None:
    """以 JSON 输出命令结果（ensure_ascii=False 保中文；datetime 序列化为 ISO）. """
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def _print_error(exc: BaseException) -> None:
    code = getattr(exc, "code", "CLI_ERROR")
    message = str(exc)
    print(json.dumps({"code": str(code), "message": message}, ensure_ascii=False), file=sys.stderr)


def _tenant_guard(tenant_code: str | None, subject_tenant_code: str | None) -> None:
    """CLI 租户护栏：--tenant-code 提供时须与主体归属租户一致（防跨租户误触）."""
    if tenant_code is not None and subject_tenant_code != tenant_code:
        raise ValueError(
            f"tenant_code mismatch: subject belongs to {subject_tenant_code!r}, "
            f"got {tenant_code!r}"
        )


async def _run_authorize(args: argparse.Namespace) -> dict[str, Any]:
    from openbase.core.db.session import get_session_factory
    from openbase.modules.identity.purge import IdentityPurgeService

    async with get_session_factory()() as session:
        ttl_seconds = args.ttl_seconds or _default_ttl()
        issued = await IdentityPurgeService.issue_authorization(
            session,
            subject_id=args.subject_id,
            subject_type=args.subject_type,
            ttl_seconds=ttl_seconds,
        )
        _tenant_guard(args.tenant_code, issued.tenant_code)
        await session.commit()
        return {
            "ok": True,
            "subject_id": issued.subject_id,
            "subject_type": issued.subject_type,
            "username": issued.username,
            "tenant_code": issued.tenant_code,
            "purge_authorization_code": issued.authorization_code,
            "expires_at": issued.expires_at.isoformat(),
            "scope_report_hash": issued.scope_report_hash,
            "scope_report": issued.scope_report,
        }


async def _run_purge(args: argparse.Namespace) -> dict[str, Any]:
    from openbase.core.db.session import get_session_factory
    from openbase.modules.identity.purge import IdentityPurgeService

    async with get_session_factory()() as session:
        result = await IdentityPurgeService.execute_purge(
            session,
            subject_id=args.subject_id,
            subject_type=args.subject_type,
            authorization_code=args.authorization_code,
            scope_report_hash=args.scope_report_hash,
            idempotency_key=getattr(args, "idempotency_key", None),
        )
        _tenant_guard(args.tenant_code, result.tenant_code)
        await session.commit()
        return {
            "ok": True,
            "purged": True,
            "subject_id": result.subject_id,
            "subject_type": result.subject_type,
            "username": result.username,
            "tenant_code": result.tenant_code,
            "previous_state": result.previous_state,
            "status_state": result.status_state,
            "scope_report_hash": result.scope_report_hash,
            "deleted_counts": result.deleted_counts,
            "audit_log_id": result.audit_log_id,
        }


def cmd_purge_authorize(args: argparse.Namespace) -> int:
    """identity purge-authorize：签发一次性 purge 授权码 + 影响范围报告."""
    try:
        _print_result(asyncio.run(_run_authorize(args)))
    except Exception as exc:  # noqa: BLE001 - CLI 边界统一收敛错误输出
        _print_error(exc)
        return 1
    return 0


def cmd_purge_execute(args: argparse.Namespace) -> int:
    """identity purge：执行 purge（显式合规触发；物理清除 + 审计留痕）."""
    try:
        _print_result(asyncio.run(_run_purge(args)))
    except Exception as exc:  # noqa: BLE001 - CLI 边界统一收敛错误输出
        _print_error(exc)
        return 1
    return 0


def add_identity_purge_subparsers(parser: argparse.ArgumentParser) -> None:
    """向 openbase-cli 注册 ``identity`` 子命令组（purge-authorize / purge）.

    Args:
        parser: 已构建 openbase-cli 顶层 parser（含既有 create-* 子命令）。
    """
    identity_sub = parser.add_subparsers(dest="identity_command", required=True)

    p_authorize = identity_sub.add_parser(
        "purge-authorize",
        help="对 deactivated 主体签发一次性 purge 授权码 + 影响范围报告",
    )
    p_authorize.add_argument("--subject-id", type=int, required=True)
    p_authorize.add_argument(
        "--subject-type", default="user", choices=list(PURGE_SUBJECT_CHOICES)
    )
    p_authorize.add_argument("--tenant-code", default=None, help="租户护栏（须与主体一致）")
    p_authorize.add_argument(
        "--ttl-seconds", type=int, default=None, help="授权码有效期秒数（默认 600s）"
    )
    p_authorize.set_defaults(func=cmd_purge_authorize)

    p_purge = identity_sub.add_parser("purge", help="执行 purge（显式合规触发）")
    p_purge.add_argument("--subject-id", type=int, required=True)
    p_purge.add_argument(
        "--subject-type", default="user", choices=list(PURGE_SUBJECT_CHOICES)
    )
    p_purge.add_argument("--authorization-code", required=True)
    p_purge.add_argument("--scope-report-hash", required=True)
    p_purge.add_argument("--tenant-code", default=None, help="租户护栏（须与主体一致）")
    p_purge.add_argument("--idempotency-key", default=None)
    p_purge.set_defaults(func=cmd_purge_execute)


__all__ = [
    "PURGE_SUBJECT_CHOICES",
    "add_identity_purge_subparsers",
    "cmd_purge_authorize",
    "cmd_purge_execute",
]
