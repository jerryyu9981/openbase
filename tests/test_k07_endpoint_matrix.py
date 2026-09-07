"""P2-1 T4 RED 断言：K07 端点-过滤矩阵模板 v1.0（§4/§10 T4）.

对齐草案 §10 T4：
- T4-1  模板主表列齐全（§4.1 十列 + 端点类别枚举）
- T4-2  核对脚本骨架：输入示例 openapi.json → 输出端点骨架行
        （端点/方法/类别三列自动填充）
- T4-3  填报说明文档存在且含 S2-S5 填报与 S7 终验规则
- T4-4  S2-S5 填报跟踪表登记完成（四系统行 + 责任段）
- T4-5  模板评审记录归档——S1b 门禁项
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = ROOT / "scripts" / "k07_endpoint_matrix.py"


def _load_script() -> Any:
    """以独立模块名加载 scripts/k07_endpoint_matrix.py（不污染 sys.modules）."""
    spec = importlib.util.spec_from_file_location("openbase_k07_matrix", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None, "k07 脚本缺失"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_SAMPLE_OPENAPI: dict[str, Any] = {
    "openapi": "3.0.0",
    "info": {"title": "sample", "version": "1.0.0"},
    "paths": {
        "/api/v1/collections": {"get": {}, "post": {}},
        "/api/v1/collections/{id}": {"get": {}, "put": {}, "delete": {}},
        "/api/v1/collections/{id}/list": {"get": {}},
        "/api/v1/search": {"post": {}},
        "/api/v1/export/report": {"get": {}},
        "/api/v1/batch/import": {"post": {}},
        "/api/v1/webhook/callback": {"post": {}},
        "/api/v1/reports/overview": {"get": {}},
        "/health": {"get": {}},
    },
}


# ---------------------------------------------------------------------------
# T4-1：模板主表列齐全（§4.1 十列 + 端点类别枚举）
# ---------------------------------------------------------------------------


def test_t4_1_template_columns_complete() -> None:
    """主表列 = §4.1 十列；端点类别枚举 = R-M2-1 八类."""
    module = _load_script()
    assert module.MATRIX_COLUMNS == [
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
    assert len(module.MATRIX_COLUMNS) == 10
    assert module.ENDPOINT_CATEGORIES == [
        "CRUD",
        "列表分页",
        "搜索",
        "统计聚合",
        "导出",
        "回调异步读",
        "批量",
        "健康管理",
    ]
    assert len(module.ENDPOINT_CATEGORIES) == 8
    # 身份头需求四列子字段（X-User-ID/X-Tenant-ID/X-User-Role/X-Proxy-Source）
    assert module.IDENTITY_HEADER_FIELDS == [
        "X-User-ID",
        "X-Tenant-ID",
        "X-User-Role",
        "X-Proxy-Source",
    ]
    assert module.STATUS_VALUES == ["覆盖", "缺口", "未覆盖", "豁免"]


# ---------------------------------------------------------------------------
# T4-2：核对脚本骨架（读 openapi.json → 输出端点骨架行）
# ---------------------------------------------------------------------------


def test_t4_2_openapi_to_skeleton_rows() -> None:
    """示例 openapi.json → 逐端点骨架行（端点/方法/类别自动填充）."""
    module = _load_script()
    rows = module.openapi_to_skeleton_rows(_SAMPLE_OPENAPI, system="OpenRAG")
    # 每 path × 方法 = 12 行（health 1 + collections 2 + {id} 3 + list 1 + search 1
    # + export 1 + batch 1 + webhook 1 + overview 1）
    assert len(rows) == 12, f"expected 12 skeleton rows, got {len(rows)}"
    by_key = {(row["端点"], row["方法"]): row for row in rows}

    health_row = by_key[("/health", "GET")]
    assert health_row["系统"] == "OpenRAG"
    assert health_row["端点类别"] == "健康管理"
    assert health_row["端点"] == "/health"
    assert health_row["方法"] == "GET"

    search_row = by_key[("/api/v1/search", "POST")]
    assert search_row["端点类别"] == "搜索"
    assert by_key[("/api/v1/batch/import", "POST")]["端点类别"] == "批量"
    assert by_key[("/api/v1/export/report", "GET")]["端点类别"] == "导出"
    assert by_key[("/api/v1/webhook/callback", "POST")]["端点类别"] == "回调异步读"
    assert by_key[("/api/v1/reports/overview", "GET")]["端点类别"] == "统计聚合"
    assert by_key[("/api/v1/collections/{id}/list", "GET")]["端点类别"] == "列表分页"

    # 骨架行覆盖十列键 + 子字段结构（身份头/归属过滤/豁免审批为结构化子字段）
    for row in rows:
        for column in module.MATRIX_COLUMNS:
            assert column in row, f"row missing column {column}"
        identity_need = row["身份头需求"]
        assert isinstance(identity_need, dict)
        for header_field in module.IDENTITY_HEADER_FIELDS:
            assert header_field in identity_need
        ownership = row["归属过滤需求"]
        assert "域过滤(tenant_code,恒有)" in ownership
        assert "属主过滤(owner)" in ownership
        assert "白名单来源豁免" in ownership
        exemption = row["豁免审批"]
        assert "豁免?（是/否）" in exemption
        assert row["状态"] == "未覆盖"  # 骨架默认未覆盖（待 S2-S5 填报）


def test_t4_2_render_markdown_table() -> None:
    """骨架行可渲染为主表 markdown（十列表头 + 行对齐）."""
    module = _load_script()
    rows = module.openapi_to_skeleton_rows(_SAMPLE_OPENAPI, system="OpenRAG")
    table = module.render_markdown(rows)
    header_line = table.splitlines()[0]
    for column in module.MATRIX_COLUMNS:
        assert column in header_line
    assert len(table.splitlines()) >= len(rows) + 1


def test_t4_2_cli_entrypoint() -> None:
    """CLI 形态：--help 可用（核对脚本骨架可执行）."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "openapi" in (result.stdout + result.stderr).lower()


