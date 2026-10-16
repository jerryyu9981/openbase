"""跨仓源码编码契约扫描器（UTF-8 BOM 基线）。

**为什么两类文件的期望相反**：

- Python 源码带 BOM 对**执行**无碍，但会使以 `ast.parse(文本)` 做源码扫描的工具链直接报
  `SyntaxError: invalid non-printable character` → 故 `.py` **必须无 BOM**；
- Windows PowerShell 5.1（本机默认）对**无 BOM** 的 UTF-8 源文件按 **GBK** 解码，中文注释会致
  `Parser::ParseFile` 报错 → 故 `.ps1` **期望带 BOM**。

**契约（本模块为单一事实源）**：

| 规则 | 扩展名 | 判据 | 违规类型 |
|------|--------|------|----------|
| `REQUIRED_NO_BOM` | `.py` | **不得**带 BOM | `bom_forbidden_py`（FAIL） |
| `REQUIRED_BOM_IF_NON_ASCII` | `.ps1` | 含非 ASCII 则**必须**带 BOM | `ps1_bom_required_non_ascii`（FAIL） |
| 其余 `TEXT_EXTENSIONS` | `.json`/`.md`/`.sql`/`.ts`/… | 未定 | 仅统计上报（不计失败） |

`doc/tmp`（临时工作目录，`.gitignore` 覆盖）整体排除，不作为契约面。

**用法**：

    python -B scripts/scan_source_encoding.py                  # 契约校验（违规即 exit 1）
    python -B scripts/scan_source_encoding.py --json           # 输出 JSON 报告
    python -B scripts/scan_source_encoding.py --json --out <path>
    python -B scripts/scan_source_encoding.py --strip-py       # 剥离 .py 的 BOM（字节级、三重校验）
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Iterable, Iterator
from pathlib import Path

# ==================== 契约（单一事实源） ====================
REQUIRED_NO_BOM: frozenset[str] = frozenset({".py"})
REQUIRED_BOM_IF_NON_ASCII: frozenset[str] = frozenset({".ps1"})
TEXT_EXTENSIONS: frozenset[str] = frozenset(
    {".py", ".ps1", ".json", ".md", ".yml", ".yaml", ".sql", ".ts", ".js", ".vue", ".txt"}
)

UTF8_BOM = b"\xef\xbb\xbf"

# ==================== 扫描范围 ====================
# 本仓（OpenBase）为跨仓治理位：以「Dev 目录下的同级仓」为默认扫描根
OPENBASE_ROOT = Path(__file__).resolve().parents[1]
BASE_DIR = OPENBASE_ROOT.parent
REPOS: tuple[str, ...] = ("OpenBase", "OpenLLM", "OpenRAG", "OpenMemory", "DPS")

EXCLUDED_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        "node_modules",
        "extras",
        ".pylib",
        "__pycache__",
        "dist",
        "build",
        ".mypy_cache",
        ".ruff_cache",
        "htmlcov",
        "site-packages",
    }
)
EXCLUDED_DIR_PREFIXES: tuple[str, ...] = (".venv",)
# 临时工作目录（`.gitignore` 覆盖）整体排除，不作为契约面
EXCLUDED_RELATIVE_DIRS: tuple[tuple[str, ...], ...] = (("doc", "tmp"),)


def discover_roots(base: Path = BASE_DIR) -> list[Path]:
    """发现参与契约的仓根（仅取实际存在的同级仓目录）"""
    return [base / name for name in REPOS if (base / name).is_dir()]


def _is_excluded_dir(name: str) -> bool:
    return name in EXCLUDED_DIRS or name.startswith(EXCLUDED_DIR_PREFIXES)


def iter_files(root: Path, extensions: frozenset[str] = TEXT_EXTENSIONS) -> Iterator[Path]:
    """按扩展名枚举仓内文件（**遍历时剪枝**第三方 / 缓存 / 构建 / 临时目录，避免进入 `.git` 等大目录）"""
    for current, dirnames, filenames in os.walk(root):
        relative_parts = Path(current).relative_to(root).parts
        if relative_parts in EXCLUDED_RELATIVE_DIRS:
            dirnames[:] = []
            continue
        dirnames[:] = sorted(name for name in dirnames if not _is_excluded_dir(name))
        for filename in sorted(filenames):
            path = Path(current) / filename
            if path.suffix.lower() in extensions:
                yield path


def has_utf8_bom(path: Path) -> bool:
    with path.open("rb") as stream:
        return stream.read(len(UTF8_BOM)) == UTF8_BOM


def _has_non_ascii(path: Path) -> bool:
    """文件是否含非 ASCII 字符（读取失败按「含」处理，以保守留 WARN）"""
    try:
        return not path.read_text(encoding="utf-8-sig").isascii()
    except (UnicodeDecodeError, OSError):
        return True


def scan(roots: Iterable[Path] | None = None) -> dict:
    """执行契约扫描，返回 JSON 友好报告（`pass` 为 False 表示存在违规）"""
    resolved_roots = [Path(root) for root in roots] if roots is not None else discover_roots()

    scanned_files = 0
    bom_hits_by_kind: dict[str, int] = {}
    violations: list[dict] = []

    for root in resolved_roots:
        for path in iter_files(root):
            scanned_files += 1
            suffix = path.suffix.lower()
            relative = str(path.relative_to(root))
            has_bom = has_utf8_bom(path)
            if has_bom:
                kind = suffix.lstrip(".")
                bom_hits_by_kind[kind] = bom_hits_by_kind.get(kind, 0) + 1
            if has_bom and suffix in REQUIRED_NO_BOM:
                violations.append(
                    {"repo": root.name, "path": relative, "kind": "bom_forbidden_py"}
                )
            elif not has_bom and suffix in REQUIRED_BOM_IF_NON_ASCII and _has_non_ascii(path):
                violations.append(
                    {"repo": root.name, "path": relative, "kind": "ps1_bom_required_non_ascii"}
                )

    return {
        "roots": [str(root) for root in resolved_roots],
        "scanned_files": scanned_files,
        "bom_hits_total": sum(bom_hits_by_kind.values()),
        "bom_hits_by_kind": bom_hits_by_kind,
        "violations": violations,
        "policy": {
            "required_no_bom": sorted(REQUIRED_NO_BOM),
            "required_bom_if_non_ascii": sorted(REQUIRED_BOM_IF_NON_ASCII),
            "other_extensions": sorted(
                TEXT_EXTENSIONS - REQUIRED_NO_BOM - REQUIRED_BOM_IF_NON_ASCII
            ),
        },
        "pass": not violations,
    }


def strip_py_bom(path: Path) -> str:
    """剥离单个 `.py` 的 UTF-8 BOM（字节级，三重校验）。

    返回 `stripped` / `skipped`（无 BOM）/ `aborted`（解码不合法或内容不等价，未改动文件）。
    """
    data = path.read_bytes()
    if not data.startswith(UTF8_BOM):
        return "skipped"

    body = data[len(UTF8_BOM) :]
    try:
        text_before = data.decode("utf-8-sig")
        text_after = body.decode("utf-8")  # 严格解码：非法字节即抛错
    except UnicodeDecodeError:
        return "aborted"
    if text_before != text_after:
        return "aborted"

    path.write_bytes(body)
    return "stripped"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="跨仓源码编码契约扫描器（UTF-8 BOM 基线）")
    parser.add_argument("--json", action="store_true", help="输出 JSON 报告")
    parser.add_argument("--out", help="JSON 报告落盘路径")
    parser.add_argument("--strip-py", action="store_true", help="剥离 .py 的 UTF-8 BOM（字节级、三重校验）")
    parser.add_argument("--roots", nargs="*", help="自定义扫描根（默认参与契约的全部仓）")
    args = parser.parse_args(argv)

    roots = [Path(item) for item in args.roots] if args.roots else discover_roots()
    if not roots:
        print("未发现任何扫描根", file=sys.stderr)
        return 2

    if args.strip_py:
        stripped: list[str] = []
        aborted: list[str] = []
        for root in roots:
            for path in iter_files(root, extensions=REQUIRED_NO_BOM):
                outcome = strip_py_bom(path)
                if outcome == "stripped":
                    stripped.append(str(path))
                elif outcome == "aborted":
                    aborted.append(str(path))
        print(f"已剥离 {len(stripped)} 个 .py 的 BOM")
        for item in stripped:
            print(f"  stripped  {item}")
        for item in aborted:
            print(f"  aborted   {item}", file=sys.stderr)

    report = scan(roots)
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
    if args.json:
        print(payload)
    else:
        print(
            f"扫描 {report['scanned_files']} 个文件；BOM 命中 {report['bom_hits_total']} 个"
            f"（{report['bom_hits_by_kind']}）；违规 {len(report['violations'])}"
        )
        for item in report["violations"]:
            print(f"  VIOLATION {item['repo']}/{item['path']} ({item['kind']})")
        print(f"契约校验: {'PASS' if report['pass'] else 'FAIL'}")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
