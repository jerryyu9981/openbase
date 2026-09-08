"""verify-env settings snapshot 采集（P2-1 §9.2 / T9，OB-9）.

verify-env.ps1 的**纯数据源**：将当前环境（settings + 连通性 + DB 检查位 +
dps_code_map 对账事实）采样为一份 JSON snapshot，供 PowerShell 契约比对消费。
设计上把全部 I/O（TCP 探活 / DB 连接）收敛在本模块：

- 配置键：contract.json config_single_source 对应键原值（jwt_secret 仅存
  ``jwt_secret_ok`` 布尔，**不落明文密钥**，AGENTS 日志/敏感数据纪律）；
- 白名单：trusted_proxy_sources_list（settings 解析结果）；
- upstream 可达性：对 contract.upstreams 的 url 做 TCP 探活（best-effort）；
- DB 检查位：连接 + tenants.code 抽样（配合 OB-7 登记；失败仅置位不抛错）；
- dps_code_map 对账事实：entries 数/校验错误/冲突（复用 dps_code_map 模块纯函数）。

用法::

    python scripts/verify-env/snapshot.py [--out snapshot.json]
    python scripts/verify-env/snapshot.py --out snapshot.json --skip-network --skip-db

退出码：0 = 采样完成；1 = 采样失败（配置装载错误）。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import socket
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from openbase.modules.protocol_headers.dps_code_map import (  # noqa: E402
    dps_code_map_conflicts,
    parse_dps_code_map,
    validate_dps_code_map,
)
from openbase.settings import get_settings  # noqa: E402

_CONNECT_TIMEOUT_SECONDS = 1.5


def _probe_url(url: str) -> bool:
    """TCP 连通性探活（best-effort；非 http(s)/解析失败 → 视为不可探）."""
    if not url:
        return False
    try:
        parsed = urlsplit(url)
        host = parsed.hostname or ""
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError:
        return False
    if not host:
        return False
    try:
        with socket.create_connection((host, port), timeout=_CONNECT_TIMEOUT_SECONDS):
            return True
    except OSError:
        return False


async def _probe_db(db_url: str) -> tuple[bool, list[str]]:
    """DB 连接 + tenants.code 抽样（best-effort；OB-7 检查位）.

    Args:
        db_url: settings.db_url。

    Returns:
        (reachable, tenant_codes)：连接成功返回 (True, codes)；失败 (False, [])。
    """
    try:
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(db_url)
        try:
            async with engine.connect() as connection:
                result = await connection.execute(text("SELECT code FROM tenants"))
                rows = result.fetchall()
            return True, [str(row[0]) for row in rows if row[0] is not None]
        finally:
            await engine.dispose()
    except Exception:  # noqa: BLE001 - 检查位尽力探测，失败由 verify-env 记 WARN
        return False, []


def collect_snapshot(
    *,
    include_network: bool = True,
    include_db: bool = True,
) -> dict[str, Any]:
    """采集当前环境 snapshot（verify-env 契约比对数据源）.

    Args:
        include_network: 是否执行 upstream TCP 探活（离线跳过）。
        include_db: 是否执行 DB 检查位（离线跳过）。

    Returns:
        snapshot dict（结构见模块 docstring）。
    """
    settings = get_settings()
    config_keys: tuple[str, ...] = (
        "trusted_proxy_sources",
        "role_intertranslate",
        "dps_code_map",
        "service_account_subject_map",
        "enforce_org_alias",
        "enforce_token_version",
        "k03_bypass_whitelist",
        "strip_inbound_identity_headers",
        "enforce_inbound_identity_headers",
        "enforce_proxy_identity_headers",
        "db_url",
        "redis_url",
    )
    config: dict[str, Any] = {}
    for key in config_keys:
        config[key] = str(getattr(settings, key, "") or "")

    deprecated = settings.deprecated_dps_defaults()

    snapshot: dict[str, Any] = {
        "schema_version": 1,
        "source": "openbase.settings",
        "config": config,
        "trusted_proxy_sources_list": settings.trusted_proxy_sources_list,
        "deprecated_configured": deprecated,
        "jwt_secret_ok": len(settings.jwt_secret or "") >= 32,
    }

    upstream_urls: dict[str, str] = {}
    for entry in (
        {"url_key": "dps_upstream_base"},
        {"url_key": "llm_upstream_base"},
        {"url_key": "rag_upstream_base"},
        {"url_key": "memory_upstream_base"},
    ):
        url = str(getattr(settings, entry["url_key"], "") or "")
        upstream_urls[entry["url_key"]] = url
    snapshot["upstream_urls"] = upstream_urls
    if include_network:
        snapshot["upstreams_reachability"] = {
            url_key: _probe_url(url) for url_key, url in upstream_urls.items()
        }
    else:
        snapshot["upstreams_reachability"] = {}

    known_tenant_codes: list[str] | None = None
    db_reachable = False
    db_probed = False
    if include_db:
        db_probed = True
        db_reachable, known_tenant_codes = asyncio.run(
            _probe_db(str(getattr(settings, "db_url", "") or ""))
        )
        if not db_reachable:
            # DB 不可达：tenants.code 事实源不可用 → None（跳过命中校验而非误判未知）
            known_tenant_codes = None
    snapshot["db_checks"] = {
        "reachable": db_reachable,
        "probed": db_probed,
        "schema": getattr(settings, "db_schema", "openbase"),
        "note": "tenants.code 唯一事实源对账（配合 OB-7 登记）",
    }

    raw_map = str(getattr(settings, "dps_code_map", "") or "")
    baseline = parse_dps_code_map(raw_map)
    entries = [entry for entry in baseline.get("entries", []) if isinstance(entry, dict)]
    known_set = set(known_tenant_codes) if known_tenant_codes is not None else None
    snapshot["dps_code_map"] = {
        "entries_count": len(entries),
        "validation_errors": validate_dps_code_map(
            baseline, known_tenant_codes=known_set
        ),
        "conflicts": dps_code_map_conflicts(entries),
        "known_tenant_codes_from_db": known_tenant_codes is not None,
        "tenant_codes_from_db": known_tenant_codes,
    }
    return snapshot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="verify-env settings snapshot 采集")
    parser.add_argument("--out", default="", help="snapshot 输出 JSON 路径（缺省 stdout）")
    parser.add_argument("--skip-network", action="store_true", help="跳过 upstream TCP 探活")
    parser.add_argument("--skip-db", action="store_true", help="跳过 DB 检查位探测")
    args = parser.parse_args(argv)

    snapshot = collect_snapshot(
        include_network=not args.skip_network,
        include_db=not args.skip_db,
    )
    payload = json.dumps(snapshot, ensure_ascii=False, indent=2)
    if args.out:
        output_path = Path(args.out)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload, encoding="utf-8")
        print(f"[snapshot] {output_path}")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
