#!/usr/bin/env python
"""人工端到端测试「响应级错误归因」分析器（C-17）.

设计依据：《OpenBase-人工端到端测试日志记录方案-v1.0.0》v1.1.0
- §5 批 4 C-17：按 step 输出「网关状态 → 上游状态 → 归属层 → 是否首现 → request_id → 建议动作」；
  输出 ``doc/test/evidence/manual/<run_id>-analysis.md``；
- §11.5 归因矩阵（本脚本的判定口径）：
  401 → 网关鉴权；403 ``PERM_UNTRUSTED_IDENTITY_HEADER`` → 网关信任链；
  403 ``PERM_SERVICE_KEY_WRITE_DENIED`` → 网关 K03；502 → 网络/上游不可达；
  上游 4xx/5xx + ``upstream_error_code`` → 上游子系统；网关 200 但响应不符预期 → 契约/数据；
- §11.6 输出口径：一行一结论 + 「首现」标记（避免把连锁噪音当新问题）。

输入面：C-1 落盘的 L1 记录（``logs/**/*.jsonl``），其中
用例上下文由 C-3 写入，响应观测字段由 C-15（``resp_*``）/C-16（``upstream_*``）写入。

红线（禁伪造 + 合规）：

- 只分析**真实存在**的记录；解析失败的行计入 ``skipped_lines`` 并跳过；
- 无任何带用例上下文的记录 → ``status=PENDING``、退出码 ``2``、**不产出**报告文件；
- 报告只含状态码/摘要/``request_id``/建议，**不含响应明文**（``resp_summary`` 一律不引用，
  与 D-5 响应采集红线一致）。

用法::

    python scripts/test_log_analyze.py                                   # 分析全部轮次
    python scripts/test_log_analyze.py --run-id run-20260914-0100
    python scripts/test_log_analyze.py --logs-root logs --out-dir doc/test/evidence/manual
    python scripts/test_log_analyze.py --run-id run-1 --json

统一退出码：``0`` = 无失败步骤；``1`` = 存在失败步骤；``2`` = PENDING（无记录 / 目录不可达）。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOGS_ROOT = ROOT / "logs"
DEFAULT_OUT_DIR = ROOT / "doc" / "test" / "evidence" / "manual"
SCHEMA_VERSION = 1
TOOL = "test_log_analyze.py"
ALL_RUNS = "all"

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_PENDING = 2

# 记录识别：C-1 formatter 必填字段
_TS_KEY = "ts"
_MESSAGE_KEY = "message"

# 归属层名称（与方案 §11.5 表格逐行对齐）
LAYER_GATEWAY_AUTH = "网关鉴权"
LAYER_GATEWAY_TRUST = "网关信任链"
LAYER_GATEWAY_K03 = "网关 K03"
LAYER_GATEWAY_PERM = "网关权限"
LAYER_NETWORK = "网络/上游不可达"
LAYER_UPSTREAM = "上游子系统"
LAYER_GATEWAY_BUSINESS = "网关业务"
LAYER_GATEWAY_SYSTEM = "网关/系统"
LAYER_OK = "无错误"

# 每个归属层的建议动作（可执行、指向下一跳证据）
LAYER_SUGGESTIONS: dict[str, str] = {
    LAYER_GATEWAY_AUTH: "检查是否携带 JWT（或改走 ob_k_/sk-agent 服务通道）",
    LAYER_GATEWAY_TRUST: "该页应走 JWT 或经网关代理，勿直连带身份头",
    LAYER_GATEWAY_K03: "写操作需 sk-agent-* 服务账号或登记 k03_bypass_whitelist",
    LAYER_GATEWAY_PERM: "核对账号权限码与角色配置",
    LAYER_NETWORK: "检查上游进程/端口（service-orchestrator status）",
    LAYER_UPSTREAM: "查上游日志（同 request_id）→ 该仓错误码表",
    LAYER_GATEWAY_BUSINESS: "按错误码核对请求参数与业务前置条件",
    LAYER_GATEWAY_SYSTEM: "查 OpenBase 服务日志 err.log（同 request_id）",
    LAYER_OK: "无需动作",
}

# 网关层错误码前缀/精确码（命中即归因网关，不再下探上游）
_GATEWAY_CODE_PREFIXES: tuple[str, ...] = ("AUTH", "PARAM")
_GATEWAY_CODE_EXACT: dict[str, str] = {
    "PERM_UNTRUSTED_IDENTITY_HEADER": LAYER_GATEWAY_TRUST,
    "PERM_SERVICE_KEY_WRITE_DENIED": LAYER_GATEWAY_K03,
}
UPSTREAM_ERROR_CODE = "SYS_UPSTREAM_ERROR"


def _iter_jsonl_files(logs_root: Path) -> list[Path]:
    """列出待分析的 JSONL 文件（目录不存在 → 空列表）."""
    if not logs_root.exists():
        return []
    return sorted(path for path in logs_root.rglob("*.jsonl") if path.is_file())


def _parse_records(logs_root: Path) -> tuple[list[dict[str, Any]], int]:
    """解析全部 JSONL 文件.

    Returns:
        ``(records, skipped_lines)``；仅接收结构化日志行（含 ``ts`` 与 ``message``）。
    """
    records: list[dict[str, Any]] = []
    skipped = 0
    for path in _iter_jsonl_files(logs_root):
        for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue
            if not isinstance(payload, dict) or _TS_KEY not in payload or _MESSAGE_KEY not in payload:
                skipped += 1
                continue
            payload["_source"] = path.relative_to(logs_root).as_posix()
            records.append(payload)
    return records, skipped


def _is_failed(record: dict[str, Any]) -> bool:
    """失败判定：HTTP 状态码 ≥ 400 或显式 error 字段（与 C-7 聚合脚本同口径）."""
    status = record.get("status_code")
    if isinstance(status, int) and status >= 400:
        return True
    return bool(record.get("error"))


def _gateway_layer(error_code: str) -> str | None:
    """网关层错误码 → 归属层（非网关码 → None，允许继续下探上游）."""
    if error_code in _GATEWAY_CODE_EXACT:
        return _GATEWAY_CODE_EXACT[error_code]
    prefix = error_code.split("_", 1)[0]
    if prefix in _GATEWAY_CODE_PREFIXES:
        return LAYER_GATEWAY_AUTH
    if prefix == "PERM":
        return LAYER_GATEWAY_PERM
    return None


def attribute(record: dict[str, Any]) -> tuple[str, str]:
    """按方案 §11.5 矩阵判定「归属层 + 建议动作」.

    判定顺序：网关鉴权/权限码 → 上游 4xx/5xx → 502/上游不可达 → 网关 5xx → 网关 4xx → 无错误。

    Args:
        record: L1 记录（含 ``status_code``/``resp_error_code``/``upstream_*``）。

    Returns:
        ``(归属层, 建议动作)``。
    """
    status = record.get("status_code")
    status = status if isinstance(status, int) else 0
    error_code = str(record.get("resp_error_code") or "")

    layer = _gateway_layer(error_code)
    if layer is not None:
        return layer, LAYER_SUGGESTIONS[layer]

    upstream_status = record.get("upstream_status")
    if isinstance(upstream_status, int) and upstream_status >= 400:
        return LAYER_UPSTREAM, LAYER_SUGGESTIONS[LAYER_UPSTREAM]

    if status == 502 or error_code == UPSTREAM_ERROR_CODE:
        return LAYER_NETWORK, LAYER_SUGGESTIONS[LAYER_NETWORK]

    if status >= 500:
        return LAYER_GATEWAY_SYSTEM, LAYER_SUGGESTIONS[LAYER_GATEWAY_SYSTEM]

    if status >= 400:
        return LAYER_GATEWAY_BUSINESS, LAYER_SUGGESTIONS[LAYER_GATEWAY_BUSINESS]

    return LAYER_OK, LAYER_SUGGESTIONS[LAYER_OK]


def _group_steps(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按 ``(case_id, step_id)`` 分组（保留出现顺序；失败记录优先作为代表）."""
    grouped: dict[tuple[str, Any], list[dict[str, Any]]] = {}
    order: list[tuple[str, Any]] = []
    for record in records:
        key = (str(record.get("case_id") or "<unlabeled>"), record.get("step_id"))
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(record)

    steps: list[dict[str, Any]] = []
    first_failure_seen: set[str] = set()
    for key in order:
        entries = grouped[key]
        failed_entries = [entry for entry in entries if _is_failed(entry)]
        representative = failed_entries[0] if failed_entries else entries[-1]
        is_failed = bool(failed_entries)
        layer, suggestion = attribute(representative)
        case_id = key[0]
        is_first = False
        if is_failed and case_id not in first_failure_seen:
            is_first = True
            first_failure_seen.add(case_id)
        steps.append(
            {
                "case_id": case_id,
                "step_id": representative.get("step_id"),
                "gateway_status": representative.get("status_code"),
                "upstream_status": representative.get("upstream_status"),
                "layer": layer,
                "first_failure": is_first,
                "failed": is_failed,
                "request_id": representative.get("request_id"),
                "suggestion": suggestion,
                "resp_digest": representative.get("resp_digest"),
                "upstream_digest": representative.get("upstream_digest"),
                "upstream_error_code": representative.get("upstream_error_code"),
            }
        )
    return steps


