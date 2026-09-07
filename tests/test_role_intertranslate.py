"""P2-1 T6 RED 断言：OB-12 角色互译（§6，最小集 §6.3，Q-D）.

对齐草案 §10 T6：
- T6-1  `validate_role_map` 对合法起步表通过；越档（org_member→super_admin）、
        重复源、双向不一致 → 非法
- T6-2  档位语义映射：dps 出站 admin→super_admin、org_admin→org_admin、
        org_member/viewer→user（出站 X-User-Role 断言）
- T6-3  回译逆一致：target_to_openbase 与 openbase_to_target 互逆
- T6-4  无映射角色 fail-closed：未知源 code → 出站装配抛错/403，不静默降 viewer
- T6-5  语义档 rank 校验（降档允许/升档拒绝）
- T6-6  Q-D 评审结论记录（Q-D-1~Q-D-3 状态回写）
"""
from __future__ import annotations

import importlib
import json
import types
from pathlib import Path

import pytest

from openbase.core.errors import BaseError
from openbase.modules import dps_proxy as dps_proxy_module
from openbase.modules.protocol_headers import (
    HEADER_PROXY_SOURCE,
    HEADER_REQUEST_ID,
    HEADER_TENANT_ID,
    HEADER_USER_ID,
    HEADER_USER_ROLE,
    PROXY_SOURCE_DPS,
    build_outbound_headers,
    default_role_intertranslate,
    load_role_map,
    translate_role_code,
    validate_role_map,
)
from openbase.modules.protocol_headers.role_map import (
    OPENBASE_ROLE_CODES,
    ROLE_MAP_SCHEMA_VERSION,
    target_role_codes,
)
from openbase.settings import Settings

_SECRET = "p21-test-secret-0123456789abcdef0123456789abcdef"


def _req() -> types.SimpleNamespace:
    return types.SimpleNamespace(
        headers={},
        state=types.SimpleNamespace(request_id="req-t6-0001"),
    )


def _user_ctx(*, role: str, tenant_code: str = "acme") -> dict:
    return {
        "id": "42",
        "username": "alice",
        "tenant_code": tenant_code,
        "org_id": tenant_code,
        "subject_type": "user",
        "role": role,
        "permissions": [],
        "auth_method": "jwt",
    }


def _apply_settings(monkeypatch: pytest.MonkeyPatch, **overrides: object) -> Settings:
    settings = Settings(jwt_secret=_SECRET, **overrides)
    module = importlib.import_module("openbase.settings")
    monkeypatch.setattr(module, "_settings", settings)
    return settings


def _copy_with_override(
    section_overrides: dict | None = None,
    reverse_overrides: dict | None = None,
) -> dict:
    """复制默认互译表并覆写 dps 段（section 级 / reverse 级，测试便于构造非法表）."""
    data = json.loads(json.dumps(default_role_intertranslate()))
    dps = data["systems"]["dps"]
    if section_overrides:
        dps["openbase_to_target"].update(section_overrides)
    if reverse_overrides:
        dps["target_to_openbase"].update(reverse_overrides)
    return data


# ---------------------------------------------------------------------------
# T6-1：validate_role_map 对合法起步表通过；非法表（越档/重复源/双向不一致）拒绝
# ---------------------------------------------------------------------------


def test_t6_1_valid_start_map_passes() -> None:
    """起步互译表（§6.2 默认值）→ 校验通过（errors 为空）. """
    errors = validate_role_map(default_role_intertranslate())
    assert errors == []


def test_t6_1_duplicate_reverse_source_rejected() -> None:
    """重复源：target_to_openbase 单目标 source 列表含重复 code → 非法."""
    data = _copy_with_override(
        reverse_overrides={"user": {"source": ["org_member", "viewer", "viewer"]}}
    )
    errors = validate_role_map(data)
    assert errors, "duplicate reverse source should be rejected"


def test_t6_1_bidirectional_inconsistent_rejected() -> None:
    """双向不一致：viewer→user 成立但 user 的 source 不含 viewer → 非法."""
    data = _copy_with_override(
        reverse_overrides={"user": {"source": ["org_member"]}}
    )
    errors = validate_role_map(data)
    assert errors, "inverse inconsistency should be rejected"


