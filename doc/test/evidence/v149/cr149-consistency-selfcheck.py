"""v1.4.9 Step 3 变更一致性自检（门禁 3.9b）。

三件事，逐项出具可复现结果：
  ① 命名合规     —— 本版本新增/改动文档文件的命名是否符合「OpenBase-<文档名>-<版本号>.md」/「cr149-<用途>-<YYYYMMDD>.<ext>」约定
  ② 版本一致     —— 文档表头「文档版本」是否等于「修订历史」首行版本号
  ③ 路径合规     —— 新增文件是否落在规范目录内

如实登记：本仓不存在 `validate-naming.ps1`，故以「命名规范核对」等价执行，
          并在输出中显式声明，避免「门禁已过」的表述掩盖工具缺位。

用法：
    python cr149-consistency-selfcheck.py            # 打印自检报告
    python cr149-consistency-selfcheck.py --repo <仓根>   # 指定仓根（默认按脚本位置上溯）
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

DOC_HEADER_VERSION = re.compile(r"文档版本\s*\|\s*\**v?([0-9]+(?:\.[0-9]+)*)")
REVISION_HEADING = re.compile(r"^##+\s*[0-9.]*\s*修订历史")
REVISION_ROW = re.compile(r"^\|\s*v([0-9]+(?:\.[0-9]+)*)\s*\|")

# 文档命名：OpenBase-<文档名>-v<X.Y.Z>.md
DOC_NAME_OK = re.compile(r"^OpenBase-.+-v[0-9]+\.[0-9]+\.[0-9]+\.md$")
# 证据命名：小写 snake_case/kebab-case ＋ 受控扩展名（与 evidence/ 下既有脚本一致）
EVIDENCE_NAME_OK = re.compile(r"^[a-z0-9][a-z0-9_-]*\.(py|json|txt|log)$")

ALLOWED_DIRS = (
    "doc/design",
    "doc/development",
    "doc/audit/review",
    "doc/audit/verification",
    "doc/audit/comprehensive",
    "doc/requirements",
    "doc/release",
    "doc/test",
    "doc/version/releases",
)

#: **跨版本全局文档**目录：其文件名**不含版本号**（如《技术债务总表》《候选需求池》《路线图》），
#: 命名判据不适用（版本以文头「文档版本」字段表达），故显式豁免而非误判为「不合规」。
GLOBAL_DOC_DIRS = (
    "doc/version/global",
    "doc/planning",
)

#: **跨版本汇总文档**（单文件，位于版本目录内但文件名不含版本号）：
#: 如《Release Note 汇总（-All）》，其按版本列表逐行收录，版本以行为单位表达，
#: 与 GLOBAL_DOC_DIRS 同类，命名判据同样不适用 ⇒ 显式豁免。
GLOBAL_DOC_FILES = (
    "doc/release/OpenBase-Release-Note-All.md",
)


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return completed.stdout or ""


def changed_doc_files(repo: Path) -> list[tuple[str, str]]:
    """返回 [(状态, 相对路径)]；用 -z 避免中文名被八进制转义，跳过目录条目。"""
    out = _git(repo, "status", "--porcelain", "-z")
    entries: list[tuple[str, str]] = []
    for chunk in out.split("\0"):
        if len(chunk) < 4:
            continue
        status, path = chunk[:2], chunk[3:]
        if path.endswith("/") or not path.startswith("doc/"):
            continue
        entries.append((status.strip(), path))
    return entries


def check_naming(repo: Path, entries: list[tuple[str, str]]) -> int:
    print("=== ① 命名合规 ===")
    print("**如实登记**：本仓**不存在** `validate-naming.ps1` ⇒ 以「**文件命名规范核对**」等价执行：")
    print("  · 技术文档：`OpenBase-<文档名>-v<X.Y.Z>.md`")
    print("  · 证据文件：小写 snake_case/kebab-case ＋ 受控扩展名（`.py/.json/.txt/.log`）")
    print()
    bad = 0
    for status, path in entries:
        name = Path(path).name
        if any(path.startswith(directory) for directory in GLOBAL_DOC_DIRS) or path in GLOBAL_DOC_FILES:
            print(f"  OK {status:<2} {path}  （跨版本全局文档：文件名不含版本号，命名判据豁免）")
            continue
        is_evidence = "/evidence/" in path
        ok = EVIDENCE_NAME_OK.match(name) if is_evidence else DOC_NAME_OK.match(name)
        if not ok:
            bad += 1
        print(f"  {'OK' if ok else 'NG'} {status:<2} {path}")
    print(f"命名核对：{len(entries)} 个待提交/待跟踪文档文件，**不合规 {bad} 个**")
    print()
    return bad


def check_versions(repo: Path) -> int:
    print("=== ② 文件头版本号 vs 修订历史首行版本号 ===")
    candidates = sorted(p for p in repo.glob("doc/**/*v1.4.9*.md") if p.is_file())
    checked = 0
    mismatched: list[tuple[str, str, str]] = []
    for path in candidates:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        header = DOC_HEADER_VERSION.search(text)
        if not header:
            continue
        revision_version = None
        in_revision = False
        for line in text.splitlines():
            if REVISION_HEADING.match(line.strip()):
                in_revision = True
                continue
            if in_revision:
                row = REVISION_ROW.match(line.strip())
                if row:
                    revision_version = row.group(1)
                    break
        if revision_version is None:
            continue
        checked += 1
        rel = path.relative_to(repo).as_posix()
        if header.group(1) == revision_version:
            print(f"  OK  {rel}")
        else:
            mismatched.append((rel, header.group(1), revision_version))
            print(f"  NG  {rel}  表头 v{header.group(1)} vs 修订历史 v{revision_version}")
    print(f"核对份数：{checked}")
    if mismatched:
        print("不一致明细：")
        for rel, head, rev in mismatched:
            print(f"  - {rel}：表头 v{head} ≠ 修订历史 v{rev}")
    else:
        print("不一致明细：无（全部一致）")
    print()
    return len(mismatched)


def check_paths(repo: Path, entries: list[tuple[str, str]]) -> int:
    print("=== ③ 新建文件路径与命名规范匹配 ===")
    new_files = [p for status, p in entries if status == "??"]
    print(f"本版本新增（未跟踪）文档文件：{len(new_files)} 个")
    bad = [p for p in new_files if not any(p.startswith(d) for d in ALLOWED_DIRS)]
    if bad:
        for p in bad:
            print(f"  NG  {p}")
    else:
        print("  全部落在规范目录内（doc/design、doc/development、doc/audit/review、doc/audit/verification、doc/requirements、doc/test、doc/version/releases）")
    print()
    return len(bad)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=None, help="仓根（默认按脚本位置上溯到含 .git 的目录）")
    parser.add_argument("--out", default=None, help="同时把报告写入该文件（UTF-8 无 BOM，供证据入仓）")
    args = parser.parse_args()

    if args.out:
        buffer: list[str] = []
        original_print = print

        def tee(*values: object, **kwargs: object) -> None:  # type: ignore[override]
            original_print(*values, **kwargs)
            buffer.append(" ".join(str(v) for v in values))

        globals()["print"] = tee
    else:
        buffer = []

    repo = Path(args.repo).resolve() if args.repo else Path(__file__).resolve()
    if args.repo is None:
        for parent in [repo, *repo.parents]:
            if (parent / ".git").exists():
                repo = parent
                break
    if not (repo / ".git").exists():
        print(f"[FATAL] 未定位到 git 仓根：{repo}", file=sys.stderr)
        return 2

    print("=== v1.4.9 Step 3 变更一致性自检（3.9b）===")
    print(f"时间：{dt.datetime.now(dt.timezone.utc).isoformat()}")
    print(f"仓根：{repo}")
    print(f"自检脚本：{Path(__file__).name}（已入仓，命令可复现）")
    print()

    entries = changed_doc_files(repo)
    failures = 0
    failures += check_naming(repo, entries)
    failures += check_versions(repo)
    failures += check_paths(repo, entries)

    print(f"=== 结论 ===\n不合规项合计：{failures}")

    if args.out:
        Path(args.out).write_text("\n".join(buffer) + "\n", encoding="utf-8")

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