def _cell(value: Any) -> str:
    """表格单元格渲染（None/空 → ``-``；竖线转义避免破表）."""
    if value is None or value == "":
        return "-"
    return str(value).replace("|", "\\|")


def render_markdown(run_id: str, steps: list[dict[str, Any]], skipped_lines: int) -> str:
    """渲染归因报告（Markdown；不含响应明文）."""
    failed_count = sum(1 for step in steps if step["failed"])
    lines: list[str] = [
        f"# {run_id} 错误归因分析（C-17）",
        "",
        "| 项 | 值 |",
        "|----|-----|",
        f"| 生成时间 | {datetime.now(timezone.utc).isoformat(timespec='seconds')} |",
        f"| 工具 | `{TOOL}`（schema {SCHEMA_VERSION}） |",
        f"| 轮次 | {run_id} |",
        f"| 步骤总数 | {len(steps)} |",
        f"| 失败步骤 | {failed_count} |",
        f"| 跳过行（解析失败） | {skipped_lines} |",
        "| 定位 | **补充证据**（人工记录，不参与门禁判定，方案 D-3） |",
        "",
        "## 1. 归因表（一行一结论）",
        "",
        "| case_id | step | 网关 | 上游 | 归属层 | 首现 | request_id | 建议动作 |",
        "|---------|:----:|:----:|:----:|--------|:----:|------------|----------|",
    ]
    for step in steps:
        lines.append(
            "| {case} | {step} | {gateway} | {upstream} | {layer} | {first} | {request_id} | {advice} |".format(
                case=_cell(step["case_id"]),
                step=_cell(step["step_id"]),
                gateway=_cell(step["gateway_status"]),
                upstream=_cell(step["upstream_status"]),
                layer=_cell(step["layer"]),
                first="是" if step["first_failure"] else "否",
                request_id=_cell(step["request_id"]),
                advice=_cell(step["suggestion"]),
            )
        )
    lines.extend(
        [
            "",
            "## 2. 证据引用（按 request_id 与摘要可比对，**不含响应明文**）",
            "",
            "| case_id | step | request_id | resp_digest | upstream_digest | upstream_error_code |",
            "|---------|:----:|------------|-------------|-----------------|---------------------|",
        ]
    )
    for step in steps:
        lines.append(
            "| {case} | {step} | {request_id} | {resp} | {upstream} | {code} |".format(
                case=_cell(step["case_id"]),
                step=_cell(step["step_id"]),
                request_id=_cell(step["request_id"]),
                resp=_cell(step["resp_digest"]),
                upstream=_cell(step["upstream_digest"]),
                code=_cell(step["upstream_error_code"]),
            )
        )
    lines.extend(
        [
            "",
            "## 3. 口径与边界",
            "",
            "- 判定依据：方案 §11.5 归因矩阵（网关鉴权/信任链/K03 → 网关层；502 → 网络/上游；",
            "  上游 4xx/5xx + `upstream_error_code` → 上游子系统；网关 200 → 契约/数据需人工比对）；",
            "- 「首现」= 该用例**第一个**失败步骤，用于避免把连锁噪音当作新问题；",
            "- 响应摘要（`resp_summary`/`upstream_body_summary`）**不进入本报告**（D-5 红线）；",
            "- 本报告为**补充证据**，最终判定以人工结论（`/system/test-records`）与自动化断言为准。",
            "",
        ]
    )
    return "\n".join(lines)


