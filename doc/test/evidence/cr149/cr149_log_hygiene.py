"""CR-149 面日志合规审计（AGENTS.md §3）：禁止记录凭据与正文

**规则（AGENTS.md §3 / 规范「日志规范」）**：禁止记录 密码 / 令牌 / 密钥 /
**完整请求体** / 个人隐私。CR-149 各批新增了大量观测日志（回写三路、通道护栏、
预算裁剪、画像维度、路由缓存、精炼触发），**观测不得以正文或凭据为代价** ——
本工具逐条检出「参数列表里出现正文/凭据类字段名」的日志调用，供人工判定。

用法（cwd = OpenLLM/backend）：

    python <此脚本> [--json]
"""
from __future__ import annotations

import json
import os
import re
import sys

CR149_FILES = (
    "app/edgerouter/orchestration/assembler.py",
    "app/edgerouter/orchestration/prompt_pipeline.py",
    "app/edgerouter/orchestration/refine.py",
    "app/edgerouter/orchestration/context_metrics.py",
    "app/edgerouter/orchestration/component_router.py",
    "app/edgerouter/orchestration/component_graph.py",
    "app/edgerouter/orchestration/component_pipeline.py",
    "app/edgerouter/orchestration/evaluate.py",
    "app/edgerouter/orchestration/executor.py",
    "app/edgerouter/orchestration/auto.py",
    "app/edgerouter/orchestration/deferred_fetch.py",
    "app/api/writeback.py",
    "app/services/writeback_queue.py",
    "app/services/profile_drift.py",
    "app/identity/channel.py",
)

#: 正文/凭据类字段名（出现即须人工确认**不得**为整值）
RISKY = (
    "response", "query", "dialogue", "content", "payload", "body", "message",
    "updates", "prompt", "secret", "password", "api_key", "apikey",
    "authorization", "token", "credential",
)
#: 允许的**非敏感**衍生量（长度、计数、标识、等级、原因）
SAFE_DERIVED = ("len(", "count", "_id", "id=", "reason", "grade", "level", "mode", "status")


def _calls(text: str) -> list[tuple[int, str]]:
    """提取 `logger.<level>(...)` 调用（括号配对扫描，支持多行）"""
    found: list[tuple[int, str]] = []
    for match in re.finditer(r"logger\.(debug|info|warning|error|exception)\(", text):
        start = match.end() - 1
        depth = 0
        index = start
        while index < len(text):
            char = text[index]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    break
            index += 1
        line_no = text.count("\n", 0, match.start()) + 1
        found.append((line_no, text[start: index + 1]))
    return found


def main() -> int:
    flagged: list[dict[str, object]] = []
    total = 0
    for path in CR149_FILES:
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        for line_no, call in _calls(text):
            total += 1
            lowered = call.lower()
            hits = [name for name in RISKY if name in lowered]
            if not hits:
                continue
            derived = [marker for marker in SAFE_DERIVED if marker in lowered]
            flagged.append(
                {
                    "file": path,
                    "line": line_no,
                    "risky_fields": hits,
                    "safe_markers": derived,
                    "call": " ".join(call.split())[:300],
                }
            )

    print(f"扫描 CR-149 面文件 {len(CR149_FILES)} 个；logger 调用 {total} 处")
    print(f"**参数列表含正文/凭据类字段名（须人工确认非整值落日志）: {len(flagged)}**")
    for item in flagged:
        print(f"  [{item['file']}:{item['line']}] fields={item['risky_fields']} safe={item['safe_markers']}")
        print(f"      {item['call']}")

    report = {
        "probe": "cr149_log_hygiene",
        "scanned_files": len(CR149_FILES),
        "logger_calls": total,
        "flagged": flagged,
        "rule": "AGENTS.md §3：禁止记录 密码/令牌/密钥/完整请求体/个人隐私",
        "method_note": "只做「字段名出现」检出；判定须人工确认是否为整值（长度/计数/标识为安全衍生量）",
    }
    if "--json" in sys.argv:
        out = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "cr149_log_hygiene-result.json"
        )
        with open(out, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
        print(f"报告已写入: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
