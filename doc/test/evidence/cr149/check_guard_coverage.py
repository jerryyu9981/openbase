"""方案「已实施」条目的**护栏覆盖审计**：有无按名引用它的测试？

**动因（第四类保真度问题）」**：前几轮已整治三类 ——「判据随壁钟翻转」「判据挂名错位」
「判据只覆盖原文子集而未声明」。第四类是本工具要回答的：**方案声称某模块/函数已实施，
但有没有护栏引用它？** 若无，则该行为可**静默回归**（本仓历史上 `profile_refine`
「源码未落库却被当作已交付」正是「无护栏 + 无实现」叠加的后果）。

**口径（如实登记）**：
  * 只审 **代码符号**（`def x` / `class X` 的形式），**不审配置键** —— 配置键多由
    `load_budget_policy` 一类**行为级**护栏覆盖，逐键按名引用并非必要；
  * 判定＝在 `tests/`（含用例名、注释）中出现 `符号名` 即可；
  * 结论分两类：**有按名引用**（含行为级覆盖的常见情形）与 **无按名引用**（须逐项
    人工判定是「仅行为级覆盖」还是「真无护栏」）—— 本工具只出清单，**不代替判定**。

用法（cwd = OpenLLM/backend）：

    python <此脚本> <方案 md 路径> [额外测试根（如 OpenBase 证据目录）]
"""
from __future__ import annotations

import json
import os
import re
import sys

SNAKE_RE = re.compile(r"^_?[a-z][a-z0-9_]{2,}$")
CLASS_RE = re.compile(r"^[A-Z][A-Za-z0-9]{2,}$")
SKIP_TOKENS = {
    "await", "env", "seed", "noise", "requires", "ruff", "json", "yaml",
    "test", "tests", "docs", "app", "main", "config", "settings",
}


def _code_symbols(doc_text: str) -> set[str]:
    """正文中**看起来是代码符号**的反引号标识符（排除配置键与族前缀）"""
    symbols: set[str] = set()
    for match in re.finditer(r"`([^`\n]{1,60})`", doc_text):
        raw = match.group(1).strip()
        if raw.endswith("*") or raw.endswith("_") or " " in raw or not raw:
            continue
        token = raw.strip(":（()）[],.;*")
        if not token or token in SKIP_TOKENS:
            continue
        # 全大写下划线＝配置键/常量 ⇒ 本轮不审（口径见模块 docstring）
        if re.match(r"^[A-Z][A-Z0-9_]{3,}$", token):
            continue
        if SNAKE_RE.match(token) or CLASS_RE.match(token):
            symbols.add(token)
    return symbols


def _defined_symbols() -> set[str]:
    """在 `app/` 中真实定义（`def` / `class`）的符号名"""
    defined: set[str] = set()
    for root, dirs, names in os.walk("app"):
        dirs[:] = [name for name in dirs if name != "__pycache__"]
        for name in names:
            if not name.endswith(".py"):
                continue
            with open(os.path.join(root, name), encoding="utf-8") as handle:
                text = handle.read()
            defined.update(re.findall(r"^\s*(?:async )?def ([A-Za-z_][A-Za-z0-9_]*)", text, re.M))
            defined.update(re.findall(r"^\s*class ([A-Za-z_][A-Za-z0-9_]*)", text, re.M))
    return defined


def _test_sources(extra_root: str | None) -> dict[str, str]:
    sources: dict[str, str] = {}
    roots = ["tests"]
    if extra_root and os.path.isdir(extra_root):
        roots.append(extra_root)
    for root in roots:
        for walk_root, dirs, names in os.walk(root):
            dirs[:] = [name for name in dirs if name not in {"__pycache__", "node_modules"}]
            for name in names:
                if not name.endswith((".py", ".json", ".md")):
                    continue
                path = os.path.join(walk_root, name).replace("\\", "/")
                try:
                    with open(path, encoding="utf-8") as handle:
                        sources[path] = handle.read()
                except UnicodeDecodeError:  # pragma: no cover - 二进制/异常编码
                    continue
    return sources


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python check_guard_coverage.py <方案 md 路径> [额外测试根]")
        return 2
    with open(sys.argv[1], encoding="utf-8") as handle:
        doc_text = handle.read()
    extra_root = sys.argv[2] if len(sys.argv) > 2 else None
    defined = _defined_symbols()
    tests = _test_sources(extra_root)

    claimed = sorted(_code_symbols(doc_text) & defined)
    guarded: list[str] = []
    unguarded: list[str] = []
    for symbol in claimed:
        hits = [path for path, text in tests.items() if symbol in text]
        (guarded if hits else unguarded).append(symbol)

    print(f"正文声称已实施且仓内确有定义（代码符号）: {len(claimed)}")
    print(f"  有按名引用（护栏/证据）: {len(guarded)}")
    print(f"  **无按名引用（须人工判定：仅行为级覆盖 or 真无护栏）: {len(unguarded)}**")
    for symbol in unguarded:
        print(f"    [NO-NAME-REF] {symbol}")

    report = {
        "probe": "check_guard_coverage",
        "design_doc": os.path.basename(sys.argv[1]),
        "claimed_and_defined": len(claimed),
        "has_name_reference": len(guarded),
        "no_name_reference": unguarded,
        "method_note": (
            "只审代码符号（def/class），不审配置键；判定＝在 tests/ 与证据目录中出现符号名；"
            "无按名引用不等于无护栏（可能仅行为级覆盖）⇒ 清单供人工判定，工具不代判"
        ),
    }
    if "--json" in sys.argv:
        out = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "check_guard_coverage-result.json"
        )
        with open(out, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
        print(f"报告已写入: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