def _resolve_run_id(explicit: str | None, records: list[dict[str, Any]]) -> str:
    """确定报告适用的轮次名（用于文件名与标题）.

    ``--run-id`` 显式指定优先；否则**记录内只含单一 run_id** 时取该值（便于逐轮出报告）；
    多轮次混合（未过滤）→ ``all``。
    """
    if explicit:
        return explicit
    run_ids = sorted({str(record.get("run_id")) for record in records if record.get("run_id")})
    if len(run_ids) == 1:
        return run_ids[0]
    return ALL_RUNS


def main(argv: list[str] | None = None) -> int:
    """命令行入口（返回统一退出码 0/1/2）."""
    parser = argparse.ArgumentParser(
        description="人工端到端测试响应级错误归因分析器（C-17）"
    )
    parser.add_argument("--logs-root", default=str(DEFAULT_LOGS_ROOT), help="日志根目录")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="报告输出目录")
    parser.add_argument("--run-id", default=None, help="仅分析指定轮次（缺省全部）")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出汇总到 stdout")
    args = parser.parse_args(argv)

    logs_root = Path(args.logs_root)
    records, skipped = _parse_records(logs_root)
    selected = [
        record
        for record in records
        if record.get("case_id") and (args.run_id is None or record.get("run_id") == args.run_id)
    ]

    run_id = _resolve_run_id(args.run_id, selected)
    if not selected:
        summary = {
            "schema_version": SCHEMA_VERSION,
            "tool": TOOL,
            "status": "PENDING",
            "run_id": run_id,
            "steps": 0,
            "failed": 0,
            "skipped_lines": skipped,
            "message": "无带用例上下文（case_id）的记录：待人工测试产生数据后重跑",
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return EXIT_PENDING

    steps = _group_steps(selected)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / f"{run_id}-analysis.md"
    report_path.write_text(render_markdown(run_id, steps, skipped), encoding="utf-8")

    failed_count = sum(1 for step in steps if step["failed"])
    summary = {
        "schema_version": SCHEMA_VERSION,
        "tool": TOOL,
        "status": "FAIL" if failed_count else "PASS",
        "run_id": run_id,
        "steps": len(steps),
        "failed": failed_count,
        "skipped_lines": skipped,
        "report": report_path.as_posix(),
        "layers": sorted({step["layer"] for step in steps}),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return EXIT_FAIL if failed_count else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