def test_t6_1_unknown_source_code_rejected() -> None:
    """源 code 不在现役 OpenBase 码集（editor/幽灵码）→ 配置非法."""
    data = _copy_with_override(
        section_overrides={"editor": {"target": "user", "anchor": "readwrite"}}
    )
    errors = validate_role_map(data)
    assert errors, "editor/ghost source code should be rejected (Q-D-2)"


# ---------------------------------------------------------------------------
# T6-1 补充：validate_role_map 各类非法配置分支（覆盖率 + 语义断言）
# ---------------------------------------------------------------------------


def _dps_section(forward: dict, reverse: dict) -> dict:
    return {
        "schema_version": 1,
        "systems": {"dps": {
            "openbase_to_target": forward,
            "target_to_openbase": reverse,
        }},
    }


def test_t6_1_wrong_schema_version_rejected() -> None:
    data = json.loads(json.dumps(default_role_intertranslate()))
    data["schema_version"] = 999
    assert validate_role_map(data)


def test_t6_1_anchor_mismatch_rejected() -> None:
    """映射 entry 声明的 anchor 与源 code 规范档不一致 → 非法."""
    data = _copy_with_override(
        section_overrides={"admin": {"target": "super_admin", "anchor": "readonly"}}
    )
    assert validate_role_map(data)


def test_t6_1_target_enum_violation_rejected() -> None:
    """target/回译码不在 dps 目标枚举（如 super_user/ghost）→ 非法."""
    data = _dps_section(
        forward={
            "admin": {"target": "ghost_admin", "anchor": "manage"},
            "viewer": {"target": "user", "anchor": "readonly"},
        },
        reverse={"ghost_admin": {"source": ["admin"]}, "user": {"source": ["viewer"]}},
    )
    errors = validate_role_map(data)
    assert errors, "target role outside dps enumeration should be rejected"
    assert any("not in dps role enumeration" in error for error in errors)


def test_t6_1_reverse_target_not_in_enum_rejected() -> None:
    data = _dps_section(
        forward={"viewer": {"target": "user", "anchor": "readonly"}},
        reverse={"ghost_target": {"source": ["viewer"]}},
    )
    assert validate_role_map(data)


def test_t6_1_reverse_source_without_forward_rejected() -> None:
    """回译 source 在前向无映射 → 非法."""
    data = _dps_section(
        forward={"viewer": {"target": "user", "anchor": "readonly"}},
        reverse={"user": {"source": ["viewer", "admin"]}},
    )
    assert validate_role_map(data)


def test_t6_1_forward_missing_reverse_entry_rejected() -> None:
    """前向存在映射但回译缺该目标条目（或空源）→ 非法."""
    data = _dps_section(
        forward={"viewer": {"target": "user", "anchor": "readonly"}},
        reverse={"user": {"source": []}},
    )
    errors = validate_role_map(data)
    assert errors, "forward mapping without reverse entry should be rejected"


def test_t6_1_entry_missing_target_rejected() -> None:
    data = _dps_section(
        forward={"viewer": {"target": "", "anchor": "readonly"}},
        reverse={},
    )
    assert validate_role_map(data)


def test_t6_1_forward_entry_not_object_rejected() -> None:
    """前向映射值非对象（旧形态字符串/裸码）→ 非法."""
    data = _dps_section(
        forward={"viewer": "user"},
        reverse={},
    )
    assert validate_role_map(data)


def test_t6_1_reverse_entry_not_object_rejected() -> None:
    """回译条目非对象 → 非法."""
    data = _dps_section(
        forward={"viewer": {"target": "user", "anchor": "readonly"}},
        reverse={"user": ["viewer"]},
    )
    assert validate_role_map(data)


def test_t6_1_reverse_source_list_invalid_rejected() -> None:
    """回译 source 非列表 → 非法."""
    data = _dps_section(
        forward={"viewer": {"target": "user", "anchor": "readonly"}},
        reverse={"user": {"source": "viewer"}},
    )
    assert validate_role_map(data)


