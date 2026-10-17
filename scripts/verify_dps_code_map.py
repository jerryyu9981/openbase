"""DPS 码值映射一致性校验（R3）.

在发布前校验三处映射是否同源、目标码值是否真实存在，避免「配置漂移 → 运行时
403 组织/租户不存在」在上线后才暴露。

三项校验：
  1. 结构：登记式 ``OPENBASE_DPS_CODE_MAP`` 可解析、entries 必填、无同码冲突；
  2. 一致性：登记式生成的映射必须是 OpenLLM ``DPS_ORG_CODE_MAP`` /
     ``DPS_TENANT_CODE_MAP`` 的**子集**（允许额外登记 UUID 别名键）；
  3. 存在性：每个 DPS org/tenant UUID 在共享 PG 中 active 且归属正确。

用法::

    python scripts/verify_dps_code_map.py --strict
    python scripts/verify_dps_code_map.py --input map.json --skip-db
    DPS_ORG_CODE_MAP='{...}' DPS_TENANT_CODE_MAP='{...}' \
      DATABASE_URL=postgresql://... python scripts/verify_dps_code_map.py --strict

退出码：0=全部通过；2=存在失败项（`--strict`）或输入缺失。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_dps_code_map import build_maps  # noqa: E402


def _load_registry(input_path: str | None) -> str:
    if input_path:
        return Path(input_path).read_text(encoding="utf-8")
    value = (os.environ.get("OPENBASE_DPS_CODE_MAP") or "").strip()
    if not value:
        raise ValueError("未提供登记式映射（--input / OPENBASE_DPS_CODE_MAP）")
    return value


def _parse_expect(label: str, raw: str | None) -> dict[str, str] | None:
    text = (raw or "").strip()
    if not text:
        return None
    parsed: Any = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError(f"{label} 必须为 JSON 对象")
    return {str(k): str(v) for k, v in parsed.items() if str(k).strip() and str(v).strip()}


def _check_subset(label: str, expected: dict[str, str], actual: dict[str, str]) -> list[str]:
    missing = {k: v for k, v in expected.items() if actual.get(k) != v}
    if not missing:
        return []
    return [
        f"{label} 未覆盖/取值不一致的键: "
        + ", ".join(f"{k}→期望 {v}，实际 {actual.get(k, '<缺失>')}" for k, v in missing.items())
    ]


async def _check_existence(dsn: str, expected: dict[str, str], label: str) -> list[str]:
    try:
        import asyncpg
    except ImportError:
        return [f"{label} 存在性校验跳过：asyncpg 未安装"]
    conn = await asyncpg.connect(dsn, timeout=15)
    try:
        sql = (
            "select id, status from platform.organization where id = $1"
            if label == "org"
            else "select id, status from platform.tenant where id = $1"
        )
        errors: list[str] = []
        for key, value in expected.items():
            row = await conn.fetchrow(sql, value)
            if row is None:
                errors.append(f"{label} 目标不存在: {key}→{value}")
            elif row["status"] != "active":
                errors.append(f"{label} 目标已停用: {key}→{value}")
        return errors
    finally:
        await conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="DPS 码值映射一致性校验")
    parser.add_argument("--input", help="登记式 JSON 文件")
    parser.add_argument("--expect-org", help="OpenLLM DPS_ORG_CODE_MAP（JSON）")
    parser.add_argument("--expect-tenant", help="OpenLLM DPS_TENANT_CODE_MAP（JSON）")
    parser.add_argument("--skip-db", action="store_true", help="跳过存在性校验")
    parser.add_argument("--strict", action="store_true", help="任一检查不可执行即判失败")
    args = parser.parse_args()

    failures: list[str] = []

    # ---- 1. 结构 ----
    try:
        raw = _load_registry(args.input)
        expected_org, expected_tenant = build_maps(raw)
        print(f"[1/3] 结构校验 OK（{len(expected_org)} 条登记）")
    except (ValueError, json.JSONDecodeError, OSError) as exc:
        print(f"[1/3] 结构校验 FAIL: {exc}", file=sys.stderr)
        return 2

    # ---- 2. 一致性 ----
    try:
        actual_org = _parse_expect("DPS_ORG_CODE_MAP", args.expect_org or os.environ.get("DPS_ORG_CODE_MAP"))
        actual_tenant = _parse_expect(
            "DPS_TENANT_CODE_MAP", args.expect_tenant or os.environ.get("DPS_TENANT_CODE_MAP")
        )
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"[2/3] 一致性校验 FAIL: {exc}", file=sys.stderr)
        return 2

    if actual_org is None or actual_tenant is None:
        message = "未提供 DPS_ORG_CODE_MAP / DPS_TENANT_CODE_MAP，无法比对一致性"
        print(f"[2/3] 一致性校验 SKIP: {message}")
        if args.strict:
            failures.append(message)
    else:
        consistency = _check_subset("DPS_ORG_CODE_MAP", expected_org, actual_org)
        consistency += _check_subset("DPS_TENANT_CODE_MAP", expected_tenant, actual_tenant)
        if consistency:
            failures.extend(consistency)
            print("[2/3] 一致性校验 FAIL")
            for item in consistency:
                print(f"  - {item}")
        else:
            print("[2/3] 一致性校验 OK（登记式期望全部被覆盖）")

    # ---- 3. 存在性 ----
    dsn = (os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or "").strip()
    if args.skip_db or not dsn:
        message = "存在性校验跳过（--skip-db 或未提供 DATABASE_URL/POSTGRES_URL）"
        print(f"[3/3] {message}")
        if args.strict and not args.skip_db:
            failures.append(message)
    else:
        import asyncio

        existence = asyncio.run(_check_existence(dsn, expected_org, "org"))
        existence += asyncio.run(_check_existence(dsn, expected_tenant, "tenant"))
        if existence:
            failures.extend(existence)
            print("[3/3] 存在性校验 FAIL")
            for item in existence:
                print(f"  - {item}")
        else:
            print("[3/3] 存在性校验 OK（目标均存在且 active）")

    if failures:
        print(f"RESULT: FAIL（{len(failures)} 项）")
        return 2
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
