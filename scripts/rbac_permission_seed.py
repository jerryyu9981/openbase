#!/usr/bin/env python
"""B1 权限播种脚本（声明式 · 幂等 · 默认 dry-run）.

设计依据
--------
- 输入（唯一、人工裁定制品，本脚本只读不改）：``config/rbac_permission_model.json``；
- 关联契约：``config/role_tier_anchors.json``（角色档位锚点）、
  ``openbase/core/db/init.py``（既有 roles/permissions 种子与 schema=openbase 口径）。

产出（落到 ``--out-dir``，默认 ``doc/design/generated/``）
--------------------------------------------------------
- ``rbac_seed_manifest.json``：声明式种子清单（roles / permissions / role_permissions /
  user_role 绑定意图）；
- ``rbac_seed.sql``：**幂等**可执行 SQL（PostgreSQL 方言，``ON CONFLICT DO NOTHING``）；
- ``rbac_seed_diff.json``：相较既有清单（``--current`` 或同目录既往清单）的
  新增 / 变更 / 移除报告。

安全边界（为何本脚本不写库）
--------------------------
跨系统写库属**高影响动作**：权限变更影响目标系统（OpenLLM）授权面，须经人工过目、
评审与回滚预案后方可执行。故本脚本**默认且始终 dry-run**——不导入任何数据库驱动、
不建连接、不写库；仅产出**可审阅**的清单与 SQL，由**目标仓（OpenLLM）在其受控流程内
执行**（与派单《OpenBase-B1派单-OpenLLM授权接线》"权限码清单与角色映射"交付一致）。
因此本脚本**不提供 ``--apply``**：写库能力不落在本脚本内。

强制校验（fail-fast，任何一项不通过即报错退出、不产出任何文件）
--------------------------------------------------------------
1. 无悬空码：授予引用的权限码必须出现在 ``modules[*].codes``（``*`` 通配除外）；
2. 只读角色约束：``user/org_member/viewer`` 不得持有写类码（``*:write``/``*:delete``/``*:admin``）；
3. 禁授约束：``forbidden_grants`` 中的权限码不得出现在除 ``admin`` 外任何角色的授予里。

用法::

    python scripts/rbac_permission_seed.py                        # 默认 dry-run，产物落 doc/design/generated/
    python scripts/rbac_permission_seed.py --out-dir /tmp/seed    # 指定输出目录
    python scripts/rbac_permission_seed.py --current old_seed_manifest.json   # 生成差异报告
    python scripts/rbac_permission_seed.py --json                 # 追加打印清单 JSON 到 stdout

退出码：``0`` = 校验通过且产物已落盘；``1`` = 校验失败 / 输入缺失（不产出文件）。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = ROOT / "config" / "rbac_permission_model.json"
DEFAULT_OUT_DIR = ROOT / "doc" / "design" / "generated"
DEFAULT_SCHEMA = "openbase"

SCHEMA_VERSION = 1
TOOL = "rbac_permission_seed.py"
MANIFEST_FILENAME = "rbac_seed_manifest.json"
SQL_FILENAME = "rbac_seed.sql"
DIFF_FILENAME = "rbac_seed_diff.json"

WILDCARD = "*"
READONLY_ROLES = ("user", "org_member", "viewer")
WRITE_ACTIONS = ("write", "delete", "admin")

EXIT_OK = 0
EXIT_FAIL = 1

# 角色元信息（对齐 openbase/core/db/init.py 与 role_tier_anchors.json 的口径）。
ROLE_METADATA: dict[str, tuple[str, str, bool]] = {
    "admin": ("系统管理员", "内置管理员角色（持 * 通配）", True),
    "org_admin": ("组织管理员", "组织级管理角色（不含角色/权限管理，裁定 D2）", True),
    "user": ("普通用户", "标准业务用户角色（只读，裁定 D1）", True),
    "org_member": ("组织成员", "组织成员角色（只读，裁定 D1）", True),
    "viewer": ("只读用户", "只读访问角色（裁定 D1）", True),
}

# 差异报告的分段键定义（决定"同一项"的身份）。
_SECTION_KEYS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("roles", ("code",)),
    ("permissions", ("code",)),
    ("role_permissions", ("role_code", "permission_code")),
    ("user_role", ("username", "role_code")),
)


class SeedError(Exception):
    """播种校验失败（fail-fast；调用方据此报错退出）."""


# ---------------------------------------------------------------------------
# 输入 / 校验
# ---------------------------------------------------------------------------


def load_model(path: str | Path) -> dict[str, Any]:
    """读取权限模型 JSON（唯一输入）."""
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _action_of(code: str) -> str:
    """取权限码的 action 部分（``module:action`` → ``action``）."""
    return code.split(":", 1)[1] if ":" in code else code


def is_write_code(code: str) -> bool:
    """写类码判定：action ∈ {write, delete, admin}."""
    return _action_of(code) in WRITE_ACTIONS


def _known_permission_codes(model: dict[str, Any]) -> set[str]:
    """模块声明的全部权限码（用于悬空码校验）."""
    codes: set[str] = set()
    for module in (model.get("modules") or {}).values():
        for code in module.get("codes") or []:
            codes.add(code)
    return codes


def validate_model(model: dict[str, Any]) -> list[str]:
    """三条强制校验，返回违规信息列表（空列表 = 通过）.

    Args:
        model: 权限模型 dict。

    Returns:
        违规描述列表；任一非空即须 fail-fast。
    """
    errors: list[str] = []
    role_to_permissions = model.get("role_to_permissions") or {}
    modules = model.get("modules") or {}

    if not role_to_permissions:
        errors.append("模型缺少 role_to_permissions（无角色→权限映射）")
    if not modules:
        errors.append("模型缺少 modules（无权限码定义）")

    known_codes = _known_permission_codes(model)
    for module_name, module in modules.items():
        if not (module.get("codes") or []):
            errors.append(f"modules.{module_name}.codes 为空（模块未声明任何权限码）")

    # 校验 1：无悬空码（* 通配除外）。
    for role, codes in role_to_permissions.items():
        for code in codes or []:
            if code == WILDCARD:
                continue
            if code not in known_codes:
                errors.append(
                    f"悬空权限码：角色 {role} 授予了 modules[*].codes 中不存在的 '{code}'"
                )

    # 校验 2：只读角色不得持有写类码（含 * 通配）。
    for role in READONLY_ROLES:
        for code in role_to_permissions.get(role) or []:
            if code == WILDCARD or is_write_code(code):
                errors.append(
                    f"只读角色违规：{role} 持有写类权限码 '{code}'"
                    "（契约 *:write/*:delete/*:admin）"
                )

    # 校验 3：forbidden_grants 不得授予非 admin 角色。
    forbidden = {
        entry.get("code")
        for entry in (model.get("forbidden_grants") or [])
        if entry.get("code")
    }
    for role, codes in role_to_permissions.items():
        if role == "admin":
            continue
        for code in codes or []:
            if code in forbidden:
                errors.append(
                    f"禁授违规：非 admin 角色 {role} 持有 forbidden_grants 权限码 '{code}'"
                )

    return errors


# ---------------------------------------------------------------------------
# 声明式清单
# ---------------------------------------------------------------------------


def build_manifest(model: dict[str, Any], *, source_model: str = "") -> dict[str, Any]:
    """把权限模型转为声明式种子清单（校验失败即抛 :class:`SeedError`）."""
    errors = validate_model(model)
    if errors:
        raise SeedError("；".join(errors))

    role_to_permissions = model.get("role_to_permissions") or {}

    roles: list[dict[str, Any]] = []
    for code in sorted(role_to_permissions):
        name, description, is_system = ROLE_METADATA.get(code, (code, None, False))
        roles.append(
            {"code": code, "name": name, "description": description, "is_system": is_system}
        )

    permissions: list[dict[str, Any]] = [
        {"code": WILDCARD, "name": "全部权限", "module": "system", "type": 3}
    ]
    seen_codes = {WILDCARD}
    for module_name, module in sorted((model.get("modules") or {}).items()):
        for code in module.get("codes") or []:
            if code in seen_codes:
                continue
            seen_codes.add(code)
            permissions.append(
                {
                    "code": code,
                    "name": f"{module_name}·{_action_of(code)}",
                    "module": module_name,
                    "type": 1,
                }
            )

    role_permissions: list[dict[str, Any]] = []
    for role in sorted(role_to_permissions):
        for code in role_to_permissions[role] or []:
            role_permissions.append({"role_code": role, "permission_code": code})
    role_permissions.sort(key=lambda item: (item["role_code"], item["permission_code"]))

    return {
        "schema_version": SCHEMA_VERSION,
        "artifact": "rbac_seed_manifest",
        "tool": TOOL,
        "target_system": model.get("target_system"),
        "model_artifact": model.get("artifact"),
        "source_model": str(source_model),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "dry-run",
        "applied": False,
        "dialect": "postgresql",
        "schema": DEFAULT_SCHEMA,
        "note": (
            "声明式种子清单：由目标仓（OpenLLM）在其受控流程内执行 rbac_seed.sql；"
            "本脚本不连库、不写库（默认 dry-run）。"
        ),
        "roles": roles,
        "permissions": permissions,
        "role_permissions": role_permissions,
        "user_role": [],
        "user_role_note": (
            "用户→角色绑定为环境相关（依赖目标仓既有 users 行）：本脚本仅产出声明式清单，"
            "默认不含绑定；如需绑定，由目标仓按环境补充（如内置 admin 用户 → admin 角色）。"
        ),
    }


# ---------------------------------------------------------------------------
# 幂等 SQL 渲染（PostgreSQL 方言）
# ---------------------------------------------------------------------------


def _sql_literal(value: Any) -> str:
    """SQL 字面量（字符串单引号转义；bool/int 原样）."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def _qualified(schema: str, table: str) -> str:
    return f'"{schema}"."{table}"'


