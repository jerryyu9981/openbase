"""dps org/tenant code→UUID 登记式基线对账脚本（P2-1 §7.2 / T7-7，OB-8）.

以 OpenBase ``tenants.code`` 为唯一事实源，对 ``settings.dps_code_map`` 登记式
基线执行对账：

- 结构/语义校验（schema_version/键非空/无重复 code/命中 tenants.code）；
- 冲突检测（R-L3-1 形态）：同 code 双映射不同 DPS 值 → 冲突项（S7 前清零）；
- deprecated ``dps_default_org_id/dps_default_tenant_id`` WARN 提示（T7-6）；
- 输出 ``audit_report.json``（同目录或 --report 指定）含 WARN/冲突清单。

用法::

    python scripts/audit_dps_code_map.py
    python scripts/audit_dps_code_map.py --map-json dps_code_map.json \\
        --tenants-json tenants.json --report out/audit_report.json

DB 位说明：未提供 ``--tenants-json`` 时尝试连接 ``OPENBASE_DB_URL`` 读取
``tenants.code``（best-effort；DB 不可达 → 空已知集 + WARN）。退出码：0 = 0 未决
冲突；1 = 存在未决冲突或校验错误（对账门禁，T7-7）。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from openbase.modules.protocol_headers.dps_code_map import (  # noqa: E402
    dps_code_map_conflicts,
    parse_dps_code_map,
    validate_dps_code_map,
)
from openbase.settings import get_settings  # noqa: E402


def _load_json_file(path: Path, *, allow_missing: bool = False) -> Any:
    """读取 JSON 文件（缺省 missing 即报错；allow_missing → None）. """
    if allow_missing and not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload


async def _load_known_tenant_codes(db_url: str) -> set[str]:
    """从数据库读取 tenants.code（唯一事实源；best-effort）.

    Args:
        db_url: settings.db_url（openbase 应用连接串）。

    Returns:
        tenants.code 集合；DB 不可达/失败 → 空集（调用方 WARN 提示走 --tenants-json）。
    """
    try:
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(db_url)
        try:
            async with engine.connect() as connection:
                result = await connection.execute(text("SELECT code FROM tenants"))
                rows = result.fetchall()
            return {str(row[0]) for row in rows if row[0] is not None}
        finally:
            await engine.dispose()
    except Exception as exc:  # noqa: BLE001 - 脚本尽力对账，失败给 WARN
        print(f"[WARN] tenants.code DB 读取失败（{exc}）；可用 --tenants-json 离线对账")
        return set()


def build_report(
    *,
    data: dict[str, Any],
    known_tenant_codes: set[str] | None,
    deprecated_defaults: dict[str, str],
) -> dict[str, Any]:
    """构造对账报告（校验错误 + 冲突 + deprecated 提示）.

    Args:
        data: 基线 dict（dps_code_map 解析值，含 schema_version/entries）。
        known_tenant_codes: tenants.code 已知集（None = 跳过命中校验）。
        deprecated_defaults: settings.deprecated_dps_defaults()。

    Returns:
        报告 dict（校验 errors/unresolved_conflicts/warns/汇总）。
    """
    errors: list[str] = []
    if known_tenant_codes is not None:
        errors = validate_dps_code_map(
            data, known_tenant_codes=known_tenant_codes
        )
    entries = [
        entry for entry in data.get("entries", []) if isinstance(entry, dict)
    ]
    conflicts = dps_code_map_conflicts(entries)
    warns = [
        f"{name}={value} deprecated: register in dps_code_map instead"
        for name, value in sorted(deprecated_defaults.items())
    ]
    return {
        "entries_count": len(entries),
        "known_tenant_codes": sorted(known_tenant_codes) if known_tenant_codes is not None else None,
        "validation_errors": errors,
        "unresolved_conflicts": conflicts,
        "deprecated_warns": warns,
        "report_ok": not errors and not conflicts,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="dps_code_map 登记式基线对账（以 OpenBase tenants.code 为唯一事实源）"
    )
    parser.add_argument("--map-json", default="", help="dps_code_map JSON 文件路径（缺省读 settings）")
    parser.add_argument("--tenants-json", default="", help="tenants.code 列表 JSON 文件（离线对账）")
    parser.add_argument("--report", default="", help="报告输出 JSON 路径（缺省 verify-env-report 风格打印）")
    args = parser.parse_args(argv)

    settings = get_settings()
    if args.map_json:
        payload = _load_json_file(Path(args.map_json))
        data = payload if isinstance(payload, dict) else parse_dps_code_map(str(payload))
    else:
        data = parse_dps_code_map(settings.dps_code_map)

    if args.tenants_json:
        tenant_codes = {str(code) for code in _load_json_file(Path(args.tenants_json))}
    else:
        tenant_codes = asyncio.run(_load_known_tenant_codes(settings.db_url)) or None

    deprecated_defaults = settings.deprecated_dps_defaults()
    report = build_report(
        data=data,
        known_tenant_codes=tenant_codes,
        deprecated_defaults=deprecated_defaults,
    )

    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"[report] {report_path}")

    print(
        f"entries={report['entries_count']} "
        f"validation_errors={len(report['validation_errors'])} "
        f"unresolved_conflicts={len(report['unresolved_conflicts'])} "
        f"deprecated_warns={len(report['deprecated_warns'])}"
    )
    for error in report["validation_errors"]:
        print(f"  [ERROR] {error}")
    for conflict in report["unresolved_conflicts"]:
        print(
            f"  [CONFLICT] tenant_code={conflict.get('tenant_code')} "
            f"mappings={json.dumps(conflict.get('mappings'), ensure_ascii=False)}"
        )
    for warn in report["deprecated_warns"]:
        print(f"  [WARN] {warn}")

    if report["validation_errors"] or report["unresolved_conflicts"]:
        print("[FAIL] 0 未决冲突门禁未通过")
        return 1
    print("[OK] 对账通过（0 未决冲突）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