def test_t6_1_forward_section_not_object_rejected() -> None:
    """openbase_to_target 非对象 → 非法."""
    data = {
        "schema_version": 1,
        "systems": {"dps": {"openbase_to_target": "not-an-object", "target_to_openbase": {}}},
    }
    assert validate_role_map(data)


def test_t6_1_load_role_map_non_object_fails_fast() -> None:
    """role_intertranslate 为 JSON 数组/标量 → 400 PARAM_INVALID（fail-fast）."""
    with pytest.raises(BaseError) as exc_info:
        load_role_map("[1,2,3]")
    assert exc_info.value.code.value.startswith("PARAM")


def test_role_map_target_helpers() -> None:
    """target_role_codes / target_role_anchors 对外暴露（无登记系统放行）."""
    from openbase.modules.protocol_headers.role_map import (
        ROLE_MAP_ANCHOR_RANKS,
        target_role_anchors,
        target_role_codes,
    )

    assert ROLE_MAP_ANCHOR_RANKS["readonly"] == 1
    assert ROLE_MAP_ANCHOR_RANKS["readwrite"] == 2
    assert ROLE_MAP_ANCHOR_RANKS["manage"] == 3
    assert target_role_codes("dps") == frozenset({"super_admin", "org_admin", "user"})
    assert target_role_anchors("dps")["user"] == "readonly"
    assert target_role_codes("not-a-system") == frozenset()
    assert target_role_anchors("not-a-system") == {}


# ---------------------------------------------------------------------------
# T6-2：档位语义映射（dps 出站 X-User-Role 翻译断言）
# ---------------------------------------------------------------------------


def test_t6_2_dps_outbound_role_translated_by_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """dps-proxy 出站 X-User-Role 按互译表翻译（settings.role_intertranslate 接线）."""
    _apply_settings(
        monkeypatch,
        role_intertranslate=json.dumps(default_role_intertranslate()),
        dps_default_tenant_id="default-tenant",
        dps_default_org_id="default-org",
    )
    expected = {
        "admin": "super_admin",
        "org_admin": "org_admin",
        "org_member": "user",
        "viewer": "user",
    }
    for role_code, target_code in expected.items():
        headers = dps_proxy_module._build_identity_headers(
            _user_ctx(role=role_code), _req()
        )
        assert headers[HEADER_USER_ROLE] == target_code
        assert headers[HEADER_USER_ID] == "42"
        assert headers[HEADER_TENANT_ID] == "acme"
        assert headers[HEADER_PROXY_SOURCE] == PROXY_SOURCE_DPS
        assert HEADER_REQUEST_ID in headers


def test_t6_2_unmapped_system_passthrough() -> None:
    """无互译表系统（llm v1.0）原样透传 OpenBase 角色码（下游语义自行解释）."""
    role_map = load_role_map(json.dumps(default_role_intertranslate()))
    headers = build_outbound_headers(
        _req(),
        _user_ctx(role="org_member"),
        target_system="llm",
        role_map=role_map,
    )
    assert headers[HEADER_USER_ROLE] == "org_member"


# ---------------------------------------------------------------------------
# T6-3：回译逆一致（target_to_openbase ↔ openbase_to_target）
# ---------------------------------------------------------------------------


def test_t6_3_reverse_inverse_consistent() -> None:
    """起步表 target_to_openbase 与 openbase_to_target 逐目标互逆一致."""
    role_map = default_role_intertranslate()
    forward = role_map["systems"]["dps"]["openbase_to_target"]
    reverse = role_map["systems"]["dps"]["target_to_openbase"]

    forward_by_target: dict[str, set[str]] = {}
    for source_code, entry in forward.items():
        target_code = entry["target"]
        forward_by_target.setdefault(target_code, set()).add(source_code)

    reverse_sources: dict[str, set[str]] = {}
    for target_code, entry in reverse.items():
        reverse_sources[target_code] = set(entry["source"])

    # dps 目标码域一致 + 每个目标的前向源集合 == 回译源集合
    assert set(forward_by_target) == set(reverse_sources)
    for target_code, sources in forward_by_target.items():
        assert sources == reverse_sources[target_code]

    # 回译不得引入前向未声明的源
    known_sources = {s for s in forward}
    for sources in reverse_sources.values():
        assert sources <= known_sources


