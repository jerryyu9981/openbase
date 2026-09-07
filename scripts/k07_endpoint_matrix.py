"""K07 端点-过滤矩阵核对脚本骨架（P2-1 §4/§10 T4，S1b 发布物）.

读子系统导出的 openapi.json → 生成端点骨架行（端点/方法/端点类别自动填充），
填报人只填「身份头需求/归属过滤/豁免」三块；模板主表十列对齐《OpenBase-端点
过滤矩阵模板-v1.0》（doc/design/OpenBase-端点过滤矩阵模板-v1.0.md）。

主表列（§4.1）：
    系统 / 端点 / 方法 / 端点类别 / 身份头需求 / 归属过滤需求 / 租户键 /
    豁免审批 / 状态 / 隔离测试注册位

用法::

    python scripts/k07_endpoint_matrix.py <openapi.json> [--system OpenRAG] [--out matrix.md]

填报纪律（§4.2）：逐端点登记；归属过滤描述必须指向代码事实（中间件/DAO/SQL）；
豁免行必须挂 ticket+审批人+复核日期；403/越权缺陷回填对应端点行（缺口证据）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# ---- §4.1 主表列（十列，顺序固定，xlsx/md 共用）----
MATRIX_COLUMNS: list[str] = [
    "系统",
    "端点",
    "方法",
    "端点类别",
    "身份头需求",
    "归属过滤需求",
    "租户键",
    "豁免审批",
    "状态",
    "隔离测试注册位",
]

# 身份头需求四列子字段（每端点声明执行域/属主/角色过滤所依赖的身份头）
IDENTITY_HEADER_FIELDS: list[str] = [
    "X-User-ID",
    "X-Tenant-ID",
    "X-User-Role",
    "X-Proxy-Source",
]

# 归属过滤需求三态子字段（域过滤恒有；属主过滤按数据语义；白名单豁免须审批）
OWNERSHIP_FILTER_FIELDS: list[str] = [
    "域过滤(tenant_code,恒有)",
    "属主过滤(owner)",
    "白名单来源豁免",
]

# 豁免审批登记位（任何跳过过滤的端点必须显式豁免审批 + 审计留痕，R-H3-3）
EXEMPTION_FIELDS: list[str] = [
    "豁免?（是/否）",
    "豁免 ticket",
    "审批人",
    "到期/复核",
]

# 端点类别（R-M2-1 八类；健康/管理面单独标注「A 直连」）
ENDPOINT_CATEGORIES: list[str] = [
    "CRUD",
    "列表分页",
    "搜索",
    "统计聚合",
    "导出",
    "回调异步读",
    "批量",
    "健康管理",
]

# 状态（S7 终验以「缺口清零、未覆盖清零」为目标）
STATUS_VALUES: list[str] = ["覆盖", "缺口", "未覆盖", "豁免"]

# 合法子系统（填报列）
ALLOWED_SYSTEMS: frozenset[str] = frozenset(
    {"OpenMemory", "OpenRAG", "OpenLLM", "DPS"}
)

_HTTP_METHODS: tuple[str, ...] = ("GET", "POST", "PUT", "PATCH", "DELETE")

_CATEGORY_KEYWORDS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("health", "liveness", "readiness", "ping"), "健康管理"),
    (("search", "query"), "搜索"),
    (("export", "download"), "导出"),
    (("batch",), "批量"),
    (("webhook", "callback"), "回调异步读"),
    (("statistics", "stats", "summary", "aggregate", "overview", "report", "trend"), "统计聚合"),
)


def classify_endpoint(path: str, method: str) -> str:
    """按路径关键词/方法推断端点类别（骨架默认；人工可改，须 ∈ ENDPOINT_CATEGORIES）.

    规则：健康管理 > 搜索 > 导出 > 批量 > 回调异步读 > 统计聚合 > 列表分页 > CRUD。
    """
    lowered = path.lower()
    for keywords, category in _CATEGORY_KEYWORDS:
        if any(keyword in lowered for keyword in keywords):
            return category
    if method == "GET" and any(marker in lowered for marker in ("/list", "page", "list")):
        return "列表分页"
    return "CRUD"


def _identity_need_skeleton() -> dict[str, str]:
    """身份头需求骨架默认：四头待填报（'必需/可选/忽略' 三值，默认可选）."""
    return {header_field: "可选" for header_field in IDENTITY_HEADER_FIELDS}


def _ownership_skeleton() -> dict[str, str]:
    return {field: "" for field in OWNERSHIP_FILTER_FIELDS}


def _exemption_skeleton() -> dict[str, str]:
    return {
        "豁免?（是/否）": "否",
        "豁免 ticket": "",
        "审批人": "",
        "到期/复核": "",
    }


def _skeleton_row(system: str, endpoint: str, method: str) -> dict[str, Any]:
    """构造单条骨架行（端点/方法/类别自动；人工填报位给结构化默认）. """
    return {
        "系统": system,
        "端点": endpoint,
        "方法": method,
        "端点类别": classify_endpoint(endpoint, method),
        "身份头需求": _identity_need_skeleton(),
        "归属过滤需求": _ownership_skeleton(),
        "租户键": "X-Tenant-ID",
        "豁免审批": _exemption_skeleton(),
        "状态": "未覆盖",
        "隔离测试注册位": "",
    }


def openapi_to_skeleton_rows(openapi_spec: dict[str, Any], system: str) -> list[dict[str, Any]]:
    """读子系统 openapi.json → 逐端点骨架行（端点/方法/类别三列自动填充）.

    Args:
        openapi_spec: openapi.json dict（含 paths.<path>.<method>）。
        system: 填报子系统（OpenMemory/OpenRAG/OpenLLM/DPS）。

    Returns:
        主表骨架行列表（每行覆盖 MATRIX_COLUMNS 十列；身份头/归属/豁免为子字段 dict）。
    """
    if system not in ALLOWED_SYSTEMS:
        raise ValueError(
            f"unknown system {system!r}; allowed: {sorted(ALLOWED_SYSTEMS)}"
        )
    paths = openapi_spec.get("paths") or {}
    rows: list[dict[str, Any]] = []
    for endpoint, operations in paths.items():
        if not isinstance(operations, dict):
            continue
        for method in _HTTP_METHODS:
            if method.lower() in operations:
                rows.append(_skeleton_row(system, str(endpoint), method))
    rows.sort(key=lambda row: (row["端点"], row["方法"]))
    return rows


def _cell_text(value: Any) -> str:
    """单元格文本（子字段 dict → 'k=v' 逗号连接，便于 md 直读）. """
    if isinstance(value, dict):
        parts: list[str] = []
        for key, item in value.items():
            parts.append(f"{key}={item}" if item not in ("", None) else key)
        return "<br>".join(parts) if parts else ""
    return str(value)


def render_markdown(rows: list[dict[str, Any]]) -> str:
    """将骨架行渲染为主表 markdown（十列表头 + 分隔行 + 数据行）."""
    lines: list[str] = []
    header = "| " + " | ".join(MATRIX_COLUMNS) + " |"
    separator = "| " + " | ".join(["---"] * len(MATRIX_COLUMNS)) + " |"
    lines.append(header)
    lines.append(separator)
    for row in rows:
        cells = " | ".join(_cell_text(row[column]) for column in MATRIX_COLUMNS)
        lines.append(f"| {cells} |")
    return "\n".join(lines)


def _load_openapi(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        spec = json.load(handle)
    if not isinstance(spec, dict):
        raise ValueError("openapi.json must be a JSON object")
    return spec


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="K07 端点-过滤矩阵骨架生成（读 openapi.json → md 主表骨架行）"
    )
    parser.add_argument("openapi", help="子系统导出的 openapi.json 路径")
    parser.add_argument(
        "--system",
        default="OpenMemory",
        choices=sorted(ALLOWED_SYSTEMS),
        help="填报子系统（默认 OpenMemory）",
    )
    parser.add_argument("--out", default="", help="输出 md 路径（缺省打印 stdout）")
    args = parser.parse_args(argv)

    spec = _load_openapi(Path(args.openapi))
    rows = openapi_to_skeleton_rows(spec, args.system)
    table = render_markdown(rows)
    if args.out:
        Path(args.out).write_text(table + "\n", encoding="utf-8")
        print(f"[ok] {len(rows)} 骨架行 → {args.out}")
    else:
        print(table)
    return 0


if __name__ == "__main__":
    sys.exit(main())
