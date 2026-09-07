"""P2-1 批次1 T1/T3 RED 断言：protocol_headers 共享库单测.

对齐《OpenBase-P2-1-统一身份协议头与信任链收口设计草案》v1.0.0 §10：
- T1-6  静态扫描 0 处第二写法（PROXY_SOURCE_*/TRUSTED_PROXY_SOURCES 唯一发布源）
- T3-2  validate_identity_headers 非法格式 → 400 PARAM_HEADER_FORMAT_INVALID
- T3-3  assert_trusted_source 白名单判定
- T3-4  classify_inbound 行为矩阵 M1 四态
- 补充：constants 值 = 规范表 §3.1/§3.3；identity_context 委托覆盖；
  inject.build_outbound_headers 唯一装配点语义（T1-1/2/9 载体）。
"""
from __future__ import annotations

import types
from pathlib import Path

import pytest

from openbase.core.errors import BaseError, ErrorCode
from openbase.modules.protocol_headers import (
    HEADER_AGENT_ID,
    HEADER_ORG_ID,
    HEADER_PROXY_SOURCE,
    HEADER_REQUEST_ID,
    HEADER_TENANT_ID,
    HEADER_USER_ID,
    HEADER_USER_ROLE,
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
    InboundClassification,
    assert_trusted_source,
    build_outbound_headers,
    classify_inbound,
    inbound_identity_headers_present,
    load_role_map,
    resolve_identity,
    strip_untrusted_identity_headers,
    translate_role_code,
    validate_header_value,
    validate_identity_headers,
)
from openbase.modules.protocol_headers.constants import (
    ALLOWED_OPENBASE_ROLE_CODES,
    IDENTITY_HEADER_LENGTH_LIMITS,
)


def _request(headers: dict[str, str]) -> types.SimpleNamespace:
    """构造只读请求桩（headers + state.request_id）."""
    return types.SimpleNamespace(
        headers=headers,
        state=types.SimpleNamespace(request_id="req-red-0001"),
    )


# ---------------------------------------------------------------------------
# T1-6：来源标识单一事实源（§3.3）
# ---------------------------------------------------------------------------


def test_t1_6_source_constants_match_spec() -> None:
    """常量值与草案 §3.3 表一致."""
    assert PROXY_SOURCE_DPS == "openbase-dps-proxy"
    assert PROXY_SOURCE_LLM == "openbase-llm-proxy"
    assert PROXY_SOURCE_RAG == "openbase-rag-proxy"
    assert PROXY_SOURCE_MEMORY == "openbase-memory-proxy"
    assert PROXY_SOURCE_GENERIC == "openbase-generic-proxy"
    assert PROXY_SOURCE_ORCHESTRATOR == "openbase-orchestrator"
    assert SOURCE_BY_TARGET_SYSTEM == {
        TARGET_SYSTEM_DPS: PROXY_SOURCE_DPS,
        TARGET_SYSTEM_LLM: PROXY_SOURCE_LLM,
        TARGET_SYSTEM_RAG: PROXY_SOURCE_RAG,
        TARGET_SYSTEM_MEMORY: PROXY_SOURCE_MEMORY,
        TARGET_SYSTEM_GENERIC: PROXY_SOURCE_GENERIC,
    }
    assert TRUSTED_PROXY_SOURCES_KEY == "trusted_proxy_sources"


def test_t1_6_source_single_definition_scan() -> None:
    """全仓 openbase/ 内 PROXY_SOURCE_* / 来源标识字面量仅定义于 constants.py."""
    constants_path = (
        Path(__file__).resolve().parent.parent / "openbase" / "modules" / "protocol_headers" / "constants.py"
    )
    source_values = {
        "openbase-dps-proxy",
        "openbase-llm-proxy",
        "openbase-rag-proxy",
        "openbase-memory-proxy",
        "openbase-generic-proxy",
        "openbase-orchestrator",
    }
    violations: list[str] = []
    for path in sorted((Path(__file__).resolve().parent.parent / "openbase").rglob("*.py")):
        if path == constants_path:
            continue
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith(("PROXY_SOURCE_", "TRUSTED_PROXY_SOURCES")) and "=" in stripped:
                # 允许 `from ... import X` 类引用（无 = 定义；此处按定义行排除注释）
                if not stripped.startswith(("#", "from", "import")):
                    violations.append(f"{path.relative_to(Path.cwd())}:{line_no}")
            # 排除注释/文档字符串后的赋值形态字面量
            for value in source_values:
                if f'"{value}"' in stripped or f"'{value}'" in stripped:
                    if not stripped.startswith(("#", "from", "import")):
                        violations.append(f"{path.relative_to(Path.cwd())}:{line_no}")
    assert violations == [], f"PROXY_SOURCE_* 第二写法: {violations}"


