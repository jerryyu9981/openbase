#!/usr/bin/env python
"""人工端到端测试日志聚合（C-7）——按 run_id/case_id 汇总 ``logs/**/*.jsonl``.

设计依据：《OpenBase-人工端到端测试日志记录方案-v1.0.0》v1.1.2
- §3.1 三层记录通道 L3（证据级聚合报告：按 run 汇总 JSON + Markdown）；
- §3.2 数据流（``scripts/test_log_aggregate.py`` → ``doc/test/evidence/manual/<run_id>.json｜.md``）；
- §5 批 1 C-7；§6 验收（可检索性：≥95% 用例可按 ``case_id`` 检索；双证据关联：每条记录带 ``request_id``）。

输入面：C-1 落盘的 JSON Lines（``logs/<service>/<service>-YYYYMMDD.jsonl``），
其中 L1 请求级记录的用例上下文字段由 C-3 写入（``case_id``/``step_id``/``run_id``/``channel``）。

执行面（禁伪造）：
- 只聚合**真实存在**的日志行；解析失败的行计入 ``skipped_lines`` 并跳过，不臆造记录；
- 无任何记录（尚未人工测试）→ ``status=PENDING``、退出码 ``2``，且**不产出**空报告文件；
- ``.log``（C-6 采集的纯文本服务日志）不参与聚合，仅 JSONL 参与。

用法::

    python scripts/test_log_aggregate.py                      # 聚合全部轮次
    python scripts/test_log_aggregate.py --run-id run-20260914-0100
    python scripts/test_log_aggregate.py --logs-root logs --out-dir doc/test/evidence/manual
    python scripts/test_log_aggregate.py --run-id run-1 --json

统一退出码：``0`` = PASS；``1`` = FAIL（存在失败步骤）；``2`` = PENDING（无记录 / 目录不可达）。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOGS_ROOT = ROOT / "logs"
DEFAULT_OUT_DIR = ROOT / "doc" / "test" / "evidence" / "manual"
SCHEMA_VERSION = 1
TOOL = "test_log_aggregate.py"
ALL_RUNS = "<all>"

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_PENDING = 2

# 记录识别：C-1 formatter 必填字段 + C-3 用例上下文字段
_TS_KEY = "ts"
_MESSAGE_KEY = "message"
_STATUS_KEY = "status_code"


@lru_cache(maxsize=1)
def _git_head() -> str:
    """读取 OpenBase HEAD（真实；失败返回空串，不伪造）."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def _iter_jsonl_files(logs_root: Path) -> list[Path]:
    """列出待聚合的 JSONL 文件（不存在目录 → 空列表）."""
    if not logs_root.exists():
        return []
    return sorted(path for path in logs_root.rglob("*.jsonl") if path.is_file())


