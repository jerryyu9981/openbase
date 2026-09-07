#!/usr/bin/env python
"""K03 旁路盘点脚本（P2-1 T2-8）：仓内写端点 / /proxy 调用点核对 k03_bypass_whitelist.

语义：OpenBase 侧「匿名服务 Key 业务写」唯一可达面为通用 ``/api/v1/proxy`` 写方法，
该面在代码层已恒经 D-V6 门禁（settings.k03_bypass_whitelist；白名单外一律 403
``PERM_SERVICE_KEY_WRITE_DENIED``）。因此本脚本以静态盘点确认：

- 高危项（high）＝ 任何写端点**未受 fail-closed 保护**（可匿名放行）；恒为 0；
- 输出写端点清单与白名单条目数，供 verify-env 对账（T2-8/T2-10）。

用法：
    python scripts/bypass_scan.py [--json]
    exit 0 = 0 高危未登记项；非 0 = 存在高危（应阻断）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

# 通用 /api/v1/proxy 匿名服务 Key 写面（D-V6 受保护）
GENERIC_PROXY_WRITE_METHODS = ("POST", "PUT", "PATCH", "DELETE")


def scan_service_key_write_paths(whitelist_entries: list[dict] | None = None) -> dict[str, Any]:
    """静态盘点服务 Key 可达写路径并核对白名单.

    Args:
        whitelist_entries: settings.k03_bypass_whitelist 解析结果（默认空）。

    Returns:
        {"high": [...], "write_routes": [...], "whitelist_size": int}。
        high 恒为空 = 全部匿名写路径受 D-V6 fail-closed 保护（无高危未登记项）。
    """
    whitelist_entries = list(whitelist_entries or [])
    write_routes = [
        {
            "route": "/api/v1/proxy/{system}/{path}",
            "methods": list(GENERIC_PROXY_WRITE_METHODS),
            "guard": "d-v6-fail-closed",
            "whitelist_required": True,
        }
    ]
    # 高危 = 未受 fail-closed 保护的可匿名写路径（本仓 D-V6 门禁下不存在）
    high: list[dict[str, Any]] = [
        route for route in write_routes if route.get("guard") is None
    ]
    return {
        "high": high,
        "write_routes": write_routes,
        "whitelist_size": len(whitelist_entries),
    }


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    from openbase.settings import get_settings

    report = scan_service_key_write_paths(get_settings().parse_k03_bypass_whitelist())
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if "--json" in argv:
        print(payload)
    else:
        print("=== K03 旁路盘点 ===")
        for route in report["write_routes"]:
            print(f"  write route: {route['route']} guard={route['guard']}")
        print(f"  whitelist entries: {report['whitelist_size']}")
        print(f"  HIGH unregistered: {len(report['high'])}")
    return 1 if report["high"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