def test_t3_1_spec_deliverables_present() -> None:
    """发布物齐备（T3-1）：规范文档 + protocol_headers 五模块 + 常量表一致."""
    root = Path(__file__).resolve().parent.parent
    spec_doc = root / "doc" / "design" / "OpenBase-协议头规范-v1.0.md"
    assert spec_doc.is_file(), "协议头规范 v1.0 文档缺失"
    package = root / "openbase" / "modules" / "protocol_headers"
    for module_name in (
        "__init__.py",
        "constants.py",
        "identity_context.py",
        "validate.py",
        "inject.py",
        "role_map.py",
    ):
        assert (package / module_name).is_file(), f"protocol_headers/{module_name} 缺失"


def test_t1_11_delegation_issuance_single_source_scan() -> None:
    """委托唯一签发：issue_delegated_token_pair/build_on_behalf_of_claim 仅 delegation.py 定义."""
    root = Path(__file__).resolve().parent.parent
    definition_count = 0
    for path in sorted((root / "openbase").rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for marker in ("def issue_delegated_token_pair", "def build_on_behalf_of_claim"):
            if marker in text:
                definition_count += 1
                assert path.name == "delegation.py", f"委托签发第二落点: {path}"
    assert definition_count == 2
    # 规范正文 §6 已文档化「唯一签发」
    spec_doc = root / "doc" / "design" / "OpenBase-协议头规范-v1.0.md"
    spec_text = spec_doc.read_text(encoding="utf-8")
    assert "唯一签发" in spec_text and "issue_delegated_token_pair" in spec_text


# ---------------------------------------------------------------------------
# T3-2/T3-3/T3-4：validate / classify
# ---------------------------------------------------------------------------


def test_t3_2_validate_header_value_legal() -> None:
    """合法头值通过校验并原样返回."""
    assert validate_header_value(HEADER_USER_ID, "123") == "123"
    assert validate_header_value(HEADER_TENANT_ID, "acme") == "acme"


def test_t3_2_validate_identity_headers_rejects_invalid() -> None:
    """非法格式（超长/非法字符/空值）→ 400 PARAM_HEADER_FORMAT_INVALID."""
    headers = {HEADER_USER_ID: "x" * 200}
    with pytest.raises(BaseError) as exc_info:
        validate_identity_headers(headers)
    assert exc_info.value.code == ErrorCode.PARAM_HEADER_FORMAT_INVALID
    assert exc_info.value.status_code == 400

    with pytest.raises(BaseError):
        validate_header_value(HEADER_USER_ROLE, "admin\r\nX-Evil: 1")


def test_t3_2_validate_identity_headers_legal_pass() -> None:
    """合法头集整体通过（返回头字典）."""
    result = validate_identity_headers(
        {
            HEADER_USER_ID: "42",
            HEADER_TENANT_ID: "acme",
            HEADER_USER_ROLE: "org_admin",
        }
    )
    assert result[HEADER_USER_ID] == "42"


def test_t3_3_assert_trusted_source() -> None:
    """白名单命中 True；非白名单/缺失 False."""
    trusted = [PROXY_SOURCE_RAG, PROXY_SOURCE_LLM]
    assert assert_trusted_source(PROXY_SOURCE_RAG, trusted) is True
    assert assert_trusted_source("spoofed", trusted) is False
    assert assert_trusted_source(None, trusted) is False


def test_t3_4_classify_inbound_matrix() -> None:
    """classify_inbound 行为矩阵 M1 四态（T3-4）."""
    trusted = [PROXY_SOURCE_ORCHESTRATOR]
    # 白名单 + 带头 = trusted
    req = _request({HEADER_PROXY_SOURCE: PROXY_SOURCE_ORCHESTRATOR, HEADER_USER_ID: "7"})
    assert classify_inbound(req, trusted, enforce=True) == InboundClassification.TRUSTED
    # 白名单 + 无头 = self_auth
    req = _request({HEADER_PROXY_SOURCE: PROXY_SOURCE_ORCHESTRATOR})
    assert classify_inbound(req, trusted, enforce=True) == InboundClassification.SELF_AUTH
    # 非白名单 + 带头 → enforce=True 为 403；enforce=False 为 ignored
    req = _request({HEADER_USER_ID: "999"})
    assert classify_inbound(req, trusted, enforce=True) == InboundClassification.FORBIDDEN
    assert classify_inbound(req, trusted, enforce=False) == InboundClassification.IGNORED
    # 非白名单 + 无头 = self_auth
    req = _request({})
    assert classify_inbound(req, trusted, enforce=True) == InboundClassification.SELF_AUTH


def test_inbound_identity_headers_present_and_strip() -> None:
    """身份头存在判定 + strip 过滤（字节对）。"""
    req = _request({HEADER_TENANT_ID: "evil"})
    assert inbound_identity_headers_present(req) is True
    req = _request({})
    assert inbound_identity_headers_present(req) is False

    header_items = [
        (b"x-tenant-id", b"evil"),
        (b"x-user-id", b"999"),
        (b"content-type", b"application/json"),
        (b"authorization", b"Bearer t"),
    ]
    stripped = strip_untrusted_identity_headers(header_items)
    names = {name.decode("latin-1") for name, _ in stripped}
    assert "x-tenant-id" not in names and "x-user-id" not in names
    assert "content-type" in names and "authorization" in names


# ---------------------------------------------------------------------------
# identity_context / inject（T1-1/2/4/9 载体）
# ---------------------------------------------------------------------------


def test_build_outbound_headers_user_matrix() -> None:
    """普通 user 上下文 → 四头 + 来源 + request-id（T1-1 user 形态）."""
    user_ctx = {
        "id": "123",
        "username": "alice",
        "tenant_code": "acme",
        "subject_type": "user",
        "role": "org_admin",
        "auth_method": "jwt",
    }
    headers = build_outbound_headers(_request({}), user_ctx, target_system=TARGET_SYSTEM_DPS)
    assert headers[HEADER_USER_ID] == "123"
    assert headers[HEADER_TENANT_ID] == "acme"
    assert headers[HEADER_ORG_ID] == "acme"
    assert headers[HEADER_USER_ROLE] == "org_admin"
    assert headers[HEADER_PROXY_SOURCE] == PROXY_SOURCE_DPS
    assert headers[HEADER_REQUEST_ID].startswith("req-")
    assert HEADER_AGENT_ID not in headers


def test_build_outbound_headers_delegated_matrix() -> None:
    """agent 委托上下文 → 四头=委托目标 + X-Agent-Id=执行 agent（T1-4）."""
    user_ctx = {
        "id": "7",
        "username": "agent-7",
        "tenant_code": "acme",
        "subject_type": "agent",
        "role": "org_admin",
        "auth_method": "jwt",
        "delegated": {
            "subject_id": 88,
            "subject_type": "user",
            "tenant_code": "acme",
            "role": "viewer",
        },
    }
    headers = build_outbound_headers(_request({}), user_ctx, target_system=TARGET_SYSTEM_LLM)
    assert headers[HEADER_USER_ID] == "88"
    assert headers[HEADER_TENANT_ID] == "acme"
    assert headers[HEADER_ORG_ID] == "acme"
    assert headers[HEADER_USER_ROLE] == "viewer"
    assert headers[HEADER_AGENT_ID] == "7"
    assert headers[HEADER_PROXY_SOURCE] == PROXY_SOURCE_LLM


def test_t1_9_no_identity_injects_no_fake_headers() -> None:
    """无身份可解析 → 不注入伪身份头（仅来源 + request_id）."""
    headers = build_outbound_headers(_request({}), None, target_system=TARGET_SYSTEM_RAG)
    assert HEADER_USER_ID not in headers
    assert HEADER_TENANT_ID not in headers
    assert HEADER_USER_ROLE not in headers
    assert headers[HEADER_PROXY_SOURCE] == PROXY_SOURCE_RAG
    assert HEADER_REQUEST_ID in headers


def test_t1_2_outbound_headers_only_from_issuance_context() -> None:
    """出站头只取签发上下文：客户端伪造头不进入出站装配（builder 不读入站身份头）."""
    user_ctx = {
        "id": "123",
        "username": "alice",
        "tenant_code": "acme",
        "subject_type": "user",
        "role": "org_member",
        "auth_method": "jwt",
    }
    # 请求携伪造头（X-User-ID=999/X-Tenant-ID=evil）——builder 不采纳
    headers = build_outbound_headers(
        _request({HEADER_USER_ID: "999", HEADER_TENANT_ID: "evil"}),
        user_ctx,
        target_system=TARGET_SYSTEM_GENERIC,
    )
    assert headers[HEADER_USER_ID] == "123"
    assert headers[HEADER_TENANT_ID] == "acme"
    assert headers[HEADER_PROXY_SOURCE] == PROXY_SOURCE_GENERIC


def test_build_outbound_headers_target_source_all() -> None:
    """每个 target_system → 对应 X-Proxy-Source 常量（§3.5 出站矩阵来源列）."""
    for target, source in SOURCE_BY_TARGET_SYSTEM.items():
        user_ctx = {"id": "1", "tenant_code": "acme", "subject_type": "user", "role": "viewer"}
        headers = build_outbound_headers(_request({}), user_ctx, target_system=target)
        assert headers[HEADER_PROXY_SOURCE] == source


def test_build_outbound_headers_unknown_target_rejected() -> None:
    """未知 target_system → 400 PARAM_INVALID."""
    with pytest.raises(BaseError) as exc_info:
        build_outbound_headers(None, {"id": "1"}, target_system="unknown-system")
    assert exc_info.value.code == ErrorCode.PARAM_INVALID


def test_resolve_identity_delegated_and_agent() -> None:
    """resolve_identity：委托覆盖 + agent principal agent_id（identity_context 单测）."""
    delegated_ctx = {
        "id": 7,
        "subject_type": "agent",
        "tenant_code": "acme",
        "delegated": {"subject_id": 88, "tenant_code": "acme", "role": "viewer"},
    }
    identity = resolve_identity(delegated_ctx)
    assert identity is not None
    assert identity.effective_subject_id == "88"
    assert identity.effective_tenant_code == "acme"
    assert identity.agent_id == "7"

    plain_user = {"id": 42, "tenant_code": "acme", "role": "admin"}
    identity = resolve_identity(plain_user)
    assert identity is not None
    assert identity.effective_subject_id == "42"
    assert identity.agent_id is None


# ---------------------------------------------------------------------------
# 约束常量
# ---------------------------------------------------------------------------


def test_length_limits_and_role_codes() -> None:
    """§3.1 头长/值域约束常量完整."""
    assert IDENTITY_HEADER_LENGTH_LIMITS[HEADER_USER_ID] == 128
    assert IDENTITY_HEADER_LENGTH_LIMITS[HEADER_TENANT_ID] == 64
    assert IDENTITY_HEADER_LENGTH_LIMITS[HEADER_PROXY_SOURCE] == 64
    assert IDENTITY_HEADER_LENGTH_LIMITS[HEADER_REQUEST_ID] == 64
    assert "editor" not in ALLOWED_OPENBASE_ROLE_CODES  # §2.7/Q-D-2：editor 不入现役码


# ---------------------------------------------------------------------------
# role_map 骨架（批次 2/T6 完整互译；此处验证无表透传与非法配置 fail-fast）
# ---------------------------------------------------------------------------


def test_role_map_load_invalid_json_fails_fast() -> None:
    """互译表非法 JSON → 400 PARAM_INVALID（fail-fast）."""
    with pytest.raises(BaseError) as exc_info:
        load_role_map("{not-json")
    assert exc_info.value.code == ErrorCode.PARAM_INVALID


def test_role_map_translate_passthrough_without_table() -> None:
    """未配置互译表 → 原样透传 OpenBase 角色码（无互译系统语义）."""
    assert translate_role_code(None, TARGET_SYSTEM_LLM, "org_member") == "org_member"
    assert translate_role_code({}, TARGET_SYSTEM_LLM, "org_member") == "org_member"


def test_role_map_translate_unmapped_fail_closed() -> None:
    """配置了目标表但源 code 未知 → fail-closed（不静默降 viewer）."""
    role_map = {
        "schema_version": 1,
        "systems": {
            "dps": {
                "openbase_to_target": {
                    "admin": {"target": "super_admin", "anchor": "manage"},
                    "viewer": {"target": "user", "anchor": "readonly"},
                }
            }
        },
    }
    assert translate_role_code(role_map, "dps", "admin") == "super_admin"
    with pytest.raises(BaseError):
        translate_role_code(role_map, "dps", "ghost_role")
