"""方案正文「声称 vs 仓内实现」机械审计（文档-实现漂移检测）

**动因（历史真实教训）**：本仓曾出现「方案正文声称某配置键已存在，实际全树无此键」
（`OPENLLM_PROFILE_LLM_REFINE`）与「某模块源码未随提交落库却被正文当作已交付」
（`profile_refine`）—— 即**文档-实现漂移**。本脚本把「正文引用 vs 仓内实现」的核对
**机械化**，使该缺陷类可在每轮复核中一键复跑。

**三类引用的区分（决定误报边界，如实登记）**：

1. **引用为存在**（已实施依据、判据字段名、护栏文件名）⇒ 仓内**必须**查到；
2. **引用为缺失**（审计取证「全仓检索零命中」、历史幻影符号、已知待登记项）⇒ 仓内
   **本就不该**查到 ⇒ 依**正文上下文**命中缺席标记即**跳过**；
3. **族前缀/通配**（如 `CONTEXT_*`、`RAG_RERANK*`）⇒ 不是符号，跳过。

**首版误报与修正（如实登记）**：首版未区分 2/3，也不扫 `tests/`，把「正确地说某物
不存在」与「族前缀」「护栏文件名」共 **68** 项误报为缺失；本版依次修正为：
上下文缺席标记跳过 ＋ 通配前缀跳过 ＋ 扫描源纳入 `tests/`（护栏文件名是**交付物**，
必须可核对）＋ 违规码（f-string 内的 `unlocatable:` 一类）改按**子串**判定。

用法（cwd = OpenLLM/backend）：

    python <此脚本> <方案 md 路径> [额外扫描根（如 OpenBase 证据目录）]
"""
from __future__ import annotations

import json
import os
import re
import sys

UPPER_RE = re.compile(r"^[A-Z][A-Z0-9_]{3,}$")
SNAKE_RE = re.compile(r"^_?[a-z][a-z0-9_]{2,}$")
CLASS_RE = re.compile(r"^[A-Z][A-Za-z0-9]{2,}$")
HASH_RE = re.compile(r"^[0-9a-f]{7,40}$")
WILDCARD_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\*$")

STATUS_WORDS = {"PASS", "FAIL", "SKIP", "BLOCKED", "TRUE", "FALSE", "NONE", "DRAFT", "REVIEW"}
#: 正文**邻近上下文**出现以下标记 ⇒ 该引用是「引用为缺失」，不做存在性要求
#: **须保持精简**：过于宽泛的标记（如「返回空」「解析为」）会吞掉整行、使审计失去意义
ABSENCE_MARKERS = (
    "零命中", "不存在", "无此键", "未实施", "未接线", "未做", "待登记", "待裁定",
    "幻影", "误填", "订正为", "未随提交", "本就不该",
)
#: 外部产品/环境变量/语言关键字等（非本仓符号）
EXTERNAL = {
    "OLLAMA_KEEP_ALIVE", "OLLAMA_MODELS", "OLLAMA_HOST", "json_extract", "Sequence",
    "TestClient", "await", "env", "requires", "ruff", "seed", "size_vram", "noise",
    "http", "https", "api", "json", "yaml", "sqlite", "faiss", "pytest", "asyncio",
}
#: 正文**已明确声明为零命中**的检索词（审计取证用，逐项可回溯到具体修订行）＋
#: 工件文件名片段（如「`cr149-t18` / `t19` / `t20`」中的后两项）
EVIDENCE_ABSENT = {
    "strip_metadata": "v1.13.0 行：检索取证词（正文已声明零命中）",
    "METADATA_NOISE": "v1.13.0 行：检索取证词（正文已声明零命中）",
    "_load_rules": "v1.16.0 行：检索取证词（正文已声明零命中）",
    "t19": "工件文件名片段（cr149-t*-full.txt 列表）",
    "t20": "工件文件名片段（cr149-t*-full.txt 列表）",
}


