#!/usr/bin/env python
"""B1 影子期 would_deny 观测聚合（只读）.

设计依据
--------
- 上游：``config/rbac_permission_model.json``（role_to_permissions / modules，判定消化率）；
- 派单：《OpenBase-B1派单-OpenLLM授权接线》回执——两段开关
  ``RBAC_PERMISSION_SHADOW=true``（只审计不拒绝，输出 ``rbac_decision=would_deny``）、
  ``RBAC_PERMISSION_ENFORCE=false``；
- 影子期出口门禁（模型 ``rollout.phase_1_shadow.exit_gate``）：**消化率 100% 且无未归类调用方**。

输入
----
OpenLLM 结构化日志（JSON Lines，``--log`` 指定）。本脚本对格式**容错解析**：
- 判定字段 ``rbac_decision``（别名 decision/rbac_result…；亦支持从 ``message`` 文本
  ``rbac_decision=would_deny`` 正则提取）；
- 端点/角色/主体/权限码/request_id 支持多别名与嵌套（rbac/request/headers/… 子对象）。

输出（只读，不写库、不改任何服务）
--------------------------------
按「端点 × 角色 × 权限码」聚合清单 + 计数 + 代表性 request_id 样例 + 消化率；``--json``
可将报告落盘为 JSON 证据。**消化率**定义：

- ``digestion_rate = classified_events / total_events``：能把每条 ``would_deny`` 归入模型
  已知角色（claim 可判定）的比例；未归类角色（不在 ``role_to_permissions``）计入
  ``unclassified_events``（对应门禁"无未归类调用方"）；
- ``model_allows_events``：归类后按模型**本应被允许**（该角色授予含该码或 ``*``）——这些正是
  需**消化**（播种权限矩阵或补角色绑定）的阻塞项；
- ``model_denies_events``：归类后按模型**本应被拒绝**——拒绝符合模型预期，无需动作。

用法::

    python scripts/rbac_shadow_observe.py --log logs/openllm/openllm-20261008.jsonl
    python scripts/rbac_shadow_observe.py --log sample.jsonl --json evidence/shadow.json
    python scripts/rbac_shadow_observe.py --log sample.jsonl --json     # 打印 JSON 到 stdout

退出码：``0`` = 聚合完成；``1`` = 输入缺失（日志文件不存在）。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = ROOT / "config" / "rbac_permission_model.json"

SCHEMA_VERSION = 1
TOOL = "rbac_shadow_observe.py"
WILDCARD = "*"
WOULD_DENY = "would_deny"
UNKNOWN = "<unknown>"
DEFAULT_SAMPLE_SIZE = 3

EXIT_OK = 0
EXIT_FAIL = 1

_DECISION_IN_TEXT = re.compile(r"rbac_decision\s*=\s*([A-Za-z_\-]+)")

_DECISION_ALIASES = ("rbac_decision", "decision", "rbac_result", "permission_decision")
_ENDPOINT_ALIASES = ("endpoint", "path", "route", "url", "request_path")
_METHOD_ALIASES = ("method", "http_method", "verb")
_ROLE_ALIASES = ("role", "user_role", "x_user_role", "role_code")
_SUBJECT_ALIASES = ("subject", "subject_id", "user", "user_id", "username", "principal")
_PERMISSION_ALIASES = (
    "required_permission",
    "permission",
    "permission_code",
    "required_code",
    "required",
    "code",
)
_REQUEST_ID_ALIASES = ("request_id", "requestId", "req_id", "rid")

# 允许在嵌套子对象中查找上述字段（OpenLLM 日志可能分组）。
_NESTED_KEYS = ("rbac", "request", "http", "headers", "user")


class ObserveError(Exception):
    """观测输入错误（如日志文件不存在）."""


def load_model(path: str | Path) -> dict[str, Any]:
    """读取权限模型 JSON（判定消化率的事实源）."""
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _lookup(record: dict[str, Any], aliases: tuple[str, ...]) -> Any:
    """按别名在顶层及嵌套子对象中查值（取首个非空）."""
    for key in aliases:
        value = record.get(key)
        if value not in (None, ""):
            return value
    for nested_key in _NESTED_KEYS:
        nested = record.get(nested_key)
        if isinstance(nested, dict):
            for key in aliases:
                value = nested.get(key)
                if value not in (None, ""):
                    return value
    return None


def _normalize_decision(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).strip().lower().replace("-", "_").replace(" ", "_")


def _extract_decision(record: dict[str, Any]) -> str | None:
    """提出 rbac 判定（支持字段别名与 message 文本内嵌）."""
    decision = _normalize_decision(_lookup(record, _DECISION_ALIASES))
    if decision is None:
        for candidate in (record.get("message"), record.get("msg")):
            if isinstance(candidate, str):
                match = _DECISION_IN_TEXT.search(candidate)
                if match:
                    decision = _normalize_decision(match.group(1))
                    break
    return decision


def parse_record(record: Any) -> dict[str, Any] | None:
    """把单行日志对象解析为 would_deny 事件（非本次决策行 → None）."""
    if not isinstance(record, dict):
        return None
    if _extract_decision(record) != WOULD_DENY:
        return None

    method = _lookup(record, _METHOD_ALIASES)
    endpoint = _lookup(record, _ENDPOINT_ALIASES)
    role = _lookup(record, _ROLE_ALIASES)
    subject = _lookup(record, _SUBJECT_ALIASES)
    permission = _lookup(record, _PERMISSION_ALIASES)
    request_id = _lookup(record, _REQUEST_ID_ALIASES)

    return {
        "endpoint": str(endpoint) if endpoint is not None else UNKNOWN,
        "method": str(method) if method is not None else None,
        "role": str(role) if role is not None else UNKNOWN,
        "subject": str(subject) if subject is not None else UNKNOWN,
        "permission": str(permission) if permission is not None else UNKNOWN,
        "request_id": str(request_id) if request_id is not None else UNKNOWN,
    }


def parse_lines(text: str) -> tuple[list[dict[str, Any]], int]:
    """解析 JSON Lines：返回 ``(would_deny 事件, 跳过行数)``.

    跳过行 = 非 JSON / 非对象行；合法但非 would_deny 的行不计入跳过。
    """
    events: list[dict[str, Any]] = []
    skipped = 0
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            skipped += 1
            continue
        if not isinstance(payload, dict):
            skipped += 1
            continue
        event = parse_record(payload)
        if event is not None:
            events.append(event)
    return events, skipped


def aggregate(
    events: list[dict[str, Any]],
    model: dict[str, Any],
    *,
    skipped_lines: int = 0,
    model_path: str = "",
    log_path: str = "",
    sample_size: int = DEFAULT_SAMPLE_SIZE,
) -> dict[str, Any]:
    """按「端点 × 角色 × 权限码」聚合 + 消化率计算."""
    role_to_permissions = model.get("role_to_permissions") or {}
    known_codes: set[str] = set()
    for module in (model.get("modules") or {}).values():
        known_codes.update(module.get("codes") or [])

    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for event in events:
        key = (event["endpoint"], event["role"], event["permission"])
        grouped.setdefault(key, []).append(event)

    groups: list[dict[str, Any]] = []
    classified = 0
    unclassified = 0
    model_allows = 0
    model_denies = 0
    unclassified_roles: dict[str, int] = {}

    for (endpoint, role, permission), items in sorted(grouped.items()):
        count = len(items)
        role_known = role in role_to_permissions
        if role_known:
            grants = role_to_permissions[role] or []
            permits: bool | None = WILDCARD in grants or permission in grants
        else:
            permits = None

        if role_known:
            classified += count
            if permits:
                model_allows += count
            else:
                model_denies += count
        else:
            unclassified += count
            unclassified_roles[role] = unclassified_roles.get(role, 0) + count

        samples = list(dict.fromkeys(item["request_id"] for item in items))[:sample_size]
        groups.append(
            {
                "endpoint": endpoint,
                "role": role,
                "permission": permission,
                "count": count,
                "role_known": role_known,
                "model_allows": permits,
                "permission_known": permission in known_codes or permission == WILDCARD,
                "samples": samples,
            }
        )

    total = len(events)
    return {
        "schema_version": SCHEMA_VERSION,
        "tool": TOOL,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": model_path,
        "log": log_path,
        "totals": {"would_deny": total, "groups": len(groups)},
        "skipped_lines": skipped_lines,
        "digestion": {
            "digestion_rate": round(classified / total, 4) if total else 0.0,
            "classified_events": classified,
            "unclassified_events": unclassified,
            "model_allows_events": model_allows,
            "model_denies_events": model_denies,
        },
        "unclassified_roles": unclassified_roles,
        "groups": groups,
    }


def observe(
    log_path: str | Path,
    model_path: str | Path = DEFAULT_MODEL,
    *,
    sample_size: int = DEFAULT_SAMPLE_SIZE,
) -> dict[str, Any]:
    """读取日志并聚合（只读）.

    Raises:
        ObserveError: 日志文件不存在。
    """
    path = Path(log_path)
    if not path.exists():
        raise ObserveError(f"日志文件不存在：{path}")

    model = load_model(model_path)
    text = path.read_text(encoding="utf-8", errors="replace")
    events, skipped = parse_lines(text)
    return aggregate(
        events,
        model,
        skipped_lines=skipped,
        model_path=str(model_path),
        log_path=str(path),
        sample_size=sample_size,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "B1 影子期观测聚合：把 OpenLLM rbac_decision=would_deny 日志聚合为"
            "端点×角色×权限码清单 + 计数 + 样例 + 消化率（只读）"
        )
    )
    parser.add_argument("--log", required=True, help="OpenLLM 结构化日志路径（JSON Lines）")
    parser.add_argument("--model", default=str(DEFAULT_MODEL), help="权限模型 JSON（判定消化率）")
    parser.add_argument(
        "--json",
        nargs="?",
        const="-",
        default=None,
        help="打印/落盘 JSON 证据：`--json`=打印到 stdout；`--json <path>`=落盘到文件",
    )
    parser.add_argument(
        "--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE, help="每组代表性 request_id 样例数"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 入口；返回统一退出码（0=PASS / 1=FAIL）."""
    args = _build_parser().parse_args(argv)
    try:
        report = observe(args.log, args.model, sample_size=args.sample_size)
    except ObserveError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return EXIT_FAIL

    totals = report["totals"]
    digestion = report["digestion"]
    print(
        f"[{TOOL}] log={report['log']} would_deny={totals['would_deny']} "
        f"groups={totals['groups']} digestion_rate={digestion['digestion_rate']:.2%} "
        f"unclassified={digestion['unclassified_events']} skipped_lines={report['skipped_lines']}"
    )
    for group in report["groups"]:
        print(
            f"  {group['endpoint']} | {group['role']} | {group['permission']} × {group['count']} "
            f"(model_allows={group['model_allows']}, samples={','.join(group['samples'])})"
        )

    if args.json is not None:
        payload = json.dumps(report, ensure_ascii=False, indent=2)
        if args.json == "-":
            print(payload)
        else:
            out = Path(args.json)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(payload + "\n", encoding="utf-8")
            print(f"  证据已落盘：{out}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
