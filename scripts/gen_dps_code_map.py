"""从登记式 ``OPENBASE_DPS_CODE_MAP`` 生成 OpenLLM 侧码值互译表（B1）.

背景（《OpenBase-OpenRAG写判据与DPS码值桥接修复方案 v1.0.0》§5.1）：
OpenBase 的登记式基线（``dps_code_map``）是码值唯一事实源，OpenLLM 需要
``DPS_ORG_CODE_MAP`` / ``DPS_TENANT_CODE_MAP`` 两张「OpenBase 码 → DPS 值」表。
手工转写会漂移，故统一由本脚本生成。

输入（三选一，优先级从高到低）：
  1) ``--input <file>``：登记式 JSON 文件；
  2) ``OPENBASE_DPS_CODE_MAP`` 环境变量（登记式 JSON）；
  3) 标准输入。

登记式 JSON 形态::

    {"schema_version": 1,
     "source_of_truth": "openbase.tenants.code",
     "entries": [
       {"tenant_code": "tenant-1",
        "dps_org_id": "10000000-0000-0000-0000-000000000001",
        "dps_tenant_id": "20000000-0000-0000-0000-000000000001"}
     ]}

输出（``--format json``，默认）：一行 JSON 对象 ``{"org": {...}, "tenant": {...}}``
输出（``--format env``）：供 .env 直接粘贴的两行 ``KEY=VALUE``。

用法::

    python scripts/gen_dps_code_map.py --format env
    python scripts/gen_dps_code_map.py --input dps_code_map.json --format json

退出码：0=成功；2=输入缺失/非法（不产出半成品）。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any


def _read_source(path: str | None) -> str:
    if path:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    env_value = (os.environ.get("OPENBASE_DPS_CODE_MAP") or "").strip()
    if env_value:
        return env_value
    return sys.stdin.read().strip()


def build_maps(raw: str) -> tuple[dict[str, str], dict[str, str]]:
    """登记式 entries → (org_map, tenant_map)；同 code 冲突直接报错."""
    data: Any = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("输入必须为 JSON 对象")
    entries = data.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("entries 为空：没有可生成的码值映射")

    org_map: dict[str, str] = {}
    tenant_map: dict[str, str] = {}
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"entries[{index}] 不是对象")
        tenant_code = str(entry.get("tenant_code") or "").strip()
        dps_org_id = str(entry.get("dps_org_id") or "").strip()
        dps_tenant_id = str(entry.get("dps_tenant_id") or "").strip()
        if not tenant_code or not dps_org_id or not dps_tenant_id:
            raise ValueError(
                f"entries[{index}] 缺少 tenant_code/dps_org_id/dps_tenant_id"
            )
        if tenant_code in org_map and org_map[tenant_code] != dps_org_id:
            raise ValueError(f"tenant_code={tenant_code} 的 dps_org_id 冲突")
        if tenant_code in tenant_map and tenant_map[tenant_code] != dps_tenant_id:
            raise ValueError(f"tenant_code={tenant_code} 的 dps_tenant_id 冲突")
        org_map[tenant_code] = dps_org_id
        tenant_map[tenant_code] = dps_tenant_id
    return org_map, tenant_map


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 OpenLLM DPS 码值互译表")
    parser.add_argument("--input", help="登记式 JSON 文件路径")
    parser.add_argument(
        "--format", choices=("json", "env"), default="json", help="输出格式"
    )
    args = parser.parse_args()

    raw = _read_source(args.input)
    if not raw:
        print("错误：未提供登记式 JSON（--input / OPENBASE_DPS_CODE_MAP / stdin）", file=sys.stderr)
        return 2
    try:
        org_map, tenant_map = build_maps(raw)
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2

    org_json = json.dumps(org_map, ensure_ascii=False, sort_keys=True)
    tenant_json = json.dumps(tenant_map, ensure_ascii=False, sort_keys=True)
    if args.format == "env":
        print(f"DPS_ORG_CODE_MAP={org_json}")
        print(f"DPS_TENANT_CODE_MAP={tenant_json}")
    else:
        print(json.dumps({"org": org_map, "tenant": tenant_map}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
