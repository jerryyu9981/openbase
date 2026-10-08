"""B1 权限播种脚本测试（TDD：先 RED，后实现）.

被测：``scripts/rbac_permission_seed.py``

职责（交付 A）：
- 以 ``config/rbac_permission_model.json`` 为**唯一输入**，产出声明式种子清单 JSON +
  幂等可执行 SQL（PostgreSQL 方言）+ 差异报告；
- **默认 dry-run**：不连库、不写库；
- 三条 fail-fast 强制校验：forbidden_grants 不得授予非 admin 角色、无悬空权限码、
  只读角色不得持有写类权限码。

TDD 用例映射（需求 ①~⑤）：
1. 正常模型 → 产物齐备且含幂等 SQL（``test_seed_generates_artifacts_with_idempotent_sql``）；
2. 默认不写库（``test_default_is_dry_run_and_never_touches_db``）；
3. forbidden_grants 被授予 org_admin → 报错退出（``test_forbidden_grant_to_non_admin_role_fails``）；
4. 只读角色含写码 → 报错（``test_readonly_role_with_write_code_fails``）；
5. 悬空权限码 → 报错（``test_dangling_permission_code_fails``）。
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "rbac_permission_seed.py"
MODEL_PATH = ROOT / "config" / "rbac_permission_model.json"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("rbac_permission_seed", SCRIPT)
    assert spec and spec.loader, f"无法加载播种脚本: {SCRIPT}"
    module = importlib.util.module_from_spec(spec)
    sys.modules["rbac_permission_seed"] = module
    spec.loader.exec_module(module)
    return module


def _model() -> dict:
    return json.loads(MODEL_PATH.read_text(encoding="utf-8"))


def _write_model(tmp_path: Path, model: dict) -> Path:
    path = tmp_path / "model.json"
    path.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# ① 正常模型 → 产物齐备 + 幂等 SQL
# ---------------------------------------------------------------------------


def test_seed_generates_artifacts_with_idempotent_sql(tmp_path: Path) -> None:
    """正常模型 → 四段声明式清单齐备 + 幂等 SQL + 落盘两个产物文件。"""
    module = _load_script()
    result = module.run(MODEL_PATH, tmp_path)

    manifest = result["manifest"]
    for section in ("roles", "permissions", "role_permissions", "user_role"):
        assert section in manifest, f"清单缺少段落 {section}"

    role_codes = {role["code"] for role in manifest["roles"]}
    assert {"admin", "org_admin", "user", "org_member", "viewer"} <= role_codes

    # role_permissions 条数 == 模型授予总数
    model = _model()
    expected_grants = sum(len(codes) for codes in model["role_to_permissions"].values())
    assert len(manifest["role_permissions"]) == expected_grants

    sql = result["sql"]
    assert "ON CONFLICT" in sql, "SQL 必须为幂等语义（ON CONFLICT DO NOTHING）"
    assert "INSERT INTO" in sql
    assert "BEGIN;" in sql and "COMMIT;" in sql

    assert (tmp_path / "rbac_seed_manifest.json").exists()
    assert (tmp_path / "rbac_seed.sql").exists()


# ---------------------------------------------------------------------------
# ② 默认不写库（dry-run）
# ---------------------------------------------------------------------------


def test_default_is_dry_run_and_never_touches_db(tmp_path: Path, monkeypatch) -> None:
    """默认无 --apply：流程不得建立任何数据库连接，产物标记 applied=False。"""
    module = _load_script()

    import openbase.core.db.session as dbsession

    def _boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("dry-run 不得建立数据库连接/写库")

    monkeypatch.setattr(dbsession, "init_db", _boom)
    monkeypatch.setattr(dbsession, "get_engine", _boom)
    monkeypatch.setattr(dbsession, "get_session_factory", _boom)

    exit_code = module.main(["--out-dir", str(tmp_path)])
    assert exit_code == 0

    manifest = json.loads(
        (tmp_path / "rbac_seed_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["mode"] == "dry-run"
    assert manifest["applied"] is False


# ---------------------------------------------------------------------------
# ③ forbidden_grants 被授予非 admin 角色 → fail-fast
# ---------------------------------------------------------------------------


def test_forbidden_grant_to_non_admin_role_fails(tmp_path: Path) -> None:
    """forbidden_grants（role:admin）被授予 org_admin → 校验报错并退出。"""
    module = _load_script()
    model = _model()
    model["role_to_permissions"]["org_admin"].append("role:admin")
    model_path = _write_model(tmp_path, model)
    out_dir = tmp_path / "out"

    errors = module.validate_model(model)
    assert any("forbidden_grants" in err or "禁授" in err for err in errors), errors

    exit_code = module.main(
        ["--model", str(model_path), "--out-dir", str(out_dir)]
    )
    assert exit_code != 0
    assert not (out_dir / "rbac_seed_manifest.json").exists()


# ---------------------------------------------------------------------------
# ④ 只读角色含写码 → fail-fast
# ---------------------------------------------------------------------------


def test_readonly_role_with_write_code_fails(tmp_path: Path) -> None:
    """只读角色（user）持有 user:write → 校验报错并退出。"""
    module = _load_script()
    model = _model()
    model["role_to_permissions"]["user"].append("user:write")
    model_path = _write_model(tmp_path, model)
    out_dir = tmp_path / "out"

    errors = module.validate_model(model)
    assert any("只读" in err or "readonly" in err for err in errors), errors

    exit_code = module.main(["--model", str(model_path), "--out-dir", str(out_dir)])
    assert exit_code != 0
    assert not (out_dir / "rbac_seed_manifest.json").exists()


# ---------------------------------------------------------------------------
# ⑤ 悬空权限码 → fail-fast
# ---------------------------------------------------------------------------


def test_dangling_permission_code_fails(tmp_path: Path) -> None:
    """授予了 modules[*].codes 中不存在的权限码 → 校验报错并退出。"""
    module = _load_script()
    model = _model()
    model["role_to_permissions"]["org_admin"].append("unknown_module:read")
    model_path = _write_model(tmp_path, model)
    out_dir = tmp_path / "out"

    errors = module.validate_model(model)
    assert any("悬空" in err or "dangling" in err for err in errors), errors

    exit_code = module.main(["--model", str(model_path), "--out-dir", str(out_dir)])
    assert exit_code != 0
    assert not (out_dir / "rbac_seed_manifest.json").exists()


# ---------------------------------------------------------------------------
# 差异报告
# ---------------------------------------------------------------------------


def test_diff_report_lists_added_and_removed(tmp_path: Path) -> None:
    """--current 差异报告：列出新增/移除项（角色维）。"""
    module = _load_script()
    current = {
        "roles": [{"code": "legacy_role", "name": "legacy", "description": None, "is_system": False}],
        "permissions": [],
        "role_permissions": [],
        "user_role": [],
    }
    current_path = tmp_path / "current.json"
    current_path.write_text(json.dumps(current, ensure_ascii=False), encoding="utf-8")

    result = module.run(MODEL_PATH, tmp_path / "out", current_path=current_path)
    diff = result["diff"]

    added_codes = {role["code"] for role in diff["roles"]["added"]}
    removed_codes = {role["code"] for role in diff["roles"]["removed"]}
    assert "admin" in added_codes
    assert "legacy_role" in removed_codes