def render_sql(manifest: dict[str, Any], *, schema: str = DEFAULT_SCHEMA) -> str:
    """渲染幂等 SQL（PostgreSQL；重复执行结果一致）."""
    lines: list[str] = [
        f"-- {manifest['artifact']} — 由 {TOOL} 生成（幂等；可重复执行）",
        f"-- 目标系统：{manifest.get('target_system')}；方言：PostgreSQL；schema：{schema}",
        f"-- 生成时间：{manifest['generated_at']}",
        f"-- 源模型：{manifest.get('source_model')}",
        "-- 幂等语义：INSERT ... ON CONFLICT DO NOTHING",
        "--   · roles.code / permissions.code 唯一；role_permission / user_role 复合主键；",
        "-- 执行责任：**由目标仓（OpenLLM）执行**；本脚本不连库、不写库（默认 dry-run）。",
        "BEGIN;",
        "",
        "-- 1) 角色（roles）",
    ]
    for role in manifest["roles"]:
        lines.append(
            f"INSERT INTO {_qualified(schema, 'roles')} "
            "(name, code, description, is_system, created_at, updated_at) "
            f"VALUES ({_sql_literal(role['name'])}, {_sql_literal(role['code'])}, "
            f"{_sql_literal(role['description'])}, {_sql_literal(role['is_system'])}, "
            "now(), now()) "
            "ON CONFLICT (code) DO NOTHING;"
        )

    lines.extend(["", "-- 2) 权限点（permissions）"])
    for permission in manifest["permissions"]:
        lines.append(
            f"INSERT INTO {_qualified(schema, 'permissions')} "
            "(code, name, module, type, created_at, updated_at) "
            f"VALUES ({_sql_literal(permission['code'])}, {_sql_literal(permission['name'])}, "
            f"{_sql_literal(permission['module'])}, {_sql_literal(permission['type'])}, "
            "now(), now()) "
            "ON CONFLICT (code) DO NOTHING;"
        )

    lines.extend(["", "-- 3) 角色→权限（role_permission）"])
    for binding in manifest["role_permissions"]:
        lines.append(
            f"INSERT INTO {_qualified(schema, 'role_permission')} (role_id, permission_id) "
            f"SELECT r.id, p.id FROM {_qualified(schema, 'roles')} AS r "
            f"JOIN {_qualified(schema, 'permissions')} AS p "
            f"ON p.code = {_sql_literal(binding['permission_code'])} "
            f"WHERE r.code = {_sql_literal(binding['role_code'])} "
            "ON CONFLICT DO NOTHING;"
        )

    lines.extend(["", "-- 4) 用户→角色（user_role；绑定意图，默认空）"])
    if not manifest.get("user_role"):
        lines.append("-- （无绑定意图：由目标仓按环境补充）")
    for binding in manifest.get("user_role") or []:
        lines.append(
            f"INSERT INTO {_qualified(schema, 'user_role')} (user_id, role_id) "
            f"SELECT u.id, r.id FROM {_qualified(schema, 'users')} AS u "
            f"JOIN {_qualified(schema, 'roles')} AS r "
            f"ON r.code = {_sql_literal(binding['role_code'])} "
            f"WHERE u.username = {_sql_literal(binding['username'])} "
            "ON CONFLICT DO NOTHING;"
        )

    lines.extend(["", "COMMIT;", ""])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 差异报告
