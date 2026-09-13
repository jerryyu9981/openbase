"""协议头规范 v1.0 常量与约束（单一事实源，P2-1 §3.1/§3.3）.

全仓（含 proxy）只允许 import 本模块取值；**禁止模块内写死第二写法**。
`X-Proxy-Source` 来源标识常量与受信来源配置键在此唯一发布。
"""
from __future__ import annotations

# ---- 规范头名常量（§3.1）----
HEADER_USER_ID = "X-User-ID"
HEADER_TENANT_ID = "X-Tenant-ID"
HEADER_ORG_ID = "X-Org-ID"
HEADER_USER_ROLE = "X-User-Role"
HEADER_PROXY_SOURCE = "X-Proxy-Source"
HEADER_REQUEST_ID = "X-Request-Id"
HEADER_AGENT_ID = "X-Agent-Id"
HEADER_ON_BEHALF_OF = "X-On-Behalf-Of"
HEADER_TEAM_ID = "X-Team-Id"
HEADER_API_KEY = "X-API-Key"

# ---- 人工测试用例上下文头（C-3/C-5，方案 §3.3）----
# ⚠️ 非身份头：**禁止**加入 IDENTITY_HEADERS / INBOUND_IDENTITY_HEADERS 裁剪集，
#    也不得加入 INBOUND_IDENTITY_HEADERS 派生的受信判定位集合——否则测试者携带
#    这三个头会被信任链判定为「未受信身份头」并返回 403（方案 §3.3 关键取舍）。
#    它们只用于把「人判定」与「系统客观记录」按 case/step/run 维度关联起来。
HEADER_TEST_CASE_ID = "X-Test-Case-Id"
HEADER_TEST_STEP_ID = "X-Test-Step-Id"
HEADER_TEST_RUN_ID = "X-Test-Run-Id"

# 用例上下文头集（非身份头；仅供出站透传与审计引用，不参与任何信任链判定）
TEST_CONTEXT_HEADERS: frozenset[str] = frozenset(
    {
        HEADER_TEST_CASE_ID,
        HEADER_TEST_STEP_ID,
        HEADER_TEST_RUN_ID,
    }
)

# 四头 + 委托/执行者标注（R-H1-1 校验集）；X-Org-ID 为退役兼容别名（OB-8，值=tenant_code）
IDENTITY_HEADERS: frozenset[str] = frozenset(
    {
        HEADER_USER_ID,
        HEADER_TENANT_ID,
        HEADER_ORG_ID,
        HEADER_USER_ROLE,
    }
)

# 入站裁剪头集（§3.4/§5.4）：客户端直连携带即伪造嫌疑（X-Proxy-Source 本身为来源判定位）
INBOUND_IDENTITY_HEADERS: frozenset[str] = frozenset(
    {
        HEADER_USER_ID,
        HEADER_TENANT_ID,
        HEADER_ORG_ID,
        HEADER_USER_ROLE,
        HEADER_AGENT_ID,
        HEADER_ON_BEHALF_OF,
    }
)

# 头值长度上限（§3.1 类型/长度约束）
IDENTITY_HEADER_LENGTH_LIMITS: dict[str, int] = {
    HEADER_USER_ID: 128,
    HEADER_TENANT_ID: 64,
    HEADER_ORG_ID: 64,
    HEADER_USER_ROLE: 64,
    HEADER_PROXY_SOURCE: 64,
    HEADER_REQUEST_ID: 64,
    HEADER_AGENT_ID: 64,
    HEADER_ON_BEHALF_OF: 512,
    HEADER_TEAM_ID: 64,
}

# 规范值域（§3.1）：禁止空串/控制字符；简单字符集校验（头值不出现 CR/LF）
# 角色码为 OpenBase 现役粗粒度集（最小集 §6.3；互译目标码见 role_map）
ALLOWED_OPENBASE_ROLE_CODES: frozenset[str] = frozenset(
    {"admin", "org_admin", "org_member", "viewer"}
)

# 非法头值字符（防头注入：任何出现在头值中的 CR/LF 即非法）
_FORBIDDEN_VALUE_CHARS = frozenset({"\r", "\n", "\x00"})


def header_value_allows(value: str, header_name: str) -> bool:
    """校验单头值格式（长度上限 + 无 CR/LF/控制字符）.

    Args:
        value: 待校验头值。
        header_name: 头名（取 IDENTITY_HEADER_LENGTH_LIMITS 长度上限）。

    Returns:
        合法返回 True；超长/含控制字符返回 False。
    """
    if value is None:
        return False
    text = str(value)
    upper_limit = IDENTITY_HEADER_LENGTH_LIMITS.get(header_name)
    if upper_limit is not None and len(text) > upper_limit:
        return False
    if not text:
        return True if header_name not in IDENTITY_HEADERS else False
    return not (_FORBIDDEN_VALUE_CHARS & set(text))


# ---- 来源标识常量（§3.3，X-Proxy-Source 唯一发布面）----
PROXY_SOURCE_DPS = "openbase-dps-proxy"
PROXY_SOURCE_LLM = "openbase-llm-proxy"
PROXY_SOURCE_RAG = "openbase-rag-proxy"
PROXY_SOURCE_MEMORY = "openbase-memory-proxy"
PROXY_SOURCE_GENERIC = "openbase-generic-proxy"
PROXY_SOURCE_ORCHESTRATOR = "openbase-orchestrator"

# settings 受信来源配置键（§3.3：TRUSTED_PROXY_SOURCES 全仓仅一种取值点）
TRUSTED_PROXY_SOURCES_KEY = "trusted_proxy_sources"

# target_system（build_outbound_headers 首参）→ 出口来源常量映射
TARGET_SYSTEM_DPS = "dps"
TARGET_SYSTEM_LLM = "llm"
TARGET_SYSTEM_RAG = "rag"
TARGET_SYSTEM_MEMORY = "memory"
TARGET_SYSTEM_GENERIC = "generic"

SOURCE_BY_TARGET_SYSTEM: dict[str, str] = {
    TARGET_SYSTEM_DPS: PROXY_SOURCE_DPS,
    TARGET_SYSTEM_LLM: PROXY_SOURCE_LLM,
    TARGET_SYSTEM_RAG: PROXY_SOURCE_RAG,
    TARGET_SYSTEM_MEMORY: PROXY_SOURCE_MEMORY,
    TARGET_SYSTEM_GENERIC: PROXY_SOURCE_GENERIC,
}

# 可注入出站身份头的目标系统集（§3.5 矩阵全集）
OUTBOUND_IDENTITY_TARGETS: frozenset[str] = frozenset(
    {
        TARGET_SYSTEM_DPS,
        TARGET_SYSTEM_LLM,
        TARGET_SYSTEM_RAG,
        TARGET_SYSTEM_MEMORY,
        TARGET_SYSTEM_GENERIC,
    }
)