def _parse_records(logs_root: Path) -> tuple[list[dict[str, Any]], int]:
    """解析全部 JSONL 文件.

    Returns:
        ``(records, skipped_lines)``；仅接收形如结构化日志的对象（含 ``ts`` 与
        ``message``），其余行计入 skipped。
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
    """失败判定：HTTP 状态码 ≥ 400 或显式 error 字段."""
    status = record.get(_STATUS_KEY)
    if isinstance(status, int) and status >= 400:
        return True
    return bool(record.get("error"))


def _step_of(record: dict[str, Any]) -> dict[str, Any]:
    """渲染单个步骤（双证据列：状态码 + request_id + 耗时）."""
    return {
        "step_id": record.get("step_id"),
        "request_id": record.get("request_id"),
        "method": record.get("method"),
        "path": record.get("path"),
        "status_code": record.get(_STATUS_KEY),
        "duration_ms": record.get("duration_ms"),
        "message": record.get("message"),
    }


def aggregate(logs_root: str | Path, run_id: str | None = None) -> dict[str, Any]:
    """聚合 ``logs_root/**/*.jsonl``（按 run_id → case_id 分组）.

    Args:
        logs_root: 日志根目录（如 ``logs``）。
        run_id: 仅聚合该测试轮次；None 表示聚合全部轮次。

    Returns:
        报告 dict（含 status/totals/cases/sources/skipped_lines）。
    """
    root = Path(logs_root)
    records, skipped = _parse_records(root)

    selected = [
        record for record in records if run_id is None or record.get("run_id") == run_id
    ]
    # 证据来源 = 真正贡献了本次聚合记录的文件（按 run 过滤后），保证可回溯
    sources = sorted({f"logs/{record['_source']}" for record in selected})

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for record in selected:
        case_id = record.get("case_id")
        if not case_id:
            # 无用例上下文（未启用测试模式）→ 归入未标注桶，仍参与总数统计
            case_id = "<unlabeled>"
        grouped.setdefault((str(record.get("run_id") or "-"), str(case_id)), []).append(record)

    cases: list[dict[str, Any]] = []
    failed_steps = 0
    for (case_run, case_id), case_records in sorted(grouped.items()):
        steps = sorted(
            (_step_of(record) for record in case_records),
            key=lambda step: (str(step["step_id"]), str(step["request_id"])),
        )
        case_failed = sum(1 for record in case_records if _is_failed(record))
        failed_steps += case_failed
        cases.append(
            {
                "case_id": case_id,
                "run_id": case_run,
                "status": "FAIL" if case_failed else "PASS",
                "records": len(case_records),
                "failed_steps": case_failed,
                "steps": steps,
            }
        )

    if not selected:
        status = "PENDING"
    elif failed_steps:
        status = "FAIL"
    else:
        status = "PASS"

    return {
        "schema_version": SCHEMA_VERSION,
        "tool": TOOL,
        "openbase_commit": _git_head(),
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "logs_root": root.as_posix(),
        "run_id": run_id or ALL_RUNS,
        "status": status,
        "totals": {
            "records": len(selected),
            "cases": len(cases),
            "failed_steps": failed_steps,
        },
        "cases": cases,
        "sources": sources,
        "skipped_lines": skipped,
    }


def render_markdown(report: dict[str, Any]) -> str:
    """渲染 Markdown 报告（与既有 evidence 风格一致，含双证据列）."""
    totals = report["totals"]
    lines = [
        f"# 人工端到端测试日志聚合报告（run_id={report['run_id']}）",
        "",
        "## 元信息",
        "",
        "| 项 | 值 |",
        "|----|-----|",
        f"| 结论 | **{report['status']}** |",
        f"| 生成时间 | {report['checked_at']} |",
        f"| 工具 | `{report['tool']}`（schema_version={report['schema_version']}） |",
        f"| OpenBase 提交 | `{report['openbase_commit'] or '(未获取)'}` |",
        f"| 日志根目录 | `{report['logs_root']}` |",
        f"| 记录数 / 用例数 / 失败步骤数 | {totals['records']} / {totals['cases']} / {totals['failed_steps']} |",
        f"| 跳过行数（非结构化/解析失败） | {report['skipped_lines']} |",
        "",
        "## 数据来源（JSONL）",
        "",
    ]
    if report["sources"]:
        lines.extend(f"- `{source}`" for source in report["sources"])
    else:
        lines.append("- （无）")

    lines.extend(
        [
            "",
            "## 用例明细",
            "",
            f"共 {len(report['cases'])} 个用例；下表每行 = 一个请求级步骤（双证据：状态码 + request_id）。",
            "",
            "| case_id | step_id | status_code | method | path | request_id | duration_ms |",
            "|---------|---------|-------------|--------|------|------------|-------------|",
        ]
    )
    for case in report["cases"]:
        for step in case["steps"]:
            lines.append(
                "| {case} | {step} | {status} | {method} | {path} | {request} | {took} |".format(
                    case=case["case_id"],
                    step=step["step_id"],
                    status=step["status_code"],
                    method=step["method"],
                    path=step["path"],
                    request=step["request_id"],
                    took=step["duration_ms"],
                )
            )

    lines.extend(
        [
            "",
            "## 结论与边界",
            "",
            "- 本报告由日志聚合脚本自动生成，仅作**客观证据**；PASS/FAIL 结论由人工判定（方案 D-3：人工记录仅作补充证据，不参与门禁判定）。",
            "- FAIL 判定口径：步骤 HTTP 状态码 ≥ 400 或记录含 ``error`` 字段。",
            "- 未标注用例（``<unlabeled>``）＝ 未携带 ``X-Test-Case-Id`` 的请求，仅参与总数统计。",
            "",
        ]
    )
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="按 run_id/case_id 聚合 logs/**/*.jsonl → doc/test/evidence/manual/<run_id>.json｜.md"
    )
    parser.add_argument("--logs-root", default=str(DEFAULT_LOGS_ROOT), help="日志根目录（默认 logs/）")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="证据输出目录（默认 doc/test/evidence/manual/）")
    parser.add_argument("--run-id", default=None, help="仅聚合该测试轮次（默认全部）")
    parser.add_argument("--json", action="store_true", help="同时打印报告 JSON 到 stdout")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 入口.

    Returns:
        统一退出码：0=PASS / 1=FAIL / 2=PENDING（无记录）。
    """
    args = _build_parser().parse_args(argv)
    report = aggregate(args.logs_root, run_id=args.run_id)

    totals = report["totals"]
    print(
        f"[{TOOL}] run_id={report['run_id']} status={report['status']} "
        f"records={totals['records']} cases={totals['cases']} failed_steps={totals['failed_steps']} "
        f"skipped_lines={report['skipped_lines']}"
    )

    if report["status"] == "PENDING":
        print("  无日志记录（尚未执行人工测试）：不产出空报告，退出码 2（PENDING）")
        return EXIT_PENDING

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{report['run_id']}.json"
    md_path = out_dir / f"{report['run_id']}.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(f"  证据已落盘：{json_path}")
    print(f"  报告已落盘：{md_path}")

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))

    return EXIT_FAIL if report["status"] == "FAIL" else EXIT_PASS


if __name__ == "__main__":
    sys.exit(main())
