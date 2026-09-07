"""protocol_headers：统一身份协议头共享库（P2-1 K02，纯库不注册模块）.

OpenBase 主仓内全 proxy（dps/llm/rag/memory/通用）出站身份头的**唯一装配事实源**
（R-H1-1 唯一注入点），也是《协议头规范 v1.0》（doc/design/OpenBase-协议头规范-v1.0.md）
在 OpenBase 侧的常量/校验参考实现，供 S2/S3/S5 各子系统仓按「文档 + 常量/校验函数」
移植基线落地 K02。

约束（遵循 AGENTS.md）：
- 本包为**纯库**：不注册 enable_module、不挂 router/extra_routers，不引入 FastAPI 路由。
- 出站头装配只允许经 :func:`protocol_headers.inject.build_outbound_headers`；
  `X-Proxy-Source` 取值只允许经 :data:`protocol_headers.constants`（单一事实源，静态
  扫描 0 处第二写法）。
- 包内不依赖 modules.* 业务模块（避免循环导入）；`role_map` 仅承载配置读写与校验骨架，
  完整互译逻辑（OB-12）随 P2-1 批次 2/T6 落地。
"""
from __future__ import annotations

from openbase.modules.protocol_headers.constants import (
    HEADER_AGENT_ID,
    HEADER_API_KEY,
    HEADER_ON_BEHALF_OF,
    HEADER_ORG_ID,
    HEADER_PROXY_SOURCE,
    HEADER_REQUEST_ID,
    HEADER_TEAM_ID,
    HEADER_TENANT_ID,
    HEADER_USER_ID,
    HEADER_USER_ROLE,
    IDENTITY_HEADER_LENGTH_LIMITS,
    INBOUND_IDENTITY_HEADERS,
    PROXY_SOURCE_DPS,
    PROXY_SOURCE_GENERIC,
    PROXY_SOURCE_LLM,
    PROXY_SOURCE_MEMORY,
    PROXY_SOURCE_ORCHESTRATOR,
    PROXY_SOURCE_RAG,
    SOURCE_BY_TARGET_SYSTEM,
    TARGET_SYSTEM_DPS,
    TARGET_SYSTEM_GENERIC,
    TARGET_SYSTEM_LLM,
    TARGET_SYSTEM_MEMORY,
    TARGET_SYSTEM_RAG,
    TRUSTED_PROXY_SOURCES_KEY,
)
from openbase.modules.protocol_headers.identity_context import (
    IdentityCtx,
    resolve_identity,
)
from openbase.modules.protocol_headers.inject import build_outbound_headers
from openbase.modules.protocol_headers.role_map import (
    default_role_intertranslate,
    load_role_map,
    translate_role_code,
    validate_role_map,
    validate_role_map_structure,
)
from openbase.modules.protocol_headers.validate import (
    InboundClassification,
    assert_trusted_source,
    classify_inbound,
    inbound_identity_headers_present,
    strip_untrusted_identity_headers,
    trusted_source_of,
    validate_header_value,
    validate_identity_headers,
)

__version__ = "0.1.0"

__all__ = [
    "HEADER_AGENT_ID",
    "HEADER_API_KEY",
    "HEADER_ON_BEHALF_OF",
    "HEADER_ORG_ID",
    "HEADER_PROXY_SOURCE",
    "HEADER_REQUEST_ID",
    "HEADER_TEAM_ID",
    "HEADER_TENANT_ID",
    "HEADER_USER_ID",
    "HEADER_USER_ROLE",
    "IDENTITY_HEADER_LENGTH_LIMITS",
    "INBOUND_IDENTITY_HEADERS",
    "PROXY_SOURCE_DPS",
    "PROXY_SOURCE_GENERIC",
    "PROXY_SOURCE_LLM",
    "PROXY_SOURCE_MEMORY",
    "PROXY_SOURCE_ORCHESTRATOR",
    "PROXY_SOURCE_RAG",
    "SOURCE_BY_TARGET_SYSTEM",
    "TARGET_SYSTEM_DPS",
    "TARGET_SYSTEM_GENERIC",
    "TARGET_SYSTEM_LLM",
    "TARGET_SYSTEM_MEMORY",
    "TARGET_SYSTEM_RAG",
    "TRUSTED_PROXY_SOURCES_KEY",
    "IdentityCtx",
    "InboundClassification",
    "assert_trusted_source",
    "build_outbound_headers",
    "classify_inbound",
    "default_role_intertranslate",
    "inbound_identity_headers_present",
    "load_role_map",
    "resolve_identity",
    "strip_untrusted_identity_headers",
    "translate_role_code",
    "trusted_source_of",
    "validate_header_value",
    "validate_identity_headers",
    "validate_role_map",
    "validate_role_map_structure",
]