# ---------------------------------------------------------------------------
# T4-3：填报说明文档存在且含 S2-S5 填报与 S7 终验规则
# ---------------------------------------------------------------------------


def test_t4_3_fill_guide_doc_present() -> None:
    """模板文档存在且含填报说明（S2-S5 填报流程 + S7 终验规则）."""
    doc_path = ROOT / "doc" / "design" / "OpenBase-端点过滤矩阵模板-v1.0.md"
    assert doc_path.exists(), f"模板文档缺失: {doc_path}"
    content = doc_path.read_text(encoding="utf-8")
    for marker in (
        "填报说明",
        "S2",
        "S3",
        "S5",
        "S4",
        "S7",
        "终验",
        "缺口清零",
        "未覆盖清零",
        "豁免",
        "隔离测试",
        "隔离测试注册位",
    ):
        assert marker in content, f"模板文档缺少 {marker}"


# ---------------------------------------------------------------------------
# T4-4：S2-S5 填报跟踪表登记（四系统行 + 责任段）
# ---------------------------------------------------------------------------


def test_t4_4_tracking_table_registered() -> None:
    """填报跟踪表登记：OpenMemory/OpenRAG/OpenLLM/DPS 四行 + 责任段."""
    doc_path = ROOT / "doc" / "design" / "OpenBase-端点过滤矩阵模板-v1.0.md"
    content = doc_path.read_text(encoding="utf-8")
    for marker in ("OpenMemory", "OpenRAG", "OpenLLM", "DPS", "S2", "S3", "S4", "S5"):
        assert marker in content, f"跟踪表缺少 {marker}"


# ---------------------------------------------------------------------------
# T4-5：模板评审记录归档（S1b 门禁项）
# ---------------------------------------------------------------------------


def test_t4_5_review_record_archived() -> None:
    """模板评审记录归档（评审人/结论/遗留；S1b 门禁项）."""
    doc_path = ROOT / "doc" / "design" / "OpenBase-端点过滤矩阵模板-v1.0.md"
    content = doc_path.read_text(encoding="utf-8")
    for marker in ("评审", "评审记录", "门禁", "版本", "修订历史"):
        assert marker in content, f"模板文档缺少 {marker}"


def test_t4_5_matrix_doc_versioned() -> None:
    """模板文档版本化（v1.0 + 修订历史 + 状态）."""
    doc_path = ROOT / "doc" / "design" / "OpenBase-端点过滤矩阵模板-v1.0.md"
    content = doc_path.read_text(encoding="utf-8")
    assert "v1.0" in content
    assert "状态" in content
    assert "修订历史" in content


def test_t4_matrix_doc_embeds_empty_main_table() -> None:
    """模板文档内嵌可复制主表（十列表头样例，S2-S5 直接复制填报）."""
    doc_path = ROOT / "doc" / "design" / "OpenBase-端点过滤矩阵模板-v1.0.md"
    content = doc_path.read_text(encoding="utf-8")
    table_header = content.splitlines()
    joined = "\n".join(table_header)
    assert "| 系统 " in joined or "|系统" in joined
    assert "隔离测试注册位" in joined
