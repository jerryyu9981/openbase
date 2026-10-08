"""BL-147 跨仓信任链/结构化环境接线测试（TDD：先 RED，后实现）.

背景（BL-147-05 验收发现，见《OpenBase-测试报告-v1.4.7》§2.1）：

- 网关对下游注入 `X-Proxy-Source: openbase-{dps|rag|memory|llm}-proxy` 与同一 `X-Request-Id`；
- 四仓仅对**受信来源白名单**内的入站 `X-Request-Id` 透传复用，白名单为空则忽略并本地重生成
  → 实测 DPS 0/6、OpenRAG 0/6 命中（OpenLLM 6/6 命中，说明网关注入本身正确）；
- 编排器（C-6）负责把环境变量注入各服务子进程，故**联调环境的信任链与结构化开关在此单点声明**。

判据来源：
- 网关来源常量：`openbase/modules/protocol_headers/constants.py::PROXY_SOURCE_*`（单一事实源）；
- 各仓读取键：DPS `TRUSTED_PROXY_SOURCES`（`src/config.py`）、
  OpenRAG `OPENRAG_IDENTITY_TRUSTED_PROXY_SOURCES` 与 `OPENRAG_LOG_JSON`
  （`src/openrag/config/settings.py`）。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from openbase.modules.protocol_headers.constants import (
    PROXY_SOURCE_DPS,
    PROXY_SOURCE_MEMORY,
    PROXY_SOURCE_RAG,
)
from openbase.settings import RAG_RESERVED_TENANT_CODES

ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = ROOT / "scripts" / "service-orchestrator.ps1"


def _service_block(name: str) -> str:
    """截取服务定义块（`Name = '<name>'` 起到下一个服务定义前）."""
    text = ORCHESTRATOR.read_text(encoding="utf-8-sig")
    match = re.search(r"Name\s+=\s+'" + re.escape(name) + r"'", text)
    assert match, f"编排器未定义服务 {name}"
    tail = text[match.end():]
    following = re.search(r"Name\s+=\s+'", tail)
    return tail[: following.start()] if following else tail


def test_dps_declares_trusted_proxy_source() -> None:
    """DPS 采集/联调环境须声明受信代理来源（否则忽略网关 X-Request-Id 并本地重生成）."""
    block = _service_block("dps")

    assert "TRUSTED_PROXY_SOURCES" in block, "dps 未注入 TRUSTED_PROXY_SOURCES"
    assert PROXY_SOURCE_DPS in block, f"dps 白名单缺少网关来源 {PROXY_SOURCE_DPS}"


def test_openrag_declares_trusted_proxy_source() -> None:
    """OpenRAG 须声明受信代理来源，使其 X-Request-Id 透传复用分支生效."""
    block = _service_block("openrag")

    assert "OPENRAG_IDENTITY_TRUSTED_PROXY_SOURCES" in block, (
        "openrag 未注入 OPENRAG_IDENTITY_TRUSTED_PROXY_SOURCES"
    )
    assert PROXY_SOURCE_RAG in block, f"openrag 白名单缺少网关来源 {PROXY_SOURCE_RAG}"


def test_openrag_enables_json_lines() -> None:
    """OpenRAG 采集环境须开启 JSONL（否则请求日志为 structlog 控制台文本，应用日志行为 0）."""
    block = _service_block("openrag")

    assert re.search(r"OPENRAG_LOG_JSON\s*=\s*'true'", block), (
        "openrag 未开启 OPENRAG_LOG_JSON（JSONL 结构化契约不满足）"
    )


def test_openmemory_declares_trusted_proxy_source() -> None:
    """OpenMemory 须声明受信代理来源.

    `/health` 在 `IdentityTrustConfig.whitelist_paths` 内 → 身份门直接放行、不裁决 request_id，
    故 StructuredLogMiddleware 回退复用合规入站头（表现为「探活路径能命中」）；
    业务路径（如 `/api/v1/monitor`）会走门裁决，白名单为空 → `allow_reuse=False`
    → 忽略网关 `X-Request-Id` 并本地重生成（表现为「业务路径 0 命中」）。
    """
    block = _service_block("openmemory")

    assert "OPENMEMORY_IDENTITY_TRUSTED_PROXY_SOURCES" in block, (
        "openmemory 未注入 OPENMEMORY_IDENTITY_TRUSTED_PROXY_SOURCES"
    )
    assert PROXY_SOURCE_MEMORY in block, f"openmemory 白名单缺少网关来源 {PROXY_SOURCE_MEMORY}"


def test_openbase_declares_rag_tenant_alignment_policy() -> None:
    """OpenBase（网关）须**显式声明** rag-proxy 出站租户码对齐口径（R-387 收口）。

    演进：DEF-BE-147-005（v1.4.7）曾以「不注入身份头」（
    `OPENBASE_RAG_INJECT_IDENTITY_HEADERS='false'`）规避 OpenRAG 保留租户码的 400，
    但其连带后果为**全部写类端点恒 403**（`PERM_SERVICE_KEY_WRITE_DENIED`，
    见 DEF-BE-1410-001）。出站头矩阵实测（`doc/test/evidence/manual/`）证明根因是
    **租户码落在 OpenRAG 保留码（`default`/`openrag-local`）上或缺省**，而非「注入」本身；
    受信入站 + 非保留码（如 `tenant-1`）时读、写**同时 200**。

    R-387 收口＝恢复身份头注入 + 出站租户码恒对齐为非保留码。本用例为护栏：
    ① 编排器**不得**再声明注入关闭；② 须显式声明非保留兜底租户码。
    口径再次变更时必须同步修改编排器与本说明（不得静默漂移）。
    """
    block = _service_block("openbase")

    # 判据锚定「环境变量**赋值行**」：注释中提及该键名（如说明为何不再声明）不算违规。
    assert not re.search(
        r"^[ \t]*OPENBASE_RAG_INJECT_IDENTITY_HEADERS\s*=\s*'false'", block, re.MULTILINE
    ), (
        "openbase 仍声明 OPENBASE_RAG_INJECT_IDENTITY_HEADERS='false'"
        "（DEF-BE-1410-001 已证明该口径使全部写类端点 403）"
    )

    match = re.search(
        r"^[ \t]*OPENBASE_PROXY_CODE_MAP\s*=\s*'([^']+)'", block, re.MULTILINE
    )
    assert match, (
        "openbase 未显式声明 OPENBASE_PROXY_CODE_MAP"
        "（A 批 A1/A2：出站租户码空间统一登记入口）"
    )
    code_map = json.loads(match.group(1))
    targets = code_map.get("targets") or {}
    assert targets, "OPENBASE_PROXY_CODE_MAP 未声明任何目标码空间"
    for target, entry in targets.items():
        code = entry.get("default_tenant_code")
        if code is None:
            continue
        assert code, f"目标 {target} 的 default_tenant_code 不得为空"
        assert code not in RAG_RESERVED_TENANT_CODES or target != "rag", (
            f"目标 rag 的 default_tenant_code {code!r} 命中 OpenRAG 保留码"
            f"{sorted(RAG_RESERVED_TENANT_CODES)}，受信入站将返回 400"
        )