# ---------------------------------------------------------------------------


def _index_by(section: list[dict[str, Any]], key_fields: tuple[str, ...]) -> dict[tuple, dict]:
    indexed: dict[tuple, dict] = {}
    for item in section or []:
        key = tuple(item.get(field) for field in key_fields)
        indexed[key] = item
    return indexed


def diff_manifests(current: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """逐段比较清单：新增 / 变更 / 移除项."""
    diff: dict[str, Any] = {}
    for section, key_fields in _SECTION_KEYS:
        current_map = _index_by(current.get(section) or [], key_fields)
        new_map = _index_by(new.get(section) or [], key_fields)
        added = [new_map[key] for key in new_map if key not in current_map]
        removed = [current_map[key] for key in current_map if key not in new_map]
        changed = [
            {"key": list(key), "before": current_map[key], "after": new_map[key]}
            for key in new_map
            if key in current_map and new_map[key] != current_map[key]
        ]
        diff[section] = {
            "added": added,
            "removed": removed,
            "changed": changed,
            "added_count": len(added),
            "removed_count": len(removed),
            "changed_count": len(changed),
        }
    return diff


# ---------------------------------------------------------------------------
# 编排与 CLI
# ---------------------------------------------------------------------------


def _load_current(current_path: str | Path | None, out_dir: Path) -> dict[str, Any] | None:
    """解析既有清单：显式 --current 优先；否则复用同目录既往清单（若存在）."""
    candidate = Path(current_path) if current_path else out_dir / MANIFEST_FILENAME
    if not candidate.exists():
        return None
    with candidate.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def run(
    model_path: str | Path,
    out_dir: str | Path,
    *,
    current_path: str | Path | None = None,
    schema: str = DEFAULT_SCHEMA,
) -> dict[str, Any]:
    """读取模型 → 校验 → 产出清单/SQL/差异报告（全部落盘；不写库）.

    Returns:
        ``{"manifest","sql","diff","paths"}``。

    Raises:
        SeedError: 输入缺失或校验失败（fail-fast，不落盘任何文件）。
    """
    model_file = Path(model_path)
    if not model_file.exists():
        raise SeedError(f"权限模型不存在：{model_file}")

    model = load_model(model_file)
    manifest = build_manifest(model, source_model=str(model_file))
    sql = render_sql(manifest, schema=schema)

    out = Path(out_dir)
    current = _load_current(current_path, out)
    diff = diff_manifests(current, manifest) if current is not None else None

    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / MANIFEST_FILENAME
    sql_path = out / SQL_FILENAME
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    sql_path.write_text(sql, encoding="utf-8")

    paths: dict[str, str] = {"manifest": str(manifest_path), "sql": str(sql_path)}
    if diff is not None:
        diff_path = out / DIFF_FILENAME
        diff_path.write_text(
            json.dumps(diff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        paths["diff"] = str(diff_path)

    return {"manifest": manifest, "sql": sql, "diff": diff, "paths": paths}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "B1 权限播种：把 config/rbac_permission_model.json 转为声明式种子清单 + 幂等 SQL + "
            "差异报告（默认 dry-run；不连库、不写库；由目标仓执行 SQL）"
        )
    )
    parser.add_argument("--model", default=str(DEFAULT_MODEL), help="权限模型 JSON（默认 config/rbac_permission_model.json）")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="产物输出目录（默认 doc/design/generated/）")
    parser.add_argument("--current", default=None, help="既有种子清单 JSON（可选；用于差异报告）")
    parser.add_argument("--schema", default=DEFAULT_SCHEMA, help="目标 schema（默认 openbase）")
    parser.add_argument("--json", action="store_true", help="追加打印清单 JSON 到 stdout")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 入口；返回统一退出码（0=PASS / 1=FAIL）."""
    args = _build_parser().parse_args(argv)
    try:
        result = run(
            args.model, args.out_dir, current_path=args.current, schema=args.schema
        )
    except SeedError as exc:
        print(f"[ERROR] 校验/输入失败：{exc}", file=sys.stderr)
        return EXIT_FAIL

    manifest = result["manifest"]
    diff = result["diff"]
    print(
        f"[{TOOL}] mode=dry-run applied=False target={manifest.get('target_system')} "
        f"roles={len(manifest['roles'])} permissions={len(manifest['permissions'])} "
        f"role_permissions={len(manifest['role_permissions'])} user_role={len(manifest['user_role'])}"
    )
    print(f"  清单：{result['paths']['manifest']}")
    print(f"  SQL ：{result['paths']['sql']}（幂等，由目标仓执行）")
    if diff is not None:
        changes = sum(
            diff[section]["added_count"]
            + diff[section]["removed_count"]
            + diff[section]["changed_count"]
            for section in diff
        )
        print(f"  差异：{result['paths']['diff']}（变更项合计 {changes}；0 = 与既有清单一致）")
    else:
        print("  差异：（无既有清单，未生成差异报告）")

    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
