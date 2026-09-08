"""P2-1 T7 RED 断言：OB-8 code 化收口（§7/§10 T7）.

对齐草案 §10 T7：
- T7-1  dps-proxy 出站 X-Org-ID == X-Tenant-ID（org_raw 独立链删除后别名断言）
- T7-2  llm/memory 出站 X-Org-ID 同源别名（不再取独立 org_id 中间态）
- T7-3  enforce_org_alias=true 时 X-Org-ID ≠ X-Tenant-ID → 403 BIZ_ORG_ALIAS_MISMATCH
- T7-4  validate_dps_code_map：条目命中 tenants.code、dps 侧非空、无重复、双向一致
- T7-5  冲突检测：同 code 双映射 → 对账报告冲突项（0 未决为门禁）
- T7-6  dps_default_org_id/tenant_id 标记 deprecated：verify-env WARN 提示
- T7-7  对账报告输出且 0 未决冲突（scripts/audit_dps_code_map.py）
- 附：登记式基线示例文件（config/dps_code_map.example.json + 基线登记示例文档）
"""
from __future__ import annotations

import importlib
import json
import subprocess
import sys
import types
from pathlib import Path

import pytest

from openbase.core.errors import BaseError, ErrorCode
from openbase.modules import dps_proxy as dps_proxy_module
from openbase.modules import llm_proxy as llm_proxy_module
from openbase.modules.protocol_headers import (
    HEADER_ORG_ID,
    HEADER_TENANT_ID,
    build_outbound_headers,
)
from openbase.modules.proxy import memory_proxy as memory_proxy_module
from openbase.settings import Settings

_SECRET = "p21-test-secret-0123456789abcdef0123456789abcdef"
_ROOT = Path(__file__).resolve().parent.parent


def _req() -> types.SimpleNamespace:
    return types.SimpleNamespace(
        headers={},
        state=types.SimpleNamespace(request_id="req-t7-0001"),
    )


def _user_ctx(*, tenant_code: str = "acme", org_id: str | None = "acme") -> dict:
    """统一 user 上下文（org_id 兼容遗留位；别名收敛后不得独立取值）."""
    ctx: dict = {
        "id": "42",
        "username": "alice",
        "tenant_code": tenant_code,
        "subject_type": "user",
        "role": "org_admin",
        "permissions": [],
        "auth_method": "jwt",
    }
    if org_id is not None:
        ctx["org_id"] = org_id
    return ctx


def _apply_settings(monkeypatch: pytest.MonkeyPatch, **overrides: object) -> Settings:
    settings = Settings(jwt_secret=_SECRET, **overrides)
    module = importlib.import_module("openbase.settings")
    monkeypatch.setattr(module, "_settings", settings)
    return settings


def _map_json(entries: list[dict], **extra: object) -> str:
    """构造登记式基线 JSON（dps_code_map settings 值）."""
    data: dict = {
        "schema_version": 1,
        "source_of_truth": "openbase.tenants.code",
        "last_reconciled_at": "2026-09-07",
        "entries": entries,
    }
    data.update(extra)
    return json.dumps(data, ensure_ascii=False)


def _entry(
    tenant_code: str,
    *,
    dps_org_id: str,
    dps_tenant_id: str,
    reconciled_at: str = "2026-09-07",
    status: str = "verified",
) -> dict:
    return {
        "tenant_code": tenant_code,
        "dps_org_id": dps_org_id,
        "dps_tenant_id": dps_tenant_id,
        "reconciled_at": reconciled_at,
        "status": status,
    }


# ---------------------------------------------------------------------------
# T7-1 / T7-2：X-Org-ID 别名收敛（org_raw 独立链删除，org==tenant 或别名命中）
# ---------------------------------------------------------------------------


def test_t7_1_dps_org_alias_equals_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """dps-proxy 出站 X-Org-ID == X-Tenant-ID：ctx.org_id（遗留独立值）不再取值."""
    _apply_settings(monkeypatch)
    headers = dps_proxy_module._build_identity_headers(
        _user_ctx(tenant_code="acme", org_id="ghost-org"), _req()
    )
    assert headers[HEADER_TENANT_ID] == "acme"
    assert headers[HEADER_ORG_ID] == headers[HEADER_TENANT_ID] == "acme"


