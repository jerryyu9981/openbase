"""方案正文「声称 vs 仓内实现」机械审计（文档-实现漂移检测）

**动因（历史真实教训）**：本仓曾出现「方案正文声称某配置键已存在，实际全树无此键」
（`OPENLLM_PROFILE_LLM_REFINE`）与「某模块源码未随提交落库却被正文当作已交付」
（`profile_refine`）—— 即**文档-实现漂移**。本脚本把「正文引用 vs 仓内实现」的核对
**机械化**，使该缺陷类可在每轮复核中一键复跑。

**三项检查（收口方案 A4 / 技术方案 §10 项 16·17）**：

  * **检查一 · 符号存在性**（原功能）：正文反引号引用的符号须在仓内可查（见下文三类区分）；
  * **检查二 · 配置键存在性**（本轮新增）：正文反引号引用的**配置键候选**须声明于
    `Settings`（`app/core/config.py`）。分两桶如实登记：
      - `missing_keys`（**硬缺口**）：既不在 `Settings`、也不在源码任何位置 ⇒ 幻影键；
      - `source_only_keys`（**提示**）：不在 `Settings` 但在源码中（模块级常量等）⇒ 非配置键。
    **已知局限（如实登记）**：源码中若存在**负向断言**（如护栏测试断言「某符号不得复活」），
    该符号也会落入本桶 —— 本工具**不区分「被使用」与「被断言为不存在」**，故本桶须人工过目。
    **与检查一不同，本检查不套用「缺席标记」跳过** —— 因「正文登记某键为幻影」正是要
    **稳定复现的告警**；改为对每个候选项标注 `known_absent`（正文是否已自述其不存在），
    使「已自述的历史个案」与「新增未察觉的漂移」可区分。
    **候选口径取保守侧**：仅 UPPER_SNAKE 且含 **≥2 个下划线** 的记号 —— 1 个下划线者
    （`OLLAMA_HOST` 一类）与外部环境变量高度重叠，纳入会使审计被误报淹没。
  * **检查三 · 文档头版本一致性**（本轮新增）：文档头版本号须等于**修订历史中的最高版本**。
    **口径说明（与设计原文的差异，如实登记）**：设计原文写「修订历史**末行**版本」，但本仓
    修订历史一律**最新在前**，末行即最旧版本（恒不相等，检查将失去意义）⇒ 本实现改为按
    **语义版本取最大**，对行序不作要求。该差异属**有理由的偏离**，已同步登记于 DevLogReport。

**适用对象（重要）**：三项检查**为「设计 / 方案 / 规划类文档」设计** —— 此类文档的反引号引用
多为**实施依据**（仓内应当存在）。对**问题跟踪记录 / DevLogReport** 一类「以记录缺失与缺陷
为职」的文档，检查一、检查二命中率**天然偏高**（其正文本就在陈述「某物不存在 / 待实现 /
建议新增」）⇒ 应**以检查三（文档头版本）为主**，检查一/二的命中**逐条人工判定**，不得据命中
数直接判缺陷（L3 走查实测：问题跟踪记录 43 + 5 项命中、DevLog 27 + 1 项，属此类预期噪声）。

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

    python <此脚本> <方案 md 路径> [额外扫描根（如 OpenBase 证据目录）] [--json]
    python <此脚本> --self-check        # 以两个已知历史个案为断言，不符即退出码非 0
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
#: 静态检查工具（ruff 等）的规则码（如 `UP006`/`F401`）⇒ 非本仓符号，跳过
#: （L3 走查实测：首版把 `UP006` / `UP031` 误报为缺失）
LINT_CODE_RE = re.compile(r"^[A-Z]{1,4}\d{3,4}$")

STATUS_WORDS = {"PASS", "FAIL", "SKIP", "BLOCKED", "TRUE", "FALSE", "NONE", "DRAFT", "REVIEW"}
#: 正文**邻近上下文**出现以下标记 ⇒ 该引用是「引用为缺失」，不做存在性要求
#: **须保持精简**：过于宽泛的标记（如「返回空」「解析为」）会吞掉整行、使审计失去意义
ABSENCE_MARKERS = (
    "零命中", "不存在", "无此键", "未实施", "未接线", "未做", "待登记", "待裁定",
    "幻影", "误填", "订正为", "未随提交", "本就不该",
)
#: 外部产品/环境变量/语言关键字等（非本仓符号）
EXTERNAL = {
    "OLLAMA_KEEP_ALIVE", "OLLAMA_MODELS", "OLLAMA_HOST", "num_ctx",
    "json_extract", "Sequence",
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

#: 配置键候选：UPPER_SNAKE 且 **≥2 个下划线**（保守口径，见模块 docstring）
SETTINGS_KEY_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+){2,}$")
#: `Settings` 字段声明（4 空格缩进 + `NAME: 类型`）
SETTINGS_FIELD_RE = re.compile(r"^\s{1,8}([A-Z][A-Z0-9_]{2,})\s*:\s*", re.MULTILINE)
#: 版本记号 `v1.2.3`
VERSION_TOKEN_RE = re.compile(r"v(\d+\.\d+\.\d+)")
#: 文档头版本行（**精确匹配「文档版本」优先**，避免与「版本号」混淆）
HEADER_VERSION_RES = (
    re.compile(r"\|\s*文档版本\s*\|\s*v(\d+\.\d+\.\d+)\s*\|"),
    re.compile(r"\|\s*版本\s*\|\s*v(\d+\.\d+\.\d+)\s*\|"),
)
#: 修订历史章节标题
REVISION_HEADING_RE = re.compile(r"^#+\s*[^\n]*(修订历史|变更历史|修订记录)[^\n]*$", re.MULTILINE)


def _tokens_with_context(doc_text: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for match in re.finditer(r"`([^`\n]{1,60})`", doc_text):
        raw = match.group(1).strip()
        if WILDCARD_RE.match(raw) or raw.endswith("_") or " " in raw or not raw:
            continue
        token = raw.strip(":（()）[],.;*")
        if (
            not token
            or token in STATUS_WORDS
            or HASH_RE.match(token)
            or LINT_CODE_RE.match(token)
            or token in EXTERNAL
        ):
            continue
        if token in EVIDENCE_ABSENT:
            continue
        if not (UPPER_RE.match(token) or SNAKE_RE.match(token) or CLASS_RE.match(token)):
            continue
        start = max(0, match.start() - 80)
        end = min(len(doc_text), match.end() + 80)
        result.setdefault(token, []).append(doc_text[start:end])
    return result


def _contexts_by_token(doc_text: str) -> dict[str, list[str]]:
    """所有反引号记号的 ±80 字符上下文（配置键检查与符号检查共用口径）"""
    result: dict[str, list[str]] = {}
    for match in re.finditer(r"`([^`\n]{1,60})`", doc_text):
        token = match.group(1).strip().strip(":（()）[],.;*")
        if not token:
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


def settings_keys(sources: dict[str, str]) -> set[str]:
    """从 `app/core/config.py` 的 `Settings` 类体提取字段名（仅该类，遇下一个 class 即止）"""
    keys: set[str] = set()
    for path, text in sources.items():
        if not path.endswith("core/config.py"):
            continue
        head = re.search(r"^class\s+Settings\b", text, re.MULTILINE)
        if not head:
            continue
        tail = text[head.end():]
        nxt = re.search(r"^class\s+", tail, re.MULTILINE)
        body = tail[: nxt.start()] if nxt else tail
        keys.update(SETTINGS_FIELD_RE.findall(body))
    return keys


def config_key_claims(doc_text: str) -> dict[str, list[str]]:
    """配置键候选（UPPER_SNAKE 且 ≥2 下划线 ⇒ 保守口径，避免与外部环境变量混淆）"""
    claims: dict[str, list[str]] = {}
    for token, contexts in _contexts_by_token(doc_text).items():
        if SETTINGS_KEY_RE.match(token):
            claims[token] = contexts
    return claims


def check_config_keys(
    doc_text: str, sources: dict[str, str], keys: set[str] | None = None
) -> dict[str, list[dict[str, object]]]:
    """检查二：配置键存在性。返回 `missing_keys`（硬缺口）与 `source_only_keys`（提示）"""
    known_keys = settings_keys(sources) if keys is None else keys
    missing: list[dict[str, object]] = []
    source_only: list[dict[str, object]] = []
    for token, contexts in sorted(config_key_claims(doc_text).items()):
        if token in known_keys:
            continue
        entry = {
            "key": token,
            "known_absent": any(
                any(marker in context for marker in ABSENCE_MARKERS) for context in contexts
            ),
        }
        (source_only if _exists(token, sources) else missing).append(entry)
    return {"missing_keys": missing, "source_only_keys": source_only}


def _revision_sections(doc_text: str) -> list[str]:
    """所有「标题含修订关键词」的章节正文（取**并集**，每个章节截到下一个二级标题）

    **不能只取首个命中**：正文里的**交叉引用**会先被匹配（如 DevLog §3.1 标题内即含
    「逐批详见 §8 修订历史」），而该章节内并无版本行 —— 首版即因此把 DevLog 误判为
    `revision_section_absent`。
    """
    sections: list[str] = []
    for heading in REVISION_HEADING_RE.finditer(doc_text):
        section = doc_text[heading.start():]
        nxt = re.search(r"\n##\s+\S", section[1:])
        sections.append(section[: nxt.start() + 1] if nxt else section)
    return sections


def _revision_versions(doc_text: str) -> list[str]:
    """修订历史表中**首列（版本列）**的版本号（跨所有候选章节取并集）

    **只取首列**：摘要列常引用他文档版本（如「问题跟踪记录 v1.63.0」），若整段取用会误报。
    （L3 走查实测：首版整段取用 ⇒ 技术方案 v1.26.0 被误判 `header_behind`，最高版本
    取自摘要列中的 v1.63.0。）
    """
    versions: list[str] = []
    for section in _revision_sections(doc_text):
        for line in section.splitlines():
            stripped = line.lstrip()
            if not stripped.startswith("|"):
                continue
            first_cell = stripped.lstrip("|").split("|")[0]
            match = VERSION_TOKEN_RE.search(first_cell)
            if match:
                versions.append(match.group(1))
    return versions


def check_header_version(doc_text: str) -> dict[str, object]:
    """检查三：文档头版本须等于**修订历史中的最高版本**（口径说明见模块 docstring）"""
    header = doc_header_version(doc_text)
    revisions = _revision_versions(doc_text)
    latest = max(revisions, key=_version_tuple) if revisions else None
    if not header:
        verdict = "header_absent"
    elif not latest:
        verdict = "revision_section_absent"  # ⇒ 本检查**不适用**，非「不一致」
    elif header == latest:
        verdict = "ok"
    else:
        verdict = "header_ahead" if _version_tuple(header) > _version_tuple(latest) else "header_behind"
    return {
        "header_version": header,
        "revision_versions": len(revisions),
        "latest_revision_version": latest,
        "consistent": None if verdict == "revision_section_absent" else verdict == "ok",
        "verdict": verdict,
    }


def doc_header_version(doc_text: str) -> str | None:
    """文档头版本号（仅在前 20 行内取，避免误取正文提及的版本）"""
    head = "\n".join(doc_text.splitlines()[:20])
    for pattern in HEADER_VERSION_RES:
        match = pattern.search(head)
        if match:
            return match.group(1)
    return None


def _version_tuple(version: str) -> tuple[int, int, int]:
    major, minor, patch = version.split(".")
    return int(major), int(minor), int(patch)


#: `--self-check` 夹具：两个已知历史个案（幻影配置键 / 文档头版本漂移）
SELF_CHECK_FIXTURE = """
# 自检夹具（非真实文档）

