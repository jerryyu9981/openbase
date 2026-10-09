"""B1 权限播种脚本测试（TDD：先 RED，后实现）.

被测：``scripts/rbac_permission_seed.py``

职责（交付 A · v1.2.0 重修）：
- 以 ``config/rbac_permission_model.json`` 为**唯一输入**，产出声明式种子清单 JSON +
  **前置结构变更 DDL**（``rbac_seed_ddl.sql``，独立交付）+
  **纯 DML 幂等 SQL**（PostgreSQL 方言，落点 = **目标系统自身表结构** = 目标库 public schema）+
  差异报告；
- **默认 dry-run**：不连库、不写库；脚本内**不得 import 任何数据库驱动**（纯文本生成）；
- 强制校验（fail-fast，任何一项不通过即报错退出、**任何文件均不落盘**）：
  1. 目标档案不符（声明 schema 与目标档案不一致）；
  2. SQL 含禁用 schema（声明 target=openllm 而 SQL 出现 "openbase"）；
  3. forbidden_grants 不得授予非 admin 角色；
  4. 无悬空权限码；
  5. 只读角色不得持有写类权限码。
- 幂等：roles/permissions 用 (code) 冲突键、role_permissions 用 (role_id, permission_id) 冲突键；
  行主键由 uuid5(固定命名空间 + 稳定键) 生成 → 重跑结果完全一致（二次运行 diff = 0）。

TDD 用例映射：
① 正常模型 → 产物齐备 + 幂等 SQL + 落点 public（``test_seed_generates_artifacts_with_idempotent_sql``）；
② 默认 dry-run 不连库（``test_default_is_dry_run_and_never_touches_db``）；
③ 目标档案不符 → 硬失败（``test_target_profile_mismatch_fails``）；
④ SQL 含禁用 schema → 硬失败（``test_sql_with_forbidden_schema_fails``）；
⑤ forbidden_grants 授予 org_admin → 报错（``test_forbidden_grant_to_non_admin_role_fails``）；
⑥ 只读角色含写码 → 报错（``test_readonly_role_with_write_code_fails``）；
⑦ 悬空权限码 → 报错（``test_dangling_permission_code_fails``）；
⑧ 二次运行 diff = 0 且 DDL/SQL（忽略生成时间戳）逐字节一致（``test_rerun_is_deterministic_and_diff_zero``）；
⑨ 前置 DDL 与数据播种解耦（``test_prerequisite_ddl_is_separate_from_dml``）。
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "rbac_permission_seed.py"
MODEL_PATH = ROOT / "config" / "rbac_permission_model.json"

# 禁止出现在本脚本内的数据库驱动模块名（约束：纯文本生成，不落写库能力）。
FORBIDDEN_DRIVERS = ("psycopg2", "psycopg", "asyncpg", "sqlalchemy", "aiosqlite")


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


def _insert_targets(sql: str) -> set[tuple[str, str]]:
    """提取 SQL 中全部 ``INSERT INTO "schema"."table"`` 目标（忽略注释行）。"""
    body = "\n".join(line for line in sql.splitlines() if not line.lstrip().startswith("--"))
    return set(
        re.findall(
            r'INSERT\s+INTO\s+"([A-Za-z_][A-Za-z0-9_]*)"\s*\.\s*"([A-Za-z_][A-Za-z0-9_]*)"',
            body,
            re.IGNORECASE,
        )
    )


# SQL 头部生成时间戳行前缀：重跑幂等性比较须忽略时间（内容 id 稳定即可）。
_SQL_TIMESTAMP_PREFIX = "-- 方言：PostgreSQL；生成时间："


def _strip_generated_at(sql: str) -> str:
    """剔除头部生成时间戳行，用于重跑逐字节比较。"""
    return "\n".join(
        line
        for line in sql.splitlines()
        if not line.lstrip().startswith(_SQL_TIMESTAMP_PREFIX)
    )


# ---------------------------------------------------------------------------
# ① 正常模型 → 产物齐备 + 幂等 SQL + 落点 = 目标库 public schema
# ---------------------------------------------------------------------------


def test_seed_generates_artifacts_with_idempotent_sql(tmp_path: Path) -> None:
    """正常模型 → 四段声明式清单齐备 + 幂等 SQL + 落盘产物；落点仅为 public.*。"""
    module = _load_script()
    result = module.run(MODEL_PATH, tmp_path)

    manifest = result["manifest"]
    for section in ("roles", "permissions", "role_permissions", "user_role"):
        assert section in manifest, f"清单缺少段落 {section}"

    # 目标档案
    assert manifest["target_system"] == "openllm"
    assert manifest["target_schema"] == "public"
    assert manifest["target_key_type"] == "uuid"
    assert set(manifest["target_tables"]) == {
        "roles",
        "permissions",
        "role_permissions",
        "user_roles",
    }

    role_codes = {role["code"] for role in manifest["roles"]}
    assert {"admin", "org_admin", "user", "org_member", "viewer"} <= role_codes

    # role_permissions 条数 == 模型授予总数
    model = _model()
    expected_grants = sum(len(codes) for codes in model["role_to_permissions"].values())
    assert len(manifest["role_permissions"]) == expected_grants

    sql = result["sql"]
    assert "ON CONFLICT" in sql, "SQL 必须为幂等语义（ON CONFLICT DO NOTHING）"
    assert "ON CONFLICT (code) DO NOTHING" in sql
    assert "ON CONFLICT (role_id, permission_id) DO NOTHING" in sql
    assert "BEGIN;" in sql and "COMMIT;" in sql

    # 前置结构变更已与数据播种解耦（D1）：DDL 独立成文，DML 不含 DDL
    ddl = result["ddl"]
    assert "CREATE UNIQUE INDEX IF NOT EXISTS uq_role_permissions_role_permission" in ddl
    assert "CREATE UNIQUE INDEX" not in sql, "DML 文件不得内嵌前置 DDL"
    assert "INSERT INTO" not in ddl, "DDL 文件不得含数据写入"

    # 落点：只 INSERT 到 public.{roles,permissions,role_permissions}；绝无 openbase
    targets = _insert_targets(sql)
    assert targets == {
        ("public", "roles"),
        ("public", "permissions"),
        ("public", "role_permissions"),
    }, targets
    assert '"openbase"' not in sql, "修复后不得再出现 openbase schema"

    assert (tmp_path / "rbac_seed_manifest.json").exists()
    assert (tmp_path / "rbac_seed_ddl.sql").exists()
    assert (tmp_path / "rbac_seed.sql").exists()


# ---------------------------------------------------------------------------
# ② 默认不写库（dry-run）+ 纯文本生成（不含数据库驱动）
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


def test_script_is_pure_text_and_imports_no_db_driver() -> None:
    """约束（4）：入库脚本内不得 import 任何数据库驱动（纯文本生成）。"""
    source = SCRIPT.read_text(encoding="utf-8")
    lowered = source.lower()
    for driver in FORBIDDEN_DRIVERS:
        assert driver not in lowered, f"播种脚本不得引用数据库驱动 '{driver}'"


# ---------------------------------------------------------------------------
# ③ 目标档案不符 → fail-fast
# ---------------------------------------------------------------------------


def test_target_profile_mismatch_fails(tmp_path: Path) -> None:
    """声明 schema=openbase 而目标 openllm 档案为 public → 硬失败且不落盘任何文件。"""
    module = _load_script()
    profile = module.TARGET_PROFILES["openllm"]

    errors = module.validate_target_profile(profile, declared_schema="openbase")
    assert errors and any("目标档案不符" in err for err in errors), errors

    # 未登记目标 → 亦硬失败
    try:
        module.resolve_profile("not_registered")
    except module.SeedError as exc:
        assert "未登记" in str(exc)
    else:  # pragma: no cover - 防御
        raise AssertionError("未登记目标应硬失败")

    out_dir = tmp_path / "out"
    exit_code = module.main(["--out-dir", str(out_dir), "--schema", "openbase"])
    assert exit_code != 0
    assert not out_dir.exists(), "档案不符必须在任何文件落盘前失败"


# ---------------------------------------------------------------------------
# ④ SQL 含禁用 schema → fail-fast
# ---------------------------------------------------------------------------


def test_sql_with_forbidden_schema_fails() -> None:
    """声明 target=openllm 而 SQL 出现 INSERT INTO "openbase"."roles" → 硬失败。"""
    module = _load_script()
    profile = module.TARGET_PROFILES["openllm"]

    bad_sql = 'BEGIN;\nINSERT INTO "openbase"."roles" (code) VALUES (\'admin\');\nCOMMIT;'
    try:
        module.assert_sql_target(bad_sql, profile)
    except module.SeedError as exc:
        assert "落点护栏" in str(exc) and "openbase" in str(exc)
    else:  # pragma: no cover - 防御
        raise AssertionError("禁用 schema 必须被落点护栏拦截")

    # 归档目录同名禁用 schema 的非档案表亦被拦截
    bad_table = 'INSERT INTO "public"."users" (id) VALUES (\'x\');'
    try:
        module.assert_sql_target(bad_table, profile)
    except module.SeedError:
        pass
    else:  # pragma: no cover - 防御
        raise AssertionError("非档案表 INSERT 必须被落点护栏拦截")


# ---------------------------------------------------------------------------
# ⑤ forbidden_grants 被授予非 admin 角色 → fail-fast
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

    exit_code = module.main(["--model", str(model_path), "--out-dir", str(out_dir)])
    assert exit_code != 0
    assert not (out_dir / "rbac_seed_manifest.json").exists()


# ---------------------------------------------------------------------------
# ⑥ 只读角色含写码 → fail-fast
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
# ⑦ 悬空权限码 → fail-fast
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
# ⑧ 幂等：二次运行 SQL 逐字节一致 + diff = 0 + uuid5 稳定
# ---------------------------------------------------------------------------


def test_rerun_is_deterministic_and_diff_zero(tmp_path: Path) -> None:
    """同目录二次运行：DDL 逐字节一致、SQL（忽略生成时间戳）一致、清单稳定、差异合计为 0。"""
    module = _load_script()

    module.run(MODEL_PATH, tmp_path)
    sql_first = (tmp_path / "rbac_seed.sql").read_text(encoding="utf-8")
    ddl_first = (tmp_path / "rbac_seed_ddl.sql").read_text(encoding="utf-8")
    manifest_first = json.loads(
        (tmp_path / "rbac_seed_manifest.json").read_text(encoding="utf-8")
    )

    result = module.run(MODEL_PATH, tmp_path)
    sql_second = (tmp_path / "rbac_seed.sql").read_text(encoding="utf-8")
    ddl_second = (tmp_path / "rbac_seed_ddl.sql").read_text(encoding="utf-8")
    manifest_second = json.loads(
        (tmp_path / "rbac_seed_manifest.json").read_text(encoding="utf-8")
    )

    # DDL 逐字节一致；SQL 忽略头部生成时间戳后逐字节一致（uuid5 稳定 id 与冲突键不变）
    assert ddl_first == ddl_second
    assert _strip_generated_at(sql_first) == _strip_generated_at(sql_second)

    # 清单在忽略 generated_at 后完全一致
    manifest_first.pop("generated_at")
    manifest_second.pop("generated_at")
    assert manifest_first == manifest_second

    # 差异报告：全部为 0（幂等）
    diff = result["diff"]
    total = sum(
        diff[section]["added_count"]
        + diff[section]["removed_count"]
        + diff[section]["changed_count"]
        for section in diff
    )
    assert total == 0, diff

    # uuid5 稳定性（固定命名空间 + 稳定键）
    assert module.role_uuid("admin") == module.role_uuid("admin")
    assert module.permission_uuid("user:read") == module.permission_uuid("user:read")
    assert len(module.role_uuid("admin")) == 36


# ---------------------------------------------------------------------------
# ⑨ D1 处置：前置 DDL 与数据播种解耦（结构先行、数据后行）
# ---------------------------------------------------------------------------


def test_prerequisite_ddl_is_separate_from_dml(tmp_path: Path) -> None:
    """前置 DDL 单独成文：DDL 文件只含唯一索引、不混入数据事务；DML 文件为纯 DML。"""
    module = _load_script()
    result = module.run(MODEL_PATH, tmp_path)
    ddl = result["ddl"]
    sql = result["sql"]

    # DDL 文件：只含前置唯一索引；不包裹数据事务、不写入数据
    assert "CREATE UNIQUE INDEX IF NOT EXISTS uq_role_permissions_role_permission" in ddl
    assert '"public"."role_permissions"' in ddl
    assert "INSERT INTO" not in ddl
    assert "BEGIN;" not in ddl and "COMMIT;" not in ddl
    # 执行前置（重复行预检 + DDL 权限）与回滚语句须在案
    assert "HAVING COUNT(*) > 1" in ddl
    assert "CREATE INDEX" in ddl
    assert "DROP INDEX IF EXISTS" in ddl

    # DML 文件：纯 DML，无任何 DDL
    assert "CREATE UNIQUE INDEX" not in sql
    assert "BEGIN;" in sql and "COMMIT;" in sql

    assert (tmp_path / "rbac_seed_ddl.sql").exists()


# ---------------------------------------------------------------------------
# 差异报告（保留：新增/移除项）
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