# ---------------------------------------------------------------------------
# T6-4：无映射角色 fail-closed（未知源 code 不静默降 viewer）
# ---------------------------------------------------------------------------


def test_t6_4_unknown_role_translation_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """未知源 code（ghost_role）经 dps 互译表出站 → 抛错 403，不静默降 viewer."""
    _apply_settings(
        monkeypatch,
        role_intertranslate=json.dumps(default_role_intertranslate()),
        dps_default_tenant_id="default-tenant",
        dps_default_org_id="default-org",
    )
    with pytest.raises(BaseError) as exc_info:
        dps_proxy_module._build_identity_headers(
            _user_ctx(role="ghost_role"), _req()
        )
    assert exc_info.value.status_code == 403


def test_t6_4_translate_direct_fail_closed() -> None:
    """translate_role_code 直接调用：未知源 → 403 BaseError."""
    role_map = load_role_map(json.dumps(default_role_intertranslate()))
    with pytest.raises(BaseError) as exc_info:
        translate_role_code(role_map, "dps", "ghost_role")
    assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# T6-5：语义档 rank 校验（降档允许/升档拒绝）
# ---------------------------------------------------------------------------


def test_t6_5_downrank_allowed() -> None:
    """降档（admin manage → user readonly 语义）→ 校验通过."""
    data = _copy_with_override(
        section_overrides={
            "admin": {"target": "user", "anchor": "manage"},
        },
        reverse_overrides={
            "super_admin": {"source": []},
            "user": {"source": ["org_member", "viewer", "admin"]},
        },
    )
    errors = validate_role_map(data)
    assert errors == []


def test_t6_5_uprank_rejected() -> None:
    """升档（org_member readonly → super_admin manage 语义）→ 校验拒绝（越档）."""
    data = _copy_with_override(
        section_overrides={
            "org_member": {"target": "super_admin", "anchor": "readonly"},
        },
        reverse_overrides={
            "super_admin": {"source": ["admin", "org_member"]},
            "user": {"source": ["viewer"]},
        },
    )
    errors = validate_role_map(data)
    assert errors, "uprank mapping should be rejected (越档)"


# ---------------------------------------------------------------------------
# T6-6：Q-D 评审结论记录回写（互译表文档 + 常量/配置面）
# ---------------------------------------------------------------------------


def test_t6_6_qd_conclusion_recorded_in_doc() -> None:
    """《角色互译表 v1.0》文档归档 Q-D-1~Q-D-3 结论（editor 不入表 / fail-closed）."""
    root = Path(__file__).resolve().parent.parent
    doc_path = root / "doc" / "design" / "OpenBase-角色互译表-v1.0.md"
    assert doc_path.exists(), f"互译表文档缺失: {doc_path}"
    content = doc_path.read_text(encoding="utf-8")
    for marker in ("Q-D-1", "Q-D-2", "Q-D-3", "editor 不入互译表", "fail-closed"):
        assert marker in content, f"互译表文档缺少 {marker}"


def test_t6_6_default_map_obeys_qd_decisions() -> None:
    """默认互译表内容符合 Q-D：无 editor 码、仅 dps 起步、schema_version=1."""
    role_map = default_role_intertranslate()
    assert role_map["schema_version"] == ROLE_MAP_SCHEMA_VERSION
    assert "editor" not in role_map["systems"]["dps"]["openbase_to_target"]
    # Q-D-1：起步仅 OpenBase↔DPS
    assert set(role_map["systems"]) == {"dps"}
    # editor 语义档由 org_admin 承担且 editor 码不入现役码集
    assert "editor" not in OPENBASE_ROLE_CODES
    # dps 目标角色域 = {super_admin, org_admin, user}
    assert set(target_role_codes("dps")) == {"super_admin", "org_admin", "user"}


def test_t6_6_settings_carries_role_intertranslate_key() -> None:
    """settings 已登记 role_intertranslate 配置键（verify-env config_single_source 项）."""
    settings = Settings(jwt_secret=_SECRET)
    assert hasattr(settings, "role_intertranslate")
    assert settings.role_intertranslate == ""