def _tokens_with_context(doc_text: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for match in re.finditer(r"`([^`\n]{1,60})`", doc_text):
        raw = match.group(1).strip()
        if WILDCARD_RE.match(raw) or raw.endswith("_") or " " in raw or not raw:
            continue
        token = raw.strip(":（()）[],.;*")
        if not token or token in STATUS_WORDS or HASH_RE.match(token) or token in EXTERNAL:
            continue
        if token in EVIDENCE_ABSENT:
            continue
        if not (UPPER_RE.match(token) or SNAKE_RE.match(token) or CLASS_RE.match(token)):
            continue
        start = max(0, match.start() - 80)
        end = min(len(doc_text), match.end() + 80)
        result.setdefault(token, []).append(doc_text[start:end])
    return result


def _sources(extra_root: str | None) -> dict[str, str]:
    sources: dict[str, str] = {}
    roots = ["app", "tests", "main.py", "mock_services"]
    if extra_root and os.path.isdir(extra_root):
        roots.append(extra_root)
    for root in roots:
        if os.path.isfile(root):
            with open(root, encoding="utf-8") as handle:
                sources[root] = handle.read()
            continue
        if not os.path.isdir(root):
            continue
        for walk_root, dirs, names in os.walk(root):
            dirs[:] = [name for name in dirs if name not in {"__pycache__", "node_modules"}]
            for name in names:
                if not name.endswith(".py"):
                    continue
                path = os.path.join(walk_root, name).replace("\\", "/")
                with open(path, encoding="utf-8") as handle:
                    sources[path] = handle.read()
    return sources


def _exists(identifier: str, sources: dict[str, str]) -> list[str]:
    """存在性判定：**文件名** 或 定义/声明形式，或**子串**形式（覆盖 f-string 内违规码）"""
    path_hits = [path for path in sources if identifier in os.path.basename(path)]
    if UPPER_RE.match(identifier):
        patterns = (f"{identifier}:", f"{identifier} =", f"{identifier}*", f'"{identifier}"')
    elif SNAKE_RE.match(identifier):
        patterns = (
            f"def {identifier}(",
            f"class {identifier}",
            f"{identifier} =",
            f"{identifier}:",
            f'"{identifier}',
            f"'{identifier}",
            f"{identifier}.py",
            f"{identifier}::",
        )
    else:
        patterns = (f"class {identifier}", f"{identifier}:", f"{identifier} =", f"{identifier}.")
    content_hits = [path for path, text in sources.items() if any(p in text for p in patterns)]
    return path_hits + content_hits


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python check_doc_claims.py <方案 md 路径> [额外扫描根]")
        return 2
    with open(sys.argv[1], encoding="utf-8") as handle:
        doc_text = handle.read()
    extra_root = sys.argv[2] if len(sys.argv) > 2 else None
    sources = _sources(extra_root)

    checked = skipped = 0
    missing: list[str] = []
    for token, contexts in sorted(_tokens_with_context(doc_text).items()):
        if any(any(marker in context for marker in ABSENCE_MARKERS) for context in contexts):
            skipped += 1
            continue
        checked += 1
        if not _exists(token, sources):
            missing.append(token)

    print(f"扫描源: {len(sources)} 个 .py（含 {'OpenBase 证据目录' if extra_root else '仅 OpenLLM'}）")
    print(f"「引用为缺失 / 族前缀」已跳过: {skipped}")
    print(f"「引用为存在」待核对: {checked}")
    print(f"**仓内查无此项（需判定「文档错」还是「实现缺」）: {len(missing)}**")
    for token in missing:
        print(f"  [MISSING] {token}")

    report = {
        "probe": "check_doc_claims",
        "design_doc": os.path.basename(sys.argv[1]),
        "scanned_py_files": len(sources),
        "skipped_as_absent_or_prefix": skipped,
        "checked_as_claimed_present": checked,
        "missing": missing,
        "method_note": (
            "区分「引用为存在」（须查到）与「引用为缺失/族前缀」（跳过）；"
            "首版未区分且不扫 tests/，曾误报 68 项；删除整行级跳过以免审计被宽泛标记吞掉"
        ),
    }
    if "--json" in sys.argv:
        out = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "check_doc_claims-result.json"
        )
        with open(out, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
        print(f"报告已写入: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
