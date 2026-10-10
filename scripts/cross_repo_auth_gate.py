#!/usr/bin/env python
"""D 批 D2：跨系统授权一致性门禁（静态校验，可纳入回归）。

校验五系统（OpenBase + OpenLLM/OpenRAG/OpenMemory/DPS）在**授权与多租户**四条契约轴上的一致性：

  1. **一致性矩阵完整性**（D1 制品）：覆盖全部系统、每条不变式至少被 1 格覆盖、每格齐备。
  2. **档位锚点一致性**：各仓「角色码 → 档位」映射与 `config/role_tier_anchors.json` 不矛盾。
  3. **错误码映射一致性**：`config/error_code_map.json` 中每个非空目标字面量可在该仓源码中检索到。
  4. **码空间登记一致性**：OpenBase 各目标兜底码**非该目标保留码**，且**已被目标登记**
     （OpenMemory 组织策略 / OpenRAG 租户注册表）——本轴即 C1-a 阻塞项的固化防线。
  5. **保留码防护未放宽**：各仓仍显式声明其保留码集合与拒绝路径。

用法：
    python scripts/cross_repo_auth_gate.py            # 人读输出
    python scripts/cross_repo_auth_gate.py --json out.json   # 落盘证据

退出码：0=全部 PASS（WARN 不算失败）；1=存在 FAIL。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = REPO_ROOT.parent

REPO_DIRS = {
    "openbase": REPO_ROOT,
    "openllm": WORKSPACE / "OpenLLM",
    "openrag": WORKSPACE / "OpenRAG",
    "openmemory": WORKSPACE / "OpenMemory",
    "dps": WORKSPACE / "DPS",
}

# 各目标的保留码（单一事实源：OpenBase settings + 各仓自身声明，见 check_reserved_not_relaxed）
TIER_ALIASES = {
    "readonly": "readonly",
    "read": "readonly",
    "read_only": "readonly",
    "readwrite": "readwrite",
    "read_write": "readwrite",
    "manage": "manage",
    # DPS 以 `ANCHOR_*` 常量书写档位：补别名使静态门禁可解析（否则整表退化为 WARN）
    "anchor_manage": "manage",
    "anchor_readwrite": "readwrite",
    "anchor_readonly": "readonly",
    "tier_readonly": "readonly",
    "tier_readwrite": "readwrite",
    "tier_manage": "manage",
    "role_tier_manage": "manage",
    "role_tier_readwrite": "readwrite",
    "role_tier_readonly": "readonly",
}
MATRIX_PATH = REPO_ROOT / "config" / "auth_consistency_matrix.json"
ANCHORS_PATH = REPO_ROOT / "config" / "role_tier_anchors.json"
ERROR_MAP_PATH = REPO_ROOT / "config" / "error_code_map.json"
ORCHESTRATOR = REPO_ROOT / "scripts" / "service-orchestrator.ps1"


@dataclass
class Result:
    check: str
    status: str  # PASS / FAIL / WARN
    detail: str

    def as_dict(self) -> dict:
        return {"check": self.check, "status": self.status, "detail": self.detail}


@dataclass
class Report:
    results: list[Result] = field(default_factory=list)

    def add(self, check: str, status: str, detail: str) -> None:
        self.results.append(Result(check, status, detail))

    @property
    def failed(self) -> list[Result]:
        return [r for r in self.results if r.status == "FAIL"]

    @property
    def warned(self) -> list[Result]:
        return [r for r in self.results if r.status == "WARN"]


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _norm_tier(raw: str) -> str | None:
    return TIER_ALIASES.get(re.sub(r"[^a-z_]", "", raw.strip().lower()))


def _extract_role_tier_pairs(text: str) -> dict[str, str]:
    """从源码文本粗提取「角色码 → 档位」映射（容错；仅取值可归一为档位者）.

    同时兼容两种写法：`"viewer": "readonly"` 与枚举式 `"viewer": LocalRoleTier.READ`
    （取「.」或「:」后最后一段作为档位名再归一）。
    """
    pairs: dict[str, str] = {}
    # 键兼容「引号字面量」与「常量符号」两种写法（后者如 `ROLE_VIEWER: TIER_READONLY`，
    # 2026-10-09 硬化：否则 RAG/LLM 的常量式映射无法解析，覆盖门禁退化为 WARN）。
    pattern = r'(["\']?)([A-Za-z_]\w*)\1\s*:\s*["\']?([A-Za-z_][A-Za-z_.:]*)["\']?'
    for _quote, raw_role, raw_tier in re.findall(pattern, text):
        role = re.sub(r"^role_", "", raw_role.strip().lower())
        tail = re.split(r"[.:]", raw_tier.strip())[-1]
        tier = _norm_tier(tail)
        if tier and role not in {"readonly", "readwrite", "manage", "read", "tier", "anchor"}:
            pairs.setdefault(role, tier)
    return pairs


# ---------------------------------------------------------------------------
# 1) 一致性矩阵完整性
# ---------------------------------------------------------------------------


def check_matrix(report: Report) -> None:
    if not MATRIX_PATH.exists():
        report.add("matrix.completeness", "FAIL", f"缺少矩阵制品：{MATRIX_PATH}")
        return
    doc = _load(MATRIX_PATH)
    cells = doc.get("cells") or []
    scope = doc.get("scope") or {}
    invariants = {i.split()[0] for i in doc.get("invariants") or []}

    problems: list[str] = []
    ids = [c.get("id") for c in cells]
    if len(ids) != len(set(ids)):
        problems.append("用例 id 重复")
    systems = {c.get("system") for c in cells}
    expected_systems = set(scope.get("systems") or [])
    missing_systems = {s for s in expected_systems if s != "*"} - systems
    if missing_systems:
        problems.append(f"未覆盖系统：{sorted(missing_systems)}")
    for required in ("id", "system", "endpoint", "subject", "tier", "tenant", "expected", "evidence"):
        for cell in cells:
            if not cell.get(required) and cell.get(required) != 0:
                problems.append(f"格 {cell.get('id')} 缺字段 {required}")
    covered: set[str] = set()
    for cell in cells:
        covered.update(cell.get("covers") or [])
    missing_invariants = invariants - covered
    if missing_invariants:
        problems.append(f"未覆盖不变式：{sorted(missing_invariants)}")

    report.add(
        "matrix.completeness",
        "FAIL" if problems else "PASS",
        "; ".join(problems) if problems else f"{len(cells)} 格齐备，覆盖 {len(systems)} 系统 / {len(covered)} 不变式",
    )


# ---------------------------------------------------------------------------
# 2) 档位锚点一致性
# ---------------------------------------------------------------------------


def check_tier_anchors(report: Report) -> None:
    anchors = _load(ANCHORS_PATH).get("anchors") or {}

    # 显式登记各仓「角色→档位」映射的**单一落点**（与 role_tier_anchors.json 的 consumers.module 对应）；
    # 不使用递归 glob，避免遍历 node_modules/构建产物
    consumer_files = {
        "openllm": REPO_DIRS["openllm"] / "backend" / "app" / "identity" / "role_map.py",
        "openrag": REPO_DIRS["openrag"] / "src" / "openrag" / "identity" / "role_map.py",
        "openmemory": REPO_DIRS["openmemory"] / "src" / "openmemory" / "identity" / "role_map.py",
        "dps": REPO_DIRS["dps"] / "src" / "identity" / "role_map.py",
    }

    for name, path in consumer_files.items():
        if not path.exists():
            report.add(f"anchors.{name}", "WARN", f"未找到映射文件（跳过）：{path.name}")
            continue
        pairs = _extract_role_tier_pairs(path.read_text(encoding="utf-8", errors="replace"))
        conflicts = {r: (t, anchors.get(r)) for r, t in pairs.items() if r in anchors and anchors[r] != t}
        if conflicts:
            report.add(f"anchors.{name}", "FAIL", f"档位与锚点表矛盾：{conflicts}")
        elif pairs:
            # 覆盖门禁（2026-10-09 补）：不仅「不矛盾」，还须**覆盖全部锚点角色**——
            # 漏收合法码会让其在本仓 fail-closed 403 ROLE_UNMAPPED（误拒），
            # 例：A3 并集含 `user`，RAG/OM 曾仅收四码 → 本项应 FAIL。
            missing = sorted(set(anchors) - set(pairs))
            matched = sorted(set(pairs) & set(anchors))
            if missing:
                report.add(
                    f"anchors.{name}", "FAIL",
                    f"{path.name} 未覆盖锚点角色 {missing}（该码将被本仓 fail-closed 误拒 ROLE_UNMAPPED）",
                )
            else:
                report.add(
                    f"anchors.{name}", "PASS",
                    f"{path.name} 解析 {len(pairs)} 组映射，锚点角色**全覆盖** {matched}，无矛盾",
                )
        else:
            report.add(
                f"anchors.{name}", "WARN",
                f"{path.name} 未解析出「角色→档位」字面映射（需人工核对或改用该仓自有用例）",
            )


# ---------------------------------------------------------------------------
# 3) 错误码映射一致性
# ---------------------------------------------------------------------------


def check_error_codes(report: Report) -> None:
    doc = _load(ERROR_MAP_PATH)
    source_cache: dict[str, str] = {}

    # 仅检索各仓**源码根**（避免全仓遍历；错误码字面量只可能出现在源文件）
    source_roots = {
        "openbase": [REPO_ROOT / "openbase", REPO_ROOT / "scripts"],
        "openllm": [REPO_DIRS["openllm"] / "backend" / "app", REPO_DIRS["openllm"] / "backend" / "main.py"],
        "openrag": [REPO_DIRS["openrag"] / "src"],
        "openmemory": [REPO_DIRS["openmemory"] / "src"],
        "dps": [REPO_DIRS["dps"] / "src"],
    }
    max_bytes = 512 * 1024

    def repo_text(name: str) -> str:
        if name not in source_cache:
            parts: list[str] = []
            for root in source_roots.get(name, []):
                if not root.exists():
                    continue
                targets = [root] if root.is_file() else [
                    p for p in root.rglob("*")
                    if p.is_file() and p.suffix in {".py", ".ps1"} and "__pycache__" not in p.parts
                ]
                for path in targets:
                    try:
                        if path.stat().st_size > max_bytes:
                            continue
                        parts.append(path.read_text(encoding="utf-8", errors="replace"))
                    except OSError:
                        continue
            source_cache[name] = "\n".join(parts)
        return source_cache[name]

    missing: list[str] = []
    checked = 0
    for entry in doc.get("map") or []:
        for target, literal in (entry.get("targets") or {}).items():
            if not literal:
                continue
            literal = literal.split("(")[0].split("/")[0].strip()
            if not literal:
                continue
            checked += 1
            if literal not in repo_text(target):
                missing.append(f"{entry['unified']}→{target}:{literal}")

    report.add(
        "error_codes.consistency",
        "FAIL" if missing else "PASS",
        f"检索 {checked} 条目标字面量，未命中 {len(missing)} 条：{missing[:6]}" if missing else f"{checked} 条目标字面量全部在该仓源码中命中",
    )


# ---------------------------------------------------------------------------
# 4) 码空间登记一致性（C1-a 阻塞项的固化防线）
# ---------------------------------------------------------------------------


def check_code_space(report: Report) -> None:
    sys.path.insert(0, str(REPO_ROOT))
    from openbase.settings import resolve_target_code_space  # noqa: PLC0415

    resolved = resolve_target_code_space("")
    problems: list[str] = []

    for target, entry in resolved.items():
        code = entry.get("default_tenant_code")
        if code is None:
            continue
        if code in (entry.get("reserved_codes") or frozenset()):
            problems.append(f"{target} 兜底码 {code!r} 命中自身保留码")

    # 4.1 目标登记核对：OpenMemory 组织策略（编排器声明）
    orch = ORCHESTRATOR.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"OPENMEMORY_RBAC__ORG_POLICIES\s*=\s*'([^']+)'", orch)
    memory_default = (resolved.get("memory") or {}).get("default_tenant_code")
    if not match:
        problems.append("编排器未声明 OPENMEMORY_RBAC__ORG_POLICIES（memory 目标登记缺失）")
    else:
        registered = set(json.loads(match.group(1)).keys())
        if memory_default and memory_default not in registered:
            problems.append(f"memory 兜底码 {memory_default!r} 未在 OpenMemory 已登记组织 {sorted(registered)} 中")

    # 4.2 目标登记核对：OpenRAG 租户注册表默认清单
    rag_settings = REPO_DIRS["openrag"] / "src" / "openrag" / "config" / "settings.py"
    rag_default = (resolved.get("rag") or {}).get("default_tenant_code")
    if rag_settings.exists():
        text = rag_settings.read_text(encoding="utf-8", errors="replace")
        found = re.search(r"tenant_registry_codes[^\n]*=\s*\[([^\]]*)\]", text)
        declared = {c.strip().strip('"\'') for c in (found.group(1).split(",") if found else []) if c.strip()}
        if declared and rag_default and rag_default not in declared:
            problems.append(f"rag 兜底码 {rag_default!r} 未在 OpenRAG 租户注册表 {sorted(declared)} 中")
        elif not declared:
            report.add("code_space.rag_registry", "WARN", "未能从 OpenRAG settings 解析注册表默认清单，需人工核对")

    report.add(
        "code_space.registration",
        "FAIL" if problems else "PASS",
        "; ".join(problems)
        if problems
        else f"各目标兜底码均非自身保留码，且 memory/rag 已由目标侧登记（memory={memory_default!r}）",
    )


# ---------------------------------------------------------------------------
# 5) 保留码防护未放宽
# ---------------------------------------------------------------------------


def check_reserved_not_relaxed(report: Report) -> None:
    """各仓仍显式声明保留码集合（防「静默放宽防护」）."""
    expectations = {
        "openbase": ("outbound_reserved_tenant_codes_by_target", REPO_ROOT / "openbase" / "settings.py"),
        "openrag": ("reserved_tenant_codes", REPO_DIRS["openrag"] / "src" / "openrag" / "identity" / "tenancy.py"),
        "dps": ("dps_reserved_tenant_codes", REPO_DIRS["dps"] / "src" / "identity" / "constants.py"),
    }
    missing = []
    for name, (token, path) in expectations.items():
        if not path.exists():
            missing.append(f"{name}: 文件缺失 {path.name}")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if token not in text.lower():
            missing.append(f"{name}: 未找到保留码声明 {token}")
    report.add(
        "reserved.not_relaxed",
        "FAIL" if missing else "PASS",
        "; ".join(missing) if missing else "OpenBase/OpenRAG/DPS 仍显式声明保留码集合",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="跨系统授权一致性门禁（D2）")
    parser.add_argument("--json", dest="json_out", default="", help="证据落盘路径")
    args = parser.parse_args()

    report = Report()
    check_matrix(report)
    check_tier_anchors(report)
    check_error_codes(report)
    check_code_space(report)
    check_reserved_not_relaxed(report)

    width = max(len(r.check) for r in report.results)
    print("=" * 112)
    print("跨系统授权一致性门禁（D 批 D2）")
    print("=" * 112)
    for item in report.results:
        print(f"[{item.status:<4}] {item.check:<{width}}  {item.detail[:150]}")
    print("-" * 112)
    print(
        f"汇总：{len(report.results)} 项检查，PASS {len(report.results) - len(report.failed) - len(report.warned)}，"
        f"WARN {len(report.warned)}，FAIL {len(report.failed)}"
    )

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(
                {"schema_version": 1, "title": "跨系统授权一致性门禁（D2）", "results": [r.as_dict() for r in report.results]},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"证据已落盘：{args.json_out}")

    return 1 if report.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
