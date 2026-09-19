#!/usr/bin/env python
"""R-384 / BL-147-04 采集文件命名白名单校验（命名实测工具）.

**用途**：验证编排器（``scripts/service-orchestrator.ps1``）产出的四仓采集文件名是否被
日志中心 :class:`~openbase.modules.logs.repository.RepoLogAdapter` **看得见**——即命名对齐
的唯一判据是适配器白名单正则，而非人工观感。

判据**唯一来源**：``openbase/modules/logs/repository.py::_REPO_NAME_RE``（在此直接导入该
常量，禁止本脚本自行复刻正则，避免口径漂移）。

命名契约（BL-147-04 目标口径）::

    结构化流（JSON Lines）
      {svc}-YYYYMMDD.jsonl        ← 结构化流为 stdout 的仓（openrag）
      {svc}-YYYYMMDD.err.jsonl    ← 结构化流为 stderr 的仓（dps / openllm / openmemory）
    非结构化流（纯文本）
      {svc}-YYYYMMDD.log / {svc}-YYYYMMDD.err.log
    归档（同日重复启动时把上一轮非空内容移走，保留原后缀）
      {svc}-YYYYMMDD-HHmmss.jsonl / .err.jsonl / .log / .err.log
      ↑ 时间戳必须位于 ``.err`` **之前**：``{svc}-YYYYMMDD.err-HHmmss.log`` 不匹配白名单，
        会被适配器按目录扫描漏读（BL-147-04 修复点）

用法::

    # ① 实测扫描（对真实 logs/ 目录逐文件判定「可见 / 不可见」）
    python scripts/verify_repo_log_naming.py --logs-root logs

    # ② 校验编排器将产出的命名（由 -Action namecheck 生成后传入）
    python scripts/verify_repo_log_naming.py --file dps/dps-20260919.err.jsonl \\
        --file dps/dps-20260919-155700.err.jsonl

退出码：``0`` = 全部可见（无非 repo_log 源失败项）；``1`` = 存在不可见文件；``2`` = 未给出任何
输入（用法错误）。

边界：
- 非 repo_log 源目录（``openbase`` / ``frontend`` / ``oidc-idp`` / ``service-orchestrator``）
  记 ``skipped``，**不参与**判定（其文件名不受适配器白名单约束）；
- 修复前旧归档命名（``{svc}-YYYYMMDD.err-HHmmss.{log,jsonl}``）默认记 ``failed``（新命名不得
  再产生该形态）；对**既有历史文件**可用 ``--tolerate-legacy-err-archive`` 改记 ``legacy``
  （仅用于扫描在盘历史文件，不得用于校验编排器将产出的命名）；
- 四仓目录缺失如实登记于 ``missing_dirs``，不静默当作通过。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from openbase.modules.logs.derivation import REPO_LOG_SOURCES  # noqa: E402
from openbase.modules.logs.repository import REPO_LOG_NAME_RE  # noqa: E402

STATUS_OK = "ok"
STATUS_SKIPPED = "skipped"
STATUS_FAILED = "failed"
STATUS_LEGACY = "legacy"

#: 修复前旧归档命名：``{svc}-YYYYMMDD.err-HHmmss.{log,jsonl}``（时间戳在 ``.err`` 之后）
_LEGACY_ERR_ARCHIVE_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*-\d{8}\.err-\d{6}\.(?:jsonl|log)$")


def _classify(entry: str, *, tolerate_legacy: bool = False) -> dict[str, str]:
    """判定单个 ``<svc>/<basename>`` 条目是否可被适配器检索到.

    Args:
        entry: 相对路径条目，形如 ``dps/dps-20260919.err.jsonl``。
        tolerate_legacy: 为真时，把修复前旧归档命名记为 ``legacy`` 而非 ``failed``
            （仅用于扫描在盘历史文件）。

    Returns:
        ``{"entry": ..., "status": ok|skipped|failed|legacy, "reason": ...}``。
    """
    normalized = entry.replace("\\", "/").strip("/")
    parts = normalized.split("/")
    if len(parts) != 2:
        return {
            "entry": entry,
            "status": STATUS_FAILED,
            "reason": "条目须形如 <svc>/<basename>",
        }
    svc, basename = parts
    if svc not in REPO_LOG_SOURCES:
        return {
            "entry": entry,
            "status": STATUS_SKIPPED,
            "reason": f"{svc} 非 repo_log 源目录（文件名不受白名单约束）",
        }
    match = REPO_LOG_NAME_RE.match(basename)
    if match is None:
        if tolerate_legacy and _LEGACY_ERR_ARCHIVE_RE.match(basename):
            return {
                "entry": entry,
                "status": STATUS_LEGACY,
                "reason": "修复前旧归档命名（历史文件；新命名不再产生）",
            }
        return {
            "entry": entry,
            "status": STATUS_FAILED,
            "reason": "不匹配适配器白名单 REPO_LOG_NAME_RE（该文件不会被检索到）",
        }
    if match.group("svc") != svc:
        return {
            "entry": entry,
            "status": STATUS_FAILED,
            "reason": f"文件名 svc 段 {match.group('svc')} 与目录 {svc} 不一致",
        }
    try:
        datetime.strptime(match.group("date"), "%Y%m%d")
    except ValueError:
        return {
            "entry": entry,
            "status": STATUS_FAILED,
            "reason": f"日期段 {match.group('date')} 非合法日期",
        }
    return {"entry": entry, "status": STATUS_OK, "reason": "适配器可见"}


def _summarize(results: list[dict[str, str]], **extra: Any) -> dict[str, Any]:
    report: dict[str, Any] = {
        "results": results,
        "ok": sum(1 for row in results if row["status"] == STATUS_OK),
        "skipped": sum(1 for row in results if row["status"] == STATUS_SKIPPED),
        "failed": sum(1 for row in results if row["status"] == STATUS_FAILED),
        "legacy": sum(1 for row in results if row["status"] == STATUS_LEGACY),
    }
    report.update(extra)
    return report


def verify_entries(entries: Sequence[str]) -> dict[str, Any]:
    """校验一批 ``<svc>/<basename>`` 命名条目（纯函数，供测试与编排器调用）."""
    return _summarize([_classify(entry) for entry in entries])


def scan_logs_root(logs_root: str | Path, *, tolerate_legacy: bool = False) -> dict[str, Any]:
    """实测扫描日志根目录下**全部**子目录文件，逐条判定可见性.

    Args:
        logs_root: 日志根目录（如 ``logs``）。
        tolerate_legacy: 为真时把修复前旧归档命名记为 ``legacy``（扫描在盘历史文件用）。

    Returns:
        报告 dict（含 ``results`` / ``ok`` / ``skipped`` / ``failed`` / ``legacy`` / ``missing_dirs``）。
    """
    root = Path(logs_root)
    results: list[dict[str, str]] = []
    if root.is_dir():
        for svc_dir in sorted(path for path in root.iterdir() if path.is_dir()):
            for candidate in sorted(path for path in svc_dir.iterdir() if path.is_file()):
                results.append(
                    _classify(f"{svc_dir.name}/{candidate.name}", tolerate_legacy=tolerate_legacy)
                )
    missing = [svc for svc in REPO_LOG_SOURCES if not (root / svc).is_dir()]
    return _summarize(results, logs_root=root.as_posix(), missing_dirs=missing)


def _print_report(report: dict[str, Any], *, title: str) -> None:
    print(f"[verify_repo_log_naming] {title}")
    for row in report["results"]:
        marker = {
            STATUS_OK: "OK  ",
            STATUS_SKIPPED: "SKIP",
            STATUS_FAILED: "FAIL",
            STATUS_LEGACY: "LEGC",
        }[row["status"]]
        print(f"  [{marker}] {row['entry']}  {row['reason']}")
    if report.get("missing_dirs"):
        print(f"  [INFO] 四仓目录缺失：{', '.join(report['missing_dirs'])}")
    print(
        "  汇总：可见 {ok} / 跳过 {skipped} / 不可见 {failed} / 历史旧命名 {legacy}".format(
            ok=report["ok"],
            skipped=report["skipped"],
            failed=report["failed"],
            legacy=report["legacy"],
        )
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="校验四仓采集文件命名是否被引导器白名单接受")
    parser.add_argument("--file", action="append", default=[], help="命名条目 <svc>/<basename>（可重复）")
    parser.add_argument("--logs-root", default=None, help="实测扫描的日志根目录（如 logs）")
    parser.add_argument(
        "--tolerate-legacy-err-archive",
        action="store_true",
        help="扫描在盘历史文件时，把修复前旧归档命名记为 legacy（默认记 failed）",
    )
    parser.add_argument("--json", action="store_true", help="同时输出报告 JSON（供证据归档）")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 入口.

    Returns:
        统一退出码：``0`` = 全部可见；``1`` = 存在不可见；``2`` = 未给出输入。
    """
    args = _build_parser().parse_args(argv)
    reports: list[dict[str, Any]] = []

    if args.file:
        report = verify_entries(args.file)
        _print_report(report, title=f"编排器命名校验（{len(args.file)} 条）")
        reports.append(report)
    if args.logs_root:
        report = scan_logs_root(
            args.logs_root, tolerate_legacy=args.tolerate_legacy_err_archive
        )
        _print_report(report, title=f"实测扫描（logs-root={args.logs_root}）")
        reports.append(report)

    if not reports:
        _build_parser().print_help()
        return 2

    if args.json:
        print(json.dumps(reports, ensure_ascii=False, indent=2))

    return 1 if any(report["failed"] for report in reports) else 0


if __name__ == "__main__":
    sys.exit(main())
