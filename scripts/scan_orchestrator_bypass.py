#!/usr/bin/env python
"""S7-T1-4 受管编排唯一入口静态扫描（禁批量杀绕过路径）.

设计依据：《OpenBase-S7-全域门禁与总收官-设计草案-v1.0.0》§2.2 / §4.1（Q-S7-D5）。

语义：服务生命周期编排唯一入口 = ``scripts/service-orchestrator.ps1``（stop 按记录的
PID 逆拓扑停止，**非批量杀**）。本脚本以静态扫描确认「无绕过编排入口的直接批量操作
路径」：

- 扫描仓内 ``scripts/**`` 的编排相关脚本（``.ps1``/``.psm1``/``.py``/``.sh``/``.bat``/
  ``.cmd``），检出 ``taskkill`` / ``Stop-Process`` / ``kill -9`` / ``killall`` / ``pkill``；
- 命中项区分「真实命令」与「字符串/注释中的文案提及」（防误报）：
  先剥离块注释、行注释与字符串字面量，再匹配；
- 唯一允许位：``service-orchestrator.ps1`` 中 ``Stop-Process -Id <pid>`` 形态的逆拓扑停止；
  其余任何批量杀路径（``-Name`` / ``taskkill /IM`` 等）均计为绕过。

用法：
    python scripts/scan_orchestrator_bypass.py [--json]
    exit 0 = 0 绕过命中（含允许位与自检通过）；非 0 = 存在绕过/允许位异常。

执行面：A（沙箱可判定，静态扫描）；真实编排实跑属 B 面（联调窗口），登记 PENDING。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

# 唯一允许的编排入口（服务生命周期）
ORCHESTRATOR_ENTRY = "scripts/service-orchestrator.ps1"
# 规则定义文件自身（含模式字面量）不参与扫描
SELF_PATH = "scripts/scan_orchestrator_bypass.py"

# 扫描范围（相对仓根）与代码文件后缀
SCAN_ROOTS = ("scripts",)
SCAN_SUFFIXES = (".ps1", ".psm1", ".py", ".sh", ".bat", ".cmd")

# 批量杀 / 进程终止路径标识（大小写不敏感）
BYPASS_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("taskkill", re.compile(r"\btaskkill\b", re.IGNORECASE)),
    ("stop-process", re.compile(r"\bstop-process\b", re.IGNORECASE)),
    ("kill -9", re.compile(r"\bkill\s+-9\b", re.IGNORECASE)),
    ("killall", re.compile(r"\bkillall\b", re.IGNORECASE)),
    ("pkill", re.compile(r"\bpkill\b", re.IGNORECASE)),
)

# 允许形态：按记录 PID 逆拓扑停止（Stop-Process -Id <...>）
_ALLOWED_PID_STOP = re.compile(r"Stop-Process\s+-Id\s+\S+", re.IGNORECASE)
# 批量杀征兆：按名/镜像名/通配（与唯一允许位互斥）
_BATCH_STOP_HINT = re.compile(r"-Name\b|/IM\b|Get-Process\s+\*", re.IGNORECASE)

_BLOCK_COMMENT = re.compile(r"<#.*?#>", re.DOTALL)
_SINGLE_QUOTED = re.compile(r"'[^']*'")
_DOUBLE_QUOTED = re.compile(r'"[^"]*"')
_LINE_COMMENT = re.compile(r"#.*$")


def strip_comments_and_strings(line: str) -> str:
    """剥离行内注释与字符串字面量，仅保留可执行代码片段（防文案误报）."""
    text = _BLOCK_COMMENT.sub(" ", line)
    text = _SINGLE_QUOTED.sub("''", text)
    text = _DOUBLE_QUOTED.sub('""', text)
    text = _LINE_COMMENT.sub("", text)
    return text


def _is_allowed_hit(relative_path: str, token: str, code_line: str) -> bool:
    """判定命中是否落在唯一允许位（编排入口的按 PID 逆拓扑停止）."""
    if relative_path != ORCHESTRATOR_ENTRY:
        return False
    if token != "stop-process":
        return False
    if _BATCH_STOP_HINT.search(code_line):
        return False
    return bool(_ALLOWED_PID_STOP.search(code_line))


def scan_text(text: str, relative_path: str = "") -> list[dict[str, Any]]:
    """扫描单段文本，返回命中列表（含真实命中与允许位命中）."""
    hits: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        code_line = strip_comments_and_strings(raw_line)
        if not code_line.strip():
            continue
        for token, pattern in BYPASS_PATTERNS:
            if pattern.search(code_line):
                hits.append(
                    {
                        "path": relative_path,
                        "line": line_number,
                        "token": token,
                        "snippet": raw_line.strip(),
                        "allowed": _is_allowed_hit(relative_path, token, code_line),
                    }
                )
    return hits


def _iter_scan_files() -> list[Path]:
    """枚举扫描范围内待检文件（排除规则定义文件自身）."""
    files: list[Path] = []
    self_absolute = (ROOT / SELF_PATH).resolve()
    for root_name in SCAN_ROOTS:
        root_path = ROOT / root_name
        if not root_path.exists():
            continue
        for path in sorted(root_path.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in SCAN_SUFFIXES:
                continue
            if path.resolve() == self_absolute:
                continue
            files.append(path)
    return files


def scan_repository() -> dict[str, Any]:
    """扫描仓内编排相关脚本，返回绕过命中/允许位/自检结论."""
    scanned_files = 0
    allowed: list[dict[str, Any]] = []
    disallowed: list[dict[str, Any]] = []
    for path in _iter_scan_files():
        scanned_files += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        relative_path = path.relative_to(ROOT).as_posix()
        for hit in scan_text(text, relative_path):
            (allowed if hit["allowed"] else disallowed).append(hit)
    return {
        "schema": "openbase-s7-orchestrator-bypass/v1.0.0",
        "orchestrator_entry": ORCHESTRATOR_ENTRY,
        "scanned_files": scanned_files,
        "allowed": allowed,
        "disallowed": disallowed,
        "self_check": self_check(),
    }


def self_check() -> dict[str, bool]:
    """非空化自检：防漏报（违规样本命中）与防误报（字符串文案忽略）."""
    bypass_hits = scan_text("taskkill /F /IM python.exe", "scripts/other.ps1")
    string_hits = scan_text(
        'Write-Host "Rollback: Stop-Process -Id $proc.Id -Force"',
        ORCHESTRATOR_ENTRY,
    )
    allowed_hits = scan_text(
        "Stop-Process -Id $target -Force -ErrorAction SilentlyContinue",
        ORCHESTRATOR_ENTRY,
    )
    return {
        "bypass_detected": bool(bypass_hits) and all(not hit["allowed"] for hit in bypass_hits),
        "string_mention_ignored": not string_hits,
        "allowed_pid_stop_accepted": len(allowed_hits) == 1 and allowed_hits[0]["allowed"],
    }


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    report = scan_repository()
    if "--json" in argv:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("=== S7-T1-4 编排唯一入口旁路扫描 ===")
        print(f"  orchestrator entry : {report['orchestrator_entry']}")
        print(f"  scanned files      : {report['scanned_files']}")
        print(f"  allowed hits       : {len(report['allowed'])}")
        print(f"  disallowed hits    : {len(report['disallowed'])}")
        for hit in report["disallowed"]:
            print(f"    [BYPASS] {hit['path']}:{hit['line']} token={hit['token']}")
        self_check_failed = [key for key, ok in report["self_check"].items() if not ok]
        print(f"  self-check          : {'OK' if not self_check_failed else self_check_failed}")
    failed = bool(report["disallowed"]) or not all(report["self_check"].values())
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
