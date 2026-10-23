"""发布强制核验：生产必需开关矩阵逐项检查（v1.10.2 / XR-OPS-06 S4 仓库侧）.

依据《OpenBase-五系统多租户与授权集成总览与续接指南》§10.3：
各仓新增的生产强制门禁开关必须由运维在目标环境 `.env` 显式置真，否则生产启动被拒
（fail-closed）。本脚本把这项「部署当场失败」风险提前到**发布门禁**：

- carrier 模式（默认）：检查各仓**仓库载体**（`.env.example` / 文档）是否按矩阵登记生产值；
- env-file 模式：检查**实际下发的环境文件**是否包含矩阵要求的键值。

用法::

    python scripts/verify_production_switches.py
    python scripts/verify_production_switches.py --only OpenLLM --json out.json
    python scripts/verify_production_switches.py --env-file .env.production --repo OpenLLM

退出码：``0`` = 全部 PASS；``1`` = 存在 FAIL（禁止发布）。
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from dataclasses import dataclass, field
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_MATRIX = ROOT / "config" / "production_switch_matrix.json"
DEFAULT_REPOS_ROOT = ROOT.parent

PASS, FAIL = "PASS", "FAIL"


@dataclass
class CheckResult:
    """单仓单人检查结果."""

    repo: str
    key: str
    status: str
    detail: str
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo": self.repo,
            "key": self.key,
            "status": self.status,
            "detail": self.detail,
            "source": self.source,
        }


@dataclass
class Report:
    """聚合报告."""

    results: list[CheckResult] = field(default_factory=list)

    @property
    def failed(self) -> list[CheckResult]:
        return [item for item in self.results if item.status == FAIL]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": len(self.results),
            "passed": len(self.results) - len(self.failed),
            "failed": len(self.failed),
            "results": [item.to_dict() for item in self.results],
        }


def parse_env_assignments(text: str) -> dict[str, str]:
    """解析 ``KEY=VALUE`` 形态（支持 ``export`` 前缀、行内注释、引号包裹）."""
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.split(" #", 1)[0].strip()
        if value.startswith(("'", '"')) and value[-1:] == value[:1] and len(value) >= 2:
            value = value[1:-1]
        if key:
            values[key] = value
    return values


def find_carrier(repo_root: pathlib.Path, carriers: list[str]) -> pathlib.Path | None:
    """按矩阵顺序返回第一个存在的载体文件."""
    for relative in carriers:
        candidate = repo_root / relative
        if candidate.is_file():
            return candidate
    return None


def _value_in_doc(value: str, expected: str) -> bool:
    """文档载体判定：在键后文本中按词元匹配期望值（容忍表格/说明/反引号写法）."""
    tokens = re.split(r"[^0-9A-Za-z_.]+", value.casefold())
    return expected.casefold() in tokens


#: documented_override 模式下，生产覆盖说明允许出现在密钥行的上下文行数（双向）
OVERRIDE_CONTEXT_RADIUS = 8


def _override_documented(lines: list[str], index: int, hints: list[str]) -> bool:
    """密钥行邻近上下文是否包含全部生产覆盖提示词（大小写不敏感）."""
    start = max(index - OVERRIDE_CONTEXT_RADIUS, 0)
    end = min(index + OVERRIDE_CONTEXT_RADIUS + 1, len(lines))
    block = "\n".join(lines[start:end]).casefold()
    return all(hint.casefold() in block for hint in hints)


def check_runtime_gate(
    repo_name: str,
    repo_root: pathlib.Path,
    gate_spec: dict[str, Any] | None,
) -> CheckResult | None:
    """校验运行期 fail-closed 守卫存在（documented_override 模式的机械保证）."""
    if not gate_spec:
        return None
    relative = gate_spec.get("file") or ""
    marker = gate_spec.get("marker") or ""
    path = repo_root / relative
    if not relative or not marker:
        return CheckResult(repo_name, "runtime_gate", FAIL, "runtime_gate 声明不完整")
    if not path.is_file():
        return CheckResult(repo_name, "runtime_gate", FAIL, f"守卫文件不存在：{relative}")
    if marker not in path.read_text(encoding="utf-8", errors="replace"):
        return CheckResult(
            repo_name, "runtime_gate", FAIL, f"守卫文件缺少标记 {marker!r}：{relative}", source=str(path)
        )
    return CheckResult(repo_name, "runtime_gate", PASS, f"运行期守卫存在：{relative}", source=str(path))


def check_carrier_repo(
    repo_name: str,
    repo_root: pathlib.Path,
    spec: dict[str, Any],
) -> list[CheckResult]:
    """carrier 模式：检查仓库载体是否满足矩阵要求（按 mode 分流）."""
    switches: dict[str, str] = spec.get("switches") or {}
    mode = spec.get("mode") or "template_value"
    gate_result = check_runtime_gate(repo_name, repo_root, spec.get("runtime_gate"))
    if not switches:
        return [CheckResult(repo_name, "-", PASS, "该仓无新增生产开关（矩阵豁免）")]

    carriers: list[str] = spec.get("carriers") or []
    carrier = find_carrier(repo_root, carriers)
    if carrier is None:
        missing = [
            CheckResult(
                repo_name,
                key,
                FAIL,
                f"载体缺失（尝试：{', '.join(carriers) or '未声明'}）",
                source=str(repo_root),
            )
            for key in switches
        ]
        return missing + ([gate_result] if gate_result else [])

    text = carrier.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    assignments = parse_env_assignments(text)
    results: list[CheckResult] = []

    for key, expected in switches.items():
        if mode == "documented_override":
            key_lines = [index for index, line in enumerate(lines) if key in line]
            if key not in assignments and not key_lines:
                results.append(
                    CheckResult(repo_name, key, FAIL, "载体未登记该开关", source=str(carrier))
                )
                continue
            hints = list(spec.get("override_hints") or [])
            documented = any(_override_documented(lines, index, hints) for index in key_lines)
            if not documented:
                results.append(
                    CheckResult(
                        repo_name,
                        key,
                        FAIL,
                        f"未在密钥邻近注释中写明生产覆盖值 {expected!r}（需含 {hints}）",
                        source=str(carrier),
                    )
                )
            else:
                actual = assignments.get(key, "未赋值")
                results.append(
                    CheckResult(
                        repo_name,
                        key,
                        PASS,
                        f"模板默认 {actual}（开发态），已文档化生产覆盖 {expected}",
                        source=str(carrier),
                    )
                )
            continue

        if key in assignments:
            actual = assignments[key]
        else:
            # 文档载体：按「KEY + 期望值」组合判定（容忍表格/说明写法）
            matched = any(
                key in line and _value_in_doc(line.split(key, 1)[1], expected) for line in lines
            )
            actual = expected if matched else None

        if actual is None:
            results.append(
                CheckResult(repo_name, key, FAIL, "载体未登记该开关", source=str(carrier))
            )
        elif actual.lower() != expected.lower():
            results.append(
                CheckResult(
                    repo_name,
                    key,
                    FAIL,
                    f"载体值为 {actual!r}，生产要求 {expected!r}",
                    source=str(carrier),
                )
            )
        else:
            results.append(
                CheckResult(repo_name, key, PASS, f"{key}={expected}", source=str(carrier))
            )

    if gate_result:
        results.append(gate_result)
    return results


def check_env_file(repo_name: str, env_path: pathlib.Path, switches: dict[str, str]) -> list[CheckResult]:
    """env-file 模式：检查实际下发文件中的键值."""
    if not env_path.is_file():
        return [
            CheckResult(repo_name, key, FAIL, f"环境文件不存在：{env_path}", source=str(env_path))
            for key in switches
        ]
    assignments = parse_env_assignments(env_path.read_text(encoding="utf-8", errors="replace"))
    results: list[CheckResult] = []
    for key, expected in switches.items():
        actual = assignments.get(key)
        if actual is None:
            results.append(
                CheckResult(repo_name, key, FAIL, "未下发该开关", source=str(env_path))
            )
        elif actual.lower() != expected.lower():
            results.append(
                CheckResult(
                    repo_name,
                    key,
                    FAIL,
                    f"下发值为 {actual!r}，生产要求 {expected!r}",
                    source=str(env_path),
                )
            )
        else:
            results.append(CheckResult(repo_name, key, PASS, f"{key}={expected}", source=str(env_path)))
    return results


def load_matrix(path: pathlib.Path) -> dict[str, Any]:
    """读取矩阵（校验结构）."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    repos = payload.get("repos")
    if not isinstance(repos, dict) or not repos:
        raise ValueError("矩阵缺少 repos 定义")
    return payload


