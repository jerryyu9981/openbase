"""导出审计真机验证脚本（方案 B：dps-proxy 导出 → OpenBase ``log.export`` 留痕）.

验证链路：
    1. 登录并调用 ``GET /api/v1/dps-proxy/portraits/export``；
    2. 在 OpenBase 库中查找 ``audit_logs(action='log.export')``（request_id 对齐）；
    3. 校验 detail：actor/source/filters/row_count/format + total/exported_rows/truncated；
    4. 调用 ``/api/v1/audit/chain/verify`` 校验链式哈希（无权限时记录 SKIP）；
    5. 断言 DPS ``platform.audit_logs`` 无 EXPORT（分工说明，不作为失败项）；
    6. 证据落盘 ``doc/test/evidence/portrait-waves/export-audit/``。

用法：
    python scripts/verify_export_audit.py
    python scripts/verify_export_audit.py --base-url http://127.0.0.1:8000

环境变量：
    OPENBASE_BASE_URL / OPENBASE_DB_URL（缺省回退 DATABASE_URL / POSTGRES_URL）
    OPENBASE_ADMIN_USER / OPENBASE_ADMIN_PASSWORD（缺省 admin/admin123，仅开发环境）
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any, Optional

import asyncpg

EVIDENCE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "doc",
    "test",
    "evidence",
    "portrait-waves",
    "export-audit",
)

checks: list[dict[str, Any]] = []


def _record(name: str, ok: bool, detail: str, severity: str = "critical") -> None:
    checks.append({"step": name, "ok": ok, "detail": detail, "severity": severity})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def _http(
    method: str,
    url: str,
    headers: Optional[dict[str, str]] = None,
    payload: Optional[dict[str, Any]] = None,
) -> tuple[int, dict[str, str], bytes]:
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()


def _json(payload: bytes) -> Any:
    try:
        return json.loads(payload.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None


async def _find_export_audit(db_url: str, request_id: str) -> tuple[str, dict[str, Any]] | None:
    conn = await asyncpg.connect(db_url)
    try:
        schemas = await conn.fetch(
            "SELECT table_schema FROM information_schema.tables "
            "WHERE table_name = 'audit_logs' ORDER BY table_schema"
        )
        fallback: tuple[str, dict[str, Any]] | None = None
        for row in schemas:
            schema = row["table_schema"]
            try:
                if request_id:
                    found = await conn.fetchrow(
                        f'SELECT * FROM "{schema}".audit_logs '
                        "WHERE action = 'log.export' AND request_id = $1 "
                        "ORDER BY id DESC LIMIT 1",
                        request_id,
                    )
                    if found:
                        return schema, dict(found)
                latest = await conn.fetchrow(
                    f'SELECT * FROM "{schema}".audit_logs '
                    "WHERE action = 'log.export' ORDER BY id DESC LIMIT 1"
                )
                if latest and fallback is None:
                    fallback = (schema, dict(latest))
            except asyncpg.PostgresError:
                continue
        return fallback
    finally:
        await conn.close()


async def _dps_export_count(db_url: str) -> int:
    conn = await asyncpg.connect(db_url)
    try:
        exists = await conn.fetchval(
            "SELECT to_regclass('platform.audit_logs') IS NOT NULL"
        )
        if not exists:
            return -1
        return int(
            await conn.fetchval(
                "SELECT COUNT(*) FROM platform.audit_logs WHERE action = 'EXPORT'"
            )
        )
    finally:
        await conn.close()


def _parse_detail(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except ValueError:
            return {}
    return {}


async def main() -> int:
    parser = argparse.ArgumentParser(description="导出审计真机验证")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("OPENBASE_BASE_URL", "http://127.0.0.1:8000"),
    )
    parser.add_argument(
        "--db-url",
        default=(
            os.environ.get("OPENBASE_DB_URL")
            or os.environ.get("DATABASE_URL")
            or os.environ.get("POSTGRES_URL")
        ),
    )
    parser.add_argument("--username", default=os.environ.get("OPENBASE_ADMIN_USER", "admin"))
    parser.add_argument(
        "--password", default=os.environ.get("OPENBASE_ADMIN_PASSWORD", "admin123")
    )
    args = parser.parse_args()
    if not args.db_url:
        print("FAIL: 未提供数据库连接串（--db-url 或 OPENBASE_DB_URL/DATABASE_URL/POSTGRES_URL）")
        return 1

    base = args.base_url.rstrip("/")
    status, _headers, payload = _http(
        "POST",
        f"{base}/api/v1/auth/login",
        {"Content-Type": "application/json"},
        {"username": args.username, "password": args.password},
    )
    login = _json(payload) or {}
    token = str(login.get("access_token") or "")
    _record("登录", status == 200 and bool(token), f"status={status}")
    if not token:
        return _emit(args.base_url)

    auth = {"Authorization": f"Bearer {token}"}
    status, headers, body = _http(
        "GET", f"{base}/api/v1/dps-proxy/portraits/export?page_size=10", auth
    )
    request_id = (
        headers.get("X-Request-Id")
        or headers.get("x-request-id")
        or ""
    )
    _record(
        "导出接口返回 CSV",
        200 <= status < 300 and body.startswith(b"\xef\xbb\xbf"),
        f"status={status} bytes={len(body)} request_id={request_id}",
    )

    await asyncio.sleep(1.0)
    located = await _find_export_audit(args.db_url, request_id)
    _record("存在 log.export 留痕", located is not None, "audit_logs 已定位" if located else "未找到")
    if not located:
        return _emit(args.base_url)

    schema, row = located
    detail = _parse_detail(row.get("detail"))
    row_request_id = str(row.get("request_id") or "")
    _record(
        "request_id 对齐",
        bool(request_id) and row_request_id == request_id,
        f"export={request_id or '<无>'} audit={row_request_id} schema={schema}",
    )
    _record(
        "留痕字段完整",
        all(key in detail for key in ("actor", "source", "filters", "row_count", "format")),
        json.dumps(detail, ensure_ascii=False)[:300],
    )
    _record(
        "来源与格式",
        detail.get("source") == "dps_proxy.portraits.export" and detail.get("format") == "csv",
        f"source={detail.get('source')} format={detail.get('format')}",
    )
    _record(
        "行数与截断",
        isinstance(detail.get("row_count"), int)
        and detail.get("exported_rows") == detail.get("row_count")
        and isinstance(detail.get("total"), int)
        and isinstance(detail.get("truncated"), bool),
        f"row_count={detail.get('row_count')} total={detail.get('total')} "
        f"truncated={detail.get('truncated')}",
    )
    filters = detail.get("filters")
    _record(
        "过滤条件已脱敏记录",
        isinstance(filters, dict),
        json.dumps(filters, ensure_ascii=False)[:200],
    )

    status, _h, chain_payload = _http(
        "GET", f"{base}/api/v1/audit/chain/verify?limit=500", auth
    )
    chain = _json(chain_payload) or {}
    chain_ok = bool((chain.get("data") or {}).get("ok"))
    chain_detail = (
        f"status={status} ok={chain_ok}"
        if status == 200
        else f"status={status}（权限不足则 SKIP）"
    )
    _record(
        "审计链校验",
        status == 200 and chain_ok,
        chain_detail,
        severity="critical" if status == 200 else "skip",
    )

    dps_count = await _dps_export_count(args.db_url)
    _record(
        "DPS 侧无 EXPORT（分工说明）",
        dps_count == 0,
        f"platform.audit_logs EXPORT={dps_count}（预期 0；导出由本仓生成）",
        severity="info",
    )
    return _emit(args.base_url)


def _emit(base_url: str) -> int:
    critical_failures = [
        item for item in checks if not item["ok"] and item["severity"] == "critical"
    ]
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = os.path.join(EVIDENCE_DIR, f"export-audit-{stamp}.json")
    summary = {
        "base_url": base_url,
        "generated_at": datetime.now().isoformat(),
        "total": len(checks),
        "failed": len(critical_failures),
        "checks": checks,
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    print(f"EVIDENCE={path}")
    print(f"SUMMARY={'PASS' if not critical_failures else 'FAIL'} "
          f"({len(checks) - len(critical_failures)}/{len(checks)})")
    return 0 if not critical_failures else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