def test_t7_1_dps_org_alias_equals_mapped_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """dps_code_map 登记命中时 X-Org-ID == X-Tenant-ID == dps_tenant_id（UUID 基线）."""
    _apply_settings(
        monkeypatch,
        dps_code_map=_map_json(
            [_entry("acme", dps_org_id="uuid-acme", dps_tenant_id="uuid-acme")]
        ),
    )
    headers = dps_proxy_module._build_identity_headers(
        _user_ctx(tenant_code="acme"), _req()
    )
    assert headers[HEADER_TENANT_ID] == "uuid-acme"
    assert headers[HEADER_ORG_ID] == "uuid-acme"


def test_t7_2_llm_org_alias_same_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """llm-proxy 出站 X-Org-ID 同源别名（不再取独立 org_id 中间态 org-001）. """
    _apply_settings(monkeypatch)
    headers = llm_proxy_module._build_upstream_headers(
        _req(), _user_ctx(tenant_code="tenant-001", org_id="org-001")
    )
    assert headers[HEADER_TENANT_ID] == "tenant-001"
    assert headers[HEADER_ORG_ID] == headers[HEADER_TENANT_ID]


def test_t7_2_memory_org_alias_same_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """memory-proxy 出站 X-Org-ID 同源别名（无独立 org 兜底链参与隔离键）."""
    _apply_settings(monkeypatch)
    headers = memory_proxy_module._build_upstream_headers(
        _req(), _user_ctx(tenant_code="acme", org_id="legacy-org")
    )
    assert headers[HEADER_TENANT_ID] == "acme"
    assert headers[HEADER_ORG_ID] == headers[HEADER_TENANT_ID] == "acme"
    # 硬编码默认 org 链（openbase-default）不再参与隔离键：tenant 缺省时 org==tenant 缺省
    headers_default = memory_proxy_module._build_upstream_headers(
        _req(), _user_ctx(tenant_code="", org_id="openbase-default")
    )
    assert headers_default[HEADER_TENANT_ID] == "default"
    assert headers_default[HEADER_ORG_ID] == headers_default[HEADER_TENANT_ID]


# ---------------------------------------------------------------------------
# T7-3：enforce_org_alias 强模式（X-Org-ID ≠ X-Tenant-ID → 403）
# ---------------------------------------------------------------------------


def test_t7_3_enforce_org_alias_mismatch_raises_403() -> None:
    """builder 直连：enforce_org_alias=true + org/tenant 值不一致 → 403 别名错配."""
    with pytest.raises(BaseError) as exc_info:
        build_outbound_headers(
            _req(),
            _user_ctx(tenant_code="acme"),
            target_system="dps",
            tenant_value_map={"acme": "tenant-x"},
            org_value_map={"acme": "org-y"},
            enforce_org_alias=True,
        )
    assert exc_info.value.code == ErrorCode.BIZ_ORG_ALIAS_MISMATCH
    assert exc_info.value.status_code == 403


def test_t7_3_enforce_org_alias_consistent_passes() -> None:
    """enforce=true 且 org==tenant（经 dps_code_map 同 UUID）→ 正常出站无 403."""
    headers = build_outbound_headers(
        _req(),
        _user_ctx(tenant_code="acme"),
        target_system="dps",
        tenant_value_map={"acme": "uuid-acme"},
        org_value_map={"acme": "uuid-acme"},
        enforce_org_alias=True,
    )
    assert headers[HEADER_TENANT_ID] == "uuid-acme"
    assert headers[HEADER_ORG_ID] == "uuid-acme"


def test_t7_3_enforce_org_alias_default_off_compat() -> None:
    """兼容段（enforce=false）：org≠tenant 值仍允许（两段式开关过渡）. """
    headers = build_outbound_headers(
        _req(),
        _user_ctx(tenant_code="acme"),
        target_system="dps",
        tenant_value_map={"acme": "tenant-x"},
        org_value_map={"acme": "org-y"},
        enforce_org_alias=False,
    )
    assert headers[HEADER_TENANT_ID] == "tenant-x"
    assert headers[HEADER_ORG_ID] == "org-y"