def run_carrier_check(
    matrix: dict[str, Any],
    repos_root: pathlib.Path,
    only: str | None = None,
) -> Report:
    """carrier 模式批量检查."""
    report = Report()
    for repo_name, spec in (matrix.get("repos") or {}).items():
        if only and repo_name.lower() != only.lower():
            continue
        report.results.extend(check_carrier_repo(repo_name, repos_root / repo_name, spec))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生产必需开关矩阵发布核验")
    parser.add_argument("--matrix", type=pathlib.Path, default=DEFAULT_MATRIX)
    parser.add_argument("--repos-root", type=pathlib.Path, default=DEFAULT_REPOS_ROOT)
    parser.add_argument("--only", help="仅检查指定仓（大小写不敏感）")
    parser.add_argument("--env-file", type=pathlib.Path, help="检查实际下发的环境文件")
    parser.add_argument("--repo", help="与 --env-file 搭配，指定所用矩阵条目")
    parser.add_argument("--json", type=pathlib.Path, help="报告落盘路径")
    args = parser.parse_args(argv)

    try:
        matrix = load_matrix(args.matrix)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"[FAIL] 无法读取矩阵 {args.matrix}: {error}", file=sys.stderr)
        return 1

    if args.env_file:
        repo_name = args.repo or next(iter(matrix["repos"]))
        spec = matrix["repos"].get(repo_name)
        if spec is None:
            print(f"[FAIL] 矩阵无该仓条目：{repo_name}", file=sys.stderr)
            return 1
        report = Report(results=check_env_file(repo_name, args.env_file, spec.get("switches") or {}))
    else:
        report = run_carrier_check(matrix, args.repos_root, args.only)

    payload = report.to_dict()
    for item in report.results:
        marker = "PASS" if item.status == PASS else "FAIL"
        print(f"[{marker}] {item.repo} · {item.key} · {item.detail}（{item.source}）")
    print(
        f"合计 {payload['total']} 项：PASS {payload['passed']} / FAIL {payload['failed']}"
    )

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return 0 if not report.failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