| 项目 | 内容 |
|------|------|
| 文档版本 | v1.32.1 |

正文引用了 `OPENLLM_PROFILE_LLM_REFINE`（幻影键）与 `CONTEXT_REFINE_INFERENCE_TARGET`（真实键）。

## 9. 修订历史

| 版本 | 日期 | 摘要 |
|------|------|------|
| v1.32.0 | 2026-09-01 | 上一版 |
| v1.31.0 | 2026-08-20 | 更早 |
"""


def _self_check() -> int:
    """以两个已知历史个案为断言（不符即退出码非 0）—— 使本工具自身可复跑验证"""
    sources = _sources(None)
    if not sources:
        print("[SELF-CHECK] FAIL：未找到扫描源（须在 OpenLLM/backend 下运行）")
        return 2
    keys = settings_keys(sources)
    if not keys:
        print("[SELF-CHECK] FAIL：未能从 app/core/config.py 提取 Settings 字段")
        return 2

    key_result = check_config_keys(SELF_CHECK_FIXTURE, sources, keys)
    missing = {entry["key"] for entry in key_result["missing_keys"]}
    version_result = check_header_version(SELF_CHECK_FIXTURE)

    checks = [
        ("Settings 字段可提取（>0）", len(keys) > 0),
        ("幻影键 `OPENLLM_PROFILE_LLM_REFINE` 稳定复现告警", "OPENLLM_PROFILE_LLM_REFINE" in missing),
        ("真实键 `CONTEXT_REFINE_INFERENCE_TARGET` 不误报", "CONTEXT_REFINE_INFERENCE_TARGET" not in missing),
        ("文档头 v1.32.1 与修订历史最高 v1.32.0 判为不一致", version_result["consistent"] is False),
        ("版本漂移方向判为 header_ahead", version_result["verdict"] == "header_ahead"),
        ("文档头版本可正确提取（v1.32.1）", version_result["header_version"] == "1.32.1"),
    ]
    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"[SELF-CHECK] {'PASS' if ok else 'FAIL'}：{name}")
    print(
        f"[SELF-CHECK] Settings 字段 {len(keys)} 个；幻影键告警 "
        f"{sorted(missing)}；版本判定 {version_result['verdict']}"
    )
    if failed:
        print(f"[SELF-CHECK] **共 {len(failed)} 项不符 ⇒ 退出码 1**")
        return 1
    print("[SELF-CHECK] 全部通过")
    return 0


def main() -> int:
    if "--self-check" in sys.argv:
        return _self_check()
    if len(sys.argv) < 2:
        print(
            "用法: python check_doc_claims.py <方案 md 路径> [额外扫描根] [--json]\n"
            "      python check_doc_claims.py --self-check"
        )
        return 2
    with open(sys.argv[1], encoding="utf-8") as handle:
        doc_text = handle.read()
    extra_root = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None
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

    keys = settings_keys(sources)
    key_checks = check_config_keys(doc_text, sources, keys)
    version_check = check_header_version(doc_text)

    print(f"扫描源: {len(sources)} 个 .py（含 {'OpenBase 证据目录' if extra_root else '仅 OpenLLM'}）")
    print("")
    print("=== 检查一 · 符号存在性 ===")
    print(f"「引用为缺失 / 族前缀」已跳过: {skipped}")
    print(f"「引用为存在」待核对: {checked}")
    print(f"**仓内查无此项（需判定「文档错」还是「实现缺」）: {len(missing)}**")
    for token in missing:
        print(f"  [MISSING] {token}")

    print("")
    print("=== 检查二 · 配置键存在性 ===")
    print(f"`Settings` 已声明字段: {len(keys)}")
    print(f"**硬缺口（既不在 Settings、也不在源码）: {len(key_checks['missing_keys'])}**")
    for entry in key_checks["missing_keys"]:
        flag = "（正文已自述其不存在）" if entry["known_absent"] else "（**正文未自述 ⇒ 疑似新增漂移**）"
        print(f"  [KEY-MISSING] {entry['key']}{flag}")
    print(f"提示（不在 Settings 但在源码，如模块级常量）: {len(key_checks['source_only_keys'])}")
    for entry in key_checks["source_only_keys"]:
        print(f"  [KEY-SOURCE-ONLY] {entry['key']}")

    print("")
    print("=== 检查三 · 文档头版本一致性 ===")
    print(
        f"文档头版本: {version_check['header_version']}；"
        f"修订历史版本条目: {version_check['revision_versions']}；"
        f"最高版本: {version_check['latest_revision_version']}"
    )
    verdict = version_check["verdict"]
    verdict_text = (
        "一致"
        if verdict == "ok"
        else "**不适用**（未找到含版本行的修订历史章节）⇒ 需人工确认"
        if verdict == "revision_section_absent"
        else f"不一致（{verdict}）"
    )
    print(f"**判定: {verdict_text}**")

    report = {
        "probe": "check_doc_claims",
        "design_doc": os.path.basename(sys.argv[1]),
        "scanned_py_files": len(sources),
        "check1_symbol_existence": {
            "skipped_as_absent_or_prefix": skipped,
            "checked_as_claimed_present": checked,
            "missing": missing,
        },
        "check2_config_keys": {
            "settings_declared_keys": len(keys),
            "missing_keys": key_checks["missing_keys"],
            "source_only_keys": key_checks["source_only_keys"],
        },
        "check3_header_version": version_check,
        "method_note": (
            "区分「引用为存在」（须查到）与「引用为缺失/族前缀」（跳过）；"
            "首版未区分且不扫 tests/，曾误报 68 项；删除整行级跳过以免审计被宽泛标记吞掉。"
            "配置键检查口径：UPPER_SNAKE 且 ≥2 下划线（保守侧），"
            "**不套用缺席标记跳过**，改为标注 known_absent 以区分「已自述个案」与「新增漂移」；"
            "已知局限：source_only 桶无法区分「被使用」与「被负向断言为不存在」，须人工过目。"
            "文档头版本检查口径：与设计原文「末行」不同，改按**语义版本取最大**，"
            "因本仓修订历史最新在前、末行恒为最旧版本；且**只取表首列（版本列）**，"
            "因摘要列常引用他文档版本（首版整段取用致技术方案被误判 header_behind）。"
            "符号检查中，静态检查工具规则码（如 UP006/F401）按模式跳过（L3 实测误报）。"
            "适用对象：检查为「设计/方案/规划类文档」设计；对问题跟踪记录 / DevLog 一类"
            "「以记录缺失为职」的文档，检查一/二命中属预期噪声，应以检查三为主并逐条人工判定。"
            "修订历史章节取**所有含关键词标题的并集**（避免被交叉引用标题抢先命中，"
            "首版因此把 DevLog 误判 revision_section_absent）。"
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