def test_t7_3_dps_proxy_enforce_org_alias_conflict_403(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """dps-proxy 经 settings.enforce_org_alias=true + 基线 org/tenant 值不一致 → 403."""
    _apply_settings(
        monkeypatch,
        enforce_org_alias=True,
        dps_code_map=_map_json(
            [_entry("acme", dps_org_id="uuid-org-a", dps_tenant_id="uuid-tenant-b")]
        ),
    )
    with pytest.raises(BaseError) as exc_info:
        dps_proxy_module._build_identity_headers(_user_ctx(tenant_code="acme"), _req())
    assert exc_info.value.code == ErrorCode.BIZ_ORG_ALIAS_MISMATCH
    assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# T7-4：validate_dps_code_map（基线登记式校验）
# ---------------------------------------------------------------------------


def test_t7_4_valid_map_passes() -> None:
    from openbase.modules.protocol_headers.dps_code_map import validate_dps_code_map

    errors = validate_dps_code_map(
        _map_json([_entry("acme", dps_org_id="u-1", dps_tenant_id="u-1")]),
        known_tenant_codes={"acme"},
    )
    assert errors == []


def test_t7_4_empty_map_is_valid_default() -> None:
    """默认无条目（空表）→ 合法（登记式基线默认）."""
    from openbase.modules.protocol_headers.dps_code_map import validate_dps_code_map

    assert validate_dps_code_map("", known_tenant_codes={"acme"}) == []
    assert validate_dps_code_map(
        _map_json([]), known_tenant_codes={"acme"}
    ) == []


def test_t7_4_invalid_json_rejected() -> None:
    from openbase.modules.protocol_headers.dps_code_map import validate_dps_code_map

    errors = validate_dps_code_map("not-json", known_tenant_codes={"acme"})
    assert errors
    assert errors[0].startswith("invalid JSON")


def test_t7_4_wrong_schema_version_rejected() -> None:
    from openbase.modules.protocol_headers.dps_code_map import validate_dps_code_map

    data = json.loads(_map_json([]))
    data["schema_version"] = 999
    assert validate_dps_code_map(json.dumps(data), known_tenant_codes={"acme"})


def test_t7_4_unknown_tenant_code_rejected() -> None:
    """条目 tenant_code 未命中 tenants.code（唯一事实源）→ 非法."""
    from openbase.modules.protocol_headers.dps_code_map import validate_dps_code_map

    errors = validate_dps_code_map(
        _map_json([_entry("ghost", dps_org_id="u-1", dps_tenant_id="u-1")]),
        known_tenant_codes={"acme"},
    )
    assert any("tenant_code" in error and "ghost" in error for error in errors)


def test_t7_4_dps_ids_empty_rejected() -> None:
    from openbase.modules.protocol_headers.dps_code_map import validate_dps_code_map

    errors = validate_dps_code_map(
        _map_json([_entry("acme", dps_org_id="", dps_tenant_id="u-1")]),
        known_tenant_codes={"acme"},
    )
    assert errors


def test_t7_4_duplicate_code_rejected() -> None:
    from openbase.modules.protocol_headers.dps_code_map import validate_dps_code_map

    errors = validate_dps_code_map(
        _map_json(
            [
                _entry("acme", dps_org_id="u-1", dps_tenant_id="u-1"),
                _entry("acme", dps_org_id="u-2", dps_tenant_id="u-2"),
            ]
        ),
        known_tenant_codes={"acme"},
    )
    assert errors


# ---------------------------------------------------------------------------
# T7-5：冲突检测（同 code 双映射 → 对账报告冲突项；0 未决为门禁）
# ---------------------------------------------------------------------------


def test_t7_5_conflict_detected() -> None:
    from openbase.modules.protocol_headers.dps_code_map import (
        dps_code_map_conflicts,
    )

    entries = [
        _entry("acme", dps_org_id="u-1", dps_tenant_id="u-1"),
        _entry("acme", dps_org_id="u-2", dps_tenant_id="u-2"),
    ]
    conflicts = dps_code_map_conflicts(entries)
    assert len(conflicts) == 1
    assert conflicts[0]["tenant_code"] == "acme"


def test_t7_5_no_conflict_when_clean() -> None:
    from openbase.modules.protocol_headers.dps_code_map import (
        dps_code_map_conflicts,
    )

    entries = [
        _entry("acme", dps_org_id="u-1", dps_tenant_id="u-1"),
        _entry("globex", dps_org_id="u-9", dps_tenant_id="u-9"),
    ]
    assert dps_code_map_conflicts(entries) == []


# ---------------------------------------------------------------------------
# T7-6：dps_default_org_id/tenant_id deprecated（verify-env WARN 数据源）
# ---------------------------------------------------------------------------


def test_t7_6_deprecated_defaults_reported() -> None:
    settings = Settings(jwt_secret=_SECRET, dps_default_org_id="o", dps_default_tenant_id="t")
    deprecated = settings.deprecated_dps_defaults()
    assert "dps_default_org_id" in deprecated
    assert "dps_default_tenant_id" in deprecated


def test_t7_6_deprecated_defaults_empty_when_unset() -> None:
    settings = Settings(
        jwt_secret=_SECRET, dps_default_org_id="", dps_default_tenant_id=""
    )
    assert settings.deprecated_dps_defaults() == {}


def test_t7_6_deprecation_warnings_text() -> None:
    settings = Settings(jwt_secret=_SECRET, dps_default_tenant_id="t")
    warnings_text = settings.dps_defaults_deprecation_warnings()
    assert any("deprecated" in message for message in warnings_text)


# ---------------------------------------------------------------------------
# T7-7：scripts/audit_dps_code_map.py 对账报告（0 未决冲突为门禁）
# ---------------------------------------------------------------------------


def _write_json(tmp_path: Path, name: str, payload: dict | list) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _run_audit_script(
    tmp_path: Path,
    *,
    map_payload: dict,
    tenant_codes: list[str],
    extra_args: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    map_path = _write_json(tmp_path, "dps_code_map.json", map_payload)
    tenants_path = _write_json(tmp_path, "tenants.json", tenant_codes)
    report_path = tmp_path / "audit_report.json"
    script = _ROOT / "scripts" / "audit_dps_code_map.py"
    return subprocess.run(
        [
            sys.executable,
            str(script),
            "--map-json",
            str(map_path),
            "--tenants-json",
            str(tenants_path),
            "--report",
            str(report_path),
            *(extra_args or []),
        ],
        cwd=_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_t7_7_audit_report_clean_map(tmp_path: Path) -> None:
    """对账报告：干净基线 0 未决 → 退出码 0 + report JSON 冲突为空."""
    result = _run_audit_script(
        tmp_path,
        map_payload={
            "schema_version": 1,
            "source_of_truth": "openbase.tenants.code",
            "last_reconciled_at": "2026-09-07",
            "entries": [_entry("acme", dps_org_id="u-1", dps_tenant_id="u-1")],
        },
        tenant_codes=["acme"],
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report_path = tmp_path / "audit_report.json"
    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["unresolved_conflicts"] == []
    assert "0" in result.stdout or "0" in json.dumps(report)


def test_t7_7_audit_report_conflict_exit_nonzero(tmp_path: Path) -> None:
    """对账报告：同 code 双映射（冲突未清零）→ 退出码非 0 + 冲突项输出."""
    result = _run_audit_script(
        tmp_path,
        map_payload={
            "schema_version": 1,
            "source_of_truth": "openbase.tenants.code",
            "last_reconciled_at": "2026-09-07",
            "entries": [
                _entry("acme", dps_org_id="u-1", dps_tenant_id="u-1"),
                _entry("acme", dps_org_id="u-2", dps_tenant_id="u-2"),
            ],
        },
        tenant_codes=["acme"],
    )
    assert result.returncode != 0, result.stdout + result.stderr
    report_path = tmp_path / "audit_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["unresolved_conflicts"], "冲突项应出现在对账报告"


# ---------------------------------------------------------------------------
# 附：登记式基线示例文件（config 示例 + 基线登记文档）
# ---------------------------------------------------------------------------


def test_t7_config_example_dps_code_map_file() -> None:
    """config/dps_code_map.example.json 存在且 JSON 合法、schema 通过校验."""
    example_path = _ROOT / "config" / "dps_code_map.example.json"
    assert example_path.exists(), f"示例缺失: {example_path}"
    payload = json.loads(example_path.read_text(encoding="utf-8"))
    from openbase.modules.protocol_headers.dps_code_map import validate_dps_code_map

    tenant_codes = {entry["tenant_code"] for entry in payload.get("entries", [])}
    errors = validate_dps_code_map(
        json.dumps(payload, ensure_ascii=False), known_tenant_codes=tenant_codes
    )
    assert errors == []


def test_t7_baseline_doc_registered() -> None:
    """映射基线登记示例文档存在且含登记纪律/脚本说明."""
    doc_path = _ROOT / "doc" / "design" / "OpenBase-DPS-code映射基线登记示例-v1.0.0.md"
    assert doc_path.exists(), f"基线登记文档缺失: {doc_path}"
    content = doc_path.read_text(encoding="utf-8")
    for marker in ("dps_code_map", "audit_dps_code_map", "tenants.code", "schema_version"):
        assert marker in content, f"基线登记文档缺少 {marker}"
