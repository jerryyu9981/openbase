#!/usr/bin/env python
"""B1 权限播种脚本（声明式 · 幂等 · 默认 dry-run；目标 = 目标系统自身表结构）.

设计依据
--------
- 输入（唯一、人工裁定制品，本脚本只读不改）：``config/rbac_permission_model.json``；
- 关联契约：``config/role_tier_anchors.json``（角色档位锚点）。

目标落点（这是本脚本的**唯一正确落点**）
--------------------------------------
B1 要播种的是**目标系统（OpenLLM）自身**的 RBAC 表，位于**目标库的 public schema**。
> 目标库 = **局域网内共享基础设施中的唯一数据库**（`192.168.0.151:5432/nuct`）：四系统同实例、
> 按 schema 区分（`openbase` / `platform` / `public`）。前置 DDL 与数据播种均落在该共享库上，
> 影响面跨系统共担，故须经**受控变更流程**执行（结构先行、数据后行）。

- ``public.roles(code, name, role_type, level, scope, …)``（主键 uuid）；
- ``public.permissions(code, resource_type, action, scope, …)``（code 与 resource_type/action 四字段并存）；
- ``public.role_permissions(role_id uuid, permission_id uuid, constraints jsonb, is_active)``（主键 uuid）；
- ``public.user_roles(user_id uuid, role_id uuid, …)``（主键 uuid）。

> **历史缺陷（本版修复）**：v1.0.0 误把落点写成 OpenBase 自己的
> ``"openbase"."roles"``（bigint 主键、单列 code+module 模型）——与目标系统权限模型互不相同。
> 本版引入**目标档案表**（:data:`TARGET_PROFILES`）与**生成期护栏**，令该缺陷不可能重犯。

强制校验（fail-fast，任何一项不通过即报错退出、**不产出任何文件**）
------------------------------------------------------------------
1. 目标档案一致：``target_system`` 必须登记在档案表；声明 schema/键类型/表集合与档案**逐项一致**；
2. SQL 落点护栏：声明 ``target=openllm`` 时，生成的 SQL **只允许**出现 ``"public".*``，
   出现任何禁用 schema（``"openbase"`` / ``"platform"``）即硬失败；
3. 无悬空码：授予引用的权限码必须出现在 ``modules[*].codes``（``*`` 通配除外）；
4. 只读角色约束：``user/org_member/viewer`` 不得持有 ``*:write``/``*:delete``/``*:admin``；
5. 禁授约束：``forbidden_grants`` 的权限码不得出现在除 ``admin`` 外任何角色的授予里。

幂等
----
- ``roles`` / ``permissions``：``ON CONFLICT (code) DO NOTHING``；
- ``role_permissions``：``ON CONFLICT (role_id, permission_id) DO NOTHING``；
- 行主键 ``id`` 一律由 ``uuid5(固定命名空间, 稳定键)`` 生成 → **重跑结果完全一致**；
- ``role_permissions`` 的冲突键依赖 ``(role_id, permission_id)`` 唯一索引：该唯一索引属
  **前置结构变更**，独立产出于 ``rbac_seed_ddl.sql``（实测目标库当前**尚无**该唯一约束）。
  交付与执行按「**结构先行、数据后行**」解耦：目标仓先经其结构变更通道执行 DDL，
  再执行 ``rbac_seed.sql``（纯 DML）。

安全边界（为何本脚本不写库）
--------------------------
- **默认且始终 dry-run**：不提供 ``--apply``；不建连接、不写库；
- **提交到仓的本文件不 import 任何数据库驱动**（纯文本生成）：写库能力不落在本脚本内；
- 产出的可执行 SQL 由**目标仓（OpenLLM）在其受控流程内执行**。

用法::

    python scripts/rbac_permission_seed.py                        # 默认 dry-run，产物落 doc/design/generated/
    python scripts/rbac_permission_seed.py --out-dir /tmp/seed    # 指定输出目录
    python scripts/rbac_permission_seed.py --current old.json      # 生成差异报告
    python scripts/rbac_permission_seed.py --json                  # 追加打印清单 JSON 到 stdout

退出码：``0`` = 校验通过且产物已落盘；``1`` = 校验失败 / 输入缺失（不产出文件）。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = ROOT / "config" / "rbac_permission_model.json"
DEFAULT_OUT_DIR = ROOT / "doc" / "design" / "generated"

SCHEMA_VERSION = 2
TOOL = "rbac_permission_seed.py"
MANIFEST_FILENAME = "rbac_seed_manifest.json"
DDL_FILENAME = "rbac_seed_ddl.sql"
SQL_FILENAME = "rbac_seed.sql"
DIFF_FILENAME = "rbac_seed_diff.json"

# 前置结构变更：role_permissions 幂等冲突键 (role_id, permission_id) 所需的唯一索引名。
# 名称一经登记不得更改（评审说明 §8 回滚语句依赖该名）。
ROLE_PERMISSION_UNIQUE_INDEX = "uq_role_permissions_role_permission"

WILDCARD = "*"
READONLY_ROLES = ("user", "org_member", "viewer")
WRITE_ACTIONS = ("write", "delete", "admin")
PERMISSION_SCOPE = "platform"

EXIT_OK = 0
EXIT_FAIL = 1

# uuid5 固定命名空间：一经登记不得更改，否则重跑全部行 id 变化、破坏幂等。
UUID_NAMESPACE = uuid.UUID("8f0f6c2a-3b1d-4e57-9a6c-0d2f4b7e1c93")
UUID_KEY_PREFIX = "openbase/rbac-seed/v1"


@dataclass(frozen=True)
class TargetProfile:
    """目标系统档案：声明「目标 → (库名, schema, 主键类型, 表集合)」的唯一事实源.

    生成期据此校验「声明目标」与「档案」逐项一致；任何不一致在任何文件落盘前硬失败。
    """

    target: str
    database: str
    schema: str
    key_type: str
    tables: tuple[str, ...]
    reference_tables: tuple[str, ...]
    role_table: str
    permission_table: str
    role_permission_table: str
    user_role_table: str
    role_permission_conflict_key: tuple[str, ...]
    forbidden_schemas: tuple[str, ...]


# 目标档案表：新增目标系统须先在此登记（含 schema 名、键类型、表集合），否则生成期硬失败。
TARGET_PROFILES: dict[str, TargetProfile] = {
    # B1 的真正落点：OpenLLM 自身权限表，位于目标库 public schema，主键 uuid。
    "openllm": TargetProfile(
        target="openllm",
        database="nuct",
        schema="public",
        key_type="uuid",
        tables=("roles", "permissions", "role_permissions", "user_roles"),
        reference_tables=("users",),
        role_table="roles",
        permission_table="permissions",
        role_permission_table="role_permissions",
        user_role_table="user_roles",
        role_permission_conflict_key=("role_id", "permission_id"),
        forbidden_schemas=("openbase", "platform"),
    ),
    # 对照项：OpenBase 自身表（bigint 主键、单列 code+module 模型）——**非 B1 落点**。
    "openbase": TargetProfile(
        target="openbase",
        database="nuct",
        schema="openbase",
        key_type="bigint",
        tables=("roles", "permissions", "role_permission", "user_role"),
        reference_tables=("users",),
        role_table="roles",
        permission_table="permissions",
        role_permission_table="role_permission",
        user_role_table="user_role",
        role_permission_conflict_key=("role_id", "permission_id"),
        forbidden_schemas=("public", "platform"),
    ),
}

# 角色元信息（对齐 config/role_tier_anchors.json 档位口径，并补齐目标表 NOT NULL 列）。
# 值为 (name, description, is_system, role_type, level, scope)。
ROLE_METADATA: dict[str, tuple[str, str, bool, str, int, str]] = {
    "admin": ("系统管理员", "内置管理员角色（持 * 通配）", True, "platform", 100, "platform"),
    "org_admin": (
        "组织管理员",
        "组织级管理角色（不含角色/权限管理，裁定 D2）",
        True,
        "org",
        50,
        "org",
    ),
    "user": ("普通用户", "标准业务用户角色（只读，裁定 D1）", True, "org", 10, "org"),
    "org_member": ("组织成员", "组织成员角色（只读，裁定 D1）", True, "org", 10, "org"),
    "viewer": ("只读用户", "只读访问角色（裁定 D1）", True, "org", 5, "org"),
}

# 差异报告的分段键定义（决定"同一项"的身份）。
_SECTION_KEYS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("roles", ("code",)),
    ("permissions", ("code",)),
    ("role_permissions", ("role_code", "permission_code")),
    ("user_role", ("username", "role_code")),
)

# 生成期落点护栏：从 SQL 中提取被 schema 限定的表引用（忽略注释行）。
_QUALIFIED_REF_RE = re.compile(r'"([A-Za-z_][A-Za-z0-9_]*)"\s*\.\s*"([A-Za-z_][A-Za-z0-9_]*)"')
_INSERT_RE = re.compile(
    r'INSERT\s+INTO\s+"([A-Za-z_][A-Za-z0-9_]*)"\s*\.\s*"([A-Za-z_][A-Za-z0-9_]*)"',
    re.IGNORECASE,
)


class SeedError(Exception):
    """播种校验失败（fail-fast；调用方据此报错退出）."""


# ---------------------------------------------------------------------------
# 输入 / 模型校验
# ---------------------------------------------------------------------------


def load_model(path: str | Path) -> dict[str, Any]:
    """读取权限模型 JSON（唯一输入）."""
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _action_of(code: str) -> str:
    """取权限码的 action 部分（``module:action`` → ``action``）."""
    return code.split(":", 1)[1] if ":" in code else code


def _resource_of(code: str) -> str:
    """取权限码的 resource_type 部分（``module:action`` → ``module``）."""
    return code.split(":", 1)[0] if ":" in code else code


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
    """三条业务强制校验，返回违规信息列表（空列表 = 通过）.

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
# 目标档案校验（生成期；任何不一致在任何文件落盘前硬失败）
# ---------------------------------------------------------------------------


def resolve_profile(target_system: str | None) -> TargetProfile:
    """按逻辑目标名解析目标档案；未登记即硬失败."""
    if not target_system:
        raise SeedError("权限模型缺少 target_system（无法解析目标档案）")
    profile = TARGET_PROFILES.get(target_system)
    if profile is None:
        raise SeedError(
            f"未知目标系统 '{target_system}'：档案表未登记（须先在 TARGET_PROFILES 登记）"
        )
    return profile


def validate_target_profile(
    profile: TargetProfile,
    *,
    declared_schema: str | None = None,
    declared_key_type: str | None = None,
    declared_tables: tuple[str, ...] | list[str] | None = None,
) -> list[str]:
    """校验「声明目标」与「档案」逐项一致，返回违规列表（空 = 通过）."""
    errors: list[str] = []
    if declared_schema is not None and declared_schema != profile.schema:
        errors.append(
            f"目标档案不符：声明 schema='{declared_schema}'，"
            f"档案 {profile.target}→schema='{profile.schema}'"
        )
    if declared_key_type is not None and declared_key_type != profile.key_type:
        errors.append(
            f"目标档案不符：声明键类型='{declared_key_type}'，"
            f"档案 {profile.target}→键类型='{profile.key_type}'"
        )
    if declared_tables is not None and tuple(declared_tables) != tuple(profile.tables):
        errors.append(
            f"目标档案不符：声明表集合={tuple(declared_tables)}，"
            f"档案 {profile.target}→表集合={profile.tables}"
        )
    return errors


def _strip_sql_comments(sql: str) -> str:
    """剥离 ``--`` 行注释，避免注释中的词误触落点护栏."""
    return "\n".join(
        line for line in sql.splitlines() if not line.lstrip().startswith("--")
    )


def assert_sql_target(sql: str, profile: TargetProfile) -> None:
    """生成期落点护栏：SQL 只允许落在档案 schema 与表集合内.

    声明 ``target=openllm`` 而 SQL 中出现 ``"openbase"``（或其它禁用 schema）即硬失败——
    令 v1.0.0 的落点缺陷不可能重犯。

    Raises:
        SeedError: 出现禁用 schema / 非档案 schema / 非档案表。
    """
    code = _strip_sql_comments(sql)
    errors: list[str] = []

    for forbidden in profile.forbidden_schemas:
        if f'"{forbidden}"' in code:
            errors.append(
                f"落点护栏：目标 {profile.target} 禁止写入 schema \"{forbidden}\"，"
                "但生成的 SQL 中出现该 schema"
            )

    allowed_tables = set(profile.tables) | set(profile.reference_tables)
    for schema, table in _QUALIFIED_REF_RE.findall(code):
        if schema != profile.schema:
            errors.append(
                f"落点护栏：目标 {profile.target} 只允许 schema \"{profile.schema}\"，"
                f"但出现 \"{schema}\".\"{table}\""
            )
        elif table not in allowed_tables:
            errors.append(
                f"落点护栏：目标 {profile.target} 表集合不含 \"{table}\""
                f"（出现 \"{schema}\".\"{table}\"）"
            )

    for schema, table in _INSERT_RE.findall(code):
        if schema != profile.schema or table not in set(profile.tables):
            errors.append(
                f"落点护栏：禁止 INSERT INTO \"{schema}\".\"{table}\""
                f"（目标 {profile.target} 仅允许 {profile.schema}.{profile.tables}）"
            )

    if errors:
        raise SeedError("；".join(errors))


# ---------------------------------------------------------------------------
# 稳定 UUID（uuid5：固定命名空间 + 稳定键）
# ---------------------------------------------------------------------------


def _uuid_key(*parts: str) -> str:
    return UUID_KEY_PREFIX + "/" + "/".join(parts)


def role_uuid(code: str) -> str:
    """角色行主键：uuid5(固定命名空间, 'role/{code}')."""
    return str(uuid.uuid5(UUID_NAMESPACE, _uuid_key("role", code)))


def permission_uuid(code: str) -> str:
    """权限行主键：uuid5(固定命名空间, 'permission/{code}')."""
    return str(uuid.uuid5(UUID_NAMESPACE, _uuid_key("permission", code)))


def role_permission_uuid(role_code: str, permission_code: str) -> str:
    """角色→权限行主键：uuid5(固定命名空间, 'role_permission/{role}/{permission}')."""
    return str(uuid.uuid5(UUID_NAMESPACE, _uuid_key("role_permission", role_code, permission_code)))


def user_role_uuid(username: str, role_code: str) -> str:
    """用户→角色行主键：uuid5(固定命名空间, 'user_role/{username}/{role}')."""
    return str(uuid.uuid5(UUID_NAMESPACE, _uuid_key("user_role", username, role_code)))


# ---------------------------------------------------------------------------
# 声明式清单（数据模型来源 = 目标系统自身表结构）
# ---------------------------------------------------------------------------


def build_manifest(
    model: dict[str, Any], *, source_model: str = "", profile: TargetProfile
) -> dict[str, Any]:
    """把权限模型转为声明式种子清单（校验失败即抛 :class:`SeedError`）.

    清单字段与**目标表列**一一对应（roles 补 role_type/level/scope；permissions 补
    resource_type/action/scope）——即数据模型来源已由 OpenBase 表结构改为目标系统表结构。
    """
    errors = validate_model(model)
    if errors:
        raise SeedError("；".join(errors))

    role_to_permissions = model.get("role_to_permissions") or {}

    roles: list[dict[str, Any]] = []
    for code in sorted(role_to_permissions):
        name, description, is_system, role_type, level, scope = ROLE_METADATA.get(
            code, (code, None, False, "custom", 0, "own")
        )
        roles.append(
            {
                "id": role_uuid(code),
                "code": code,
                "name": name,
                "description": description,
                "role_type": role_type,
                "level": level,
                "scope": scope,
                "is_system": is_system,
            }
        )

    permissions: list[dict[str, Any]] = [
        {
            "id": permission_uuid(WILDCARD),
            "code": WILDCARD,
            "name": "全部权限",
            "resource_type": WILDCARD,
            "action": WILDCARD,
            "scope": PERMISSION_SCOPE,
            "is_system": True,
        }
    ]
    seen_codes = {WILDCARD}
    for _module_name, module in sorted((model.get("modules") or {}).items()):
        for code in module.get("codes") or []:
            if code in seen_codes:
                continue
            seen_codes.add(code)
            resource_type = _resource_of(code)
            action = _action_of(code)
            permissions.append(
                {
                    "id": permission_uuid(code),
                    "code": code,
                    "name": f"{resource_type}·{action}",
                    "resource_type": resource_type,
                    "action": action,
                    "scope": PERMISSION_SCOPE,
                    "is_system": True,
                }
            )

    role_permissions: list[dict[str, Any]] = []
    for role in sorted(role_to_permissions):
        for code in role_to_permissions[role] or []:
            role_permissions.append(
                {
                    "id": role_permission_uuid(role, code),
                    "role_code": role,
                    "permission_code": code,
                }
            )
    role_permissions.sort(key=lambda item: (item["role_code"], item["permission_code"]))

    return {
        "schema_version": SCHEMA_VERSION,
        "artifact": "rbac_seed_manifest",
        "tool": TOOL,
        "target_system": profile.target,
        "target_database": profile.database,
        "target_schema": profile.schema,
        "target_key_type": profile.key_type,
        "target_tables": list(profile.tables),
        "target_reference_tables": list(profile.reference_tables),
        "role_permission_conflict_key": list(profile.role_permission_conflict_key),
        "model_artifact": model.get("artifact"),
        "source_model": str(source_model),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "dry-run",
        "applied": False,
        "dialect": "postgresql",
        "schema": profile.schema,
        "note": (
            "声明式种子清单：字段对齐目标系统（OpenLLM）自身表结构。执行分两步——先由共享基础设施"
            "（局域网唯一共享库）的受控流程执行前置结构变更 rbac_seed_ddl.sql，再由目标仓执行纯 DML "
            "rbac_seed.sql；本脚本不连库、不写库（默认 dry-run）。"
        ),
        "roles": roles,
        "permissions": permissions,
        "role_permissions": role_permissions,
        "user_role": [],
        "user_role_note": (
            "用户→角色绑定为环境相关（依赖目标库既有 users 行）：本脚本仅产出声明式清单，"
            "默认不含绑定；如需绑定，由目标仓按环境补充（如内置 admin 用户 → admin 角色）。"
        ),
    }


# ---------------------------------------------------------------------------
# 幂等 SQL 渲染（PostgreSQL 方言；落点 = 目标档案 schema）
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


def _qualified(profile: TargetProfile, table: str) -> str:
    return f'"{profile.schema}"."{table}"'


def render_ddl(profile: TargetProfile) -> str:
    """渲染**前置结构变更** DDL（独立于数据播种交付；由目标仓经结构变更通道执行）.

    仅为 ``role_permissions`` 的幂等冲突键 ``(role_id, permission_id)`` 提供唯一索引——
    该索引是 ``rbac_seed.sql`` 中 ``ON CONFLICT (role_id, permission_id)`` 的前提。
    本条 DDL 幂等（``IF NOT EXISTS``），但**须先于 DML 执行**，执行前需满足：
    目标库无重复 ``(role_id, permission_id)`` 行、执行账号具备 ``CREATE INDEX`` 权限。
    """
    index_columns = ", ".join(f'"{col}"' for col in profile.role_permission_conflict_key)
    conflict_key = ", ".join(profile.role_permission_conflict_key)
    role_permission_table = _qualified(profile, profile.role_permission_table)
    return "\n".join(
        [
            f"-- rbac_seed_ddl — 由 {TOOL} 生成（前置结构变更；独立于数据播种执行）",
            f"-- 目标系统（逻辑）：{profile.target}；目标库：{profile.database}；"
            f"schema：{profile.schema}",
            f"-- 用途：为 {profile.schema}.{profile.role_permission_table} 的幂等冲突键 "
            f"({conflict_key}) 建唯一索引（rbac_seed.sql 的 ON CONFLICT 依赖之）。",
            "-- 执行责任：**由共享基础设施（局域网唯一共享库）的受控结构变更流程（迁移 / DBA）执行**；"
            "本脚本不连库、不写库。",
            "-- 执行前置（缺一不可）：",
            "--   1) 只读预检重复行必须为 0（非 0 须先由目标仓消重）：",
            f"--      SELECT role_id, permission_id, COUNT(*) FROM {role_permission_table}",
            "--      GROUP BY role_id, permission_id HAVING COUNT(*) > 1;",
            "--   2) 执行账号须具备 CREATE INDEX 权限（否则由其 DBA 代执行本条）。",
            f'-- 回滚：DROP INDEX IF EXISTS "{ROLE_PERMISSION_UNIQUE_INDEX}";',
            f"CREATE UNIQUE INDEX IF NOT EXISTS {ROLE_PERMISSION_UNIQUE_INDEX} "
            f"ON {role_permission_table} ({index_columns});",
            "",
        ]
    )


def render_sql(manifest: dict[str, Any], *, profile: TargetProfile) -> str:
    """渲染**纯 DML** 幂等 SQL（PostgreSQL；重复执行结果一致；落点 = 目标档案）.

    前置结构变更（唯一索引 DDL）已拆分为独立交付 ``rbac_seed_ddl.sql``，本文件不再含 DDL。
    """
    roles = manifest["roles"]
    permissions = manifest["permissions"]
    role_permissions = manifest["role_permissions"]
    user_roles = manifest.get("user_role") or []
    conflict_key = ", ".join(profile.role_permission_conflict_key)

    lines: list[str] = [
        f"-- {manifest['artifact']} — 由 {TOOL} 生成（纯 DML；幂等，可重复执行）",
        f"-- 目标系统（逻辑）：{profile.target}；目标库：{profile.database}；schema：{profile.schema}；"
        f"主键类型：{profile.key_type}",
        f"-- 目标档案：表集合 {list(profile.tables)}（引用表 {list(profile.reference_tables)}）；"
        f"禁用 schema {list(profile.forbidden_schemas)}",
        f"-- 方言：PostgreSQL；生成时间：{manifest['generated_at']}",
        f"-- 源模型：{manifest.get('source_model')}",
        f"-- 计数：roles={len(roles)} permissions={len(permissions)} "
        f"role_permissions={len(role_permissions)} user_roles={len(user_roles)}",
        "-- 幂等语义：INSERT ... ON CONFLICT DO NOTHING",
        f"--   · roles/permissions 冲突键 = (code)；"
        f"role_permissions 冲突键 = ({conflict_key})",
        "--   · 行主键 id 由 uuid5(固定命名空间 + 稳定键) 生成 → 重跑结果逐字节一致；",
        f"--   · 前置结构变更（唯一索引）已拆分为独立交付 {DDL_FILENAME}，须先行执行；"
        "本文件为纯 DML。",
        "-- 执行责任：**由目标仓（OpenLLM）在共享基础设施（局域网唯一共享库）的受控流程内执行**；"
        "本脚本不连库、不写库（默认 dry-run）。",
        "BEGIN;",
        "",
        "-- 1) 角色（roles）",
    ]
    for role in roles:
        lines.append(
            f"INSERT INTO {_qualified(profile, profile.role_table)} "
            "(id, code, name, description, role_type, level, scope, is_active, is_system, "
            "created_at, updated_at) "
            f"VALUES ({_sql_literal(role['id'])}, {_sql_literal(role['code'])}, "
            f"{_sql_literal(role['name'])}, {_sql_literal(role.get('description'))}, "
            f"{_sql_literal(role['role_type'])}, {_sql_literal(role['level'])}, "
            f"{_sql_literal(role['scope'])}, true, {_sql_literal(role['is_system'])}, "
            "now(), now()) "
            "ON CONFLICT (code) DO NOTHING;"
        )

    lines.extend(["", "-- 2) 权限点（permissions；code 与 resource_type/action 四字段并存）"])
    for permission in permissions:
        lines.append(
            f"INSERT INTO {_qualified(profile, profile.permission_table)} "
            "(id, code, name, description, resource_type, action, scope, is_active, is_system, "
            "created_at, updated_at) "
            f"VALUES ({_sql_literal(permission['id'])}, {_sql_literal(permission['code'])}, "
            f"{_sql_literal(permission['name'])}, {_sql_literal(permission.get('description'))}, "
            f"{_sql_literal(permission['resource_type'])}, {_sql_literal(permission['action'])}, "
            f"{_sql_literal(permission['scope'])}, true, "
            f"{_sql_literal(permission['is_system'])}, now(), now()) "
            "ON CONFLICT (code) DO NOTHING;"
        )

    lines.extend(
        [
            "",
            "-- 3) 角色→权限（role_permissions）",
            f"--    · 冲突键 = ({conflict_key})；role_id/permission_id 按 code 解析（兼容目标库既有行）",
        ]
    )
    for binding in role_permissions:
        lines.append(
            f"INSERT INTO {_qualified(profile, profile.role_permission_table)} "
            "(id, role_id, permission_id, constraints, is_active, created_at) "
            f"SELECT {_sql_literal(binding['id'])}::uuid, r.id, p.id, '{{}}'::jsonb, true, now() "
            f"FROM {_qualified(profile, profile.role_table)} AS r "
            f"JOIN {_qualified(profile, profile.permission_table)} AS p "
            f"ON p.code = {_sql_literal(binding['permission_code'])} "
            f"WHERE r.code = {_sql_literal(binding['role_code'])} "
            f"ON CONFLICT ({conflict_key}) DO NOTHING;"
        )

    lines.extend(["", "-- 4) 用户→角色（user_roles；绑定意图，默认空）"])
    if not user_roles:
        lines.append("-- （无绑定意图：由目标仓按环境补充）")
    for binding in user_roles:
        lines.append(
            f"INSERT INTO {_qualified(profile, profile.user_role_table)} "
            "(id, user_id, role_id, is_active, created_at) "
            f"SELECT {_sql_literal(binding['id'])}::uuid, u.id, r.id, true, now() "
            f"FROM {_qualified(profile, 'users')} AS u "
            f"JOIN {_qualified(profile, profile.role_table)} AS r "
            f"ON r.code = {_sql_literal(binding['role_code'])} "
            f"WHERE u.username = {_sql_literal(binding['username'])} "
            "ON CONFLICT (id) DO NOTHING;"
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
    schema: str | None = None,
    target_system: str | None = None,
) -> dict[str, Any]:
    """读取模型 → 档案校验 → 落点护栏 → 产出清单/前置DDL/SQL/差异报告（全部落盘；不写库）.

    所有校验（含目标档案与落点护栏）在任何文件落盘之前完成；任一项失败即 raise。

    Returns:
        ``{"manifest","ddl","sql","diff","paths"}``。

    Raises:
        SeedError: 输入缺失 / 校验失败 / 目标档案不符 / 落点护栏触发（均不落盘）。
    """
    model_file = Path(model_path)
    if not model_file.exists():
        raise SeedError(f"权限模型不存在：{model_file}")

    model = load_model(model_file)
    profile = resolve_profile(target_system or model.get("target_system"))

    declared_schema = schema if schema is not None else model.get("target_schema")
    declared_key_type = model.get("target_key_type")
    declared_tables = model.get("target_tables")
    errors = validate_target_profile(
        profile,
        declared_schema=declared_schema,
        declared_key_type=declared_key_type,
        declared_tables=declared_tables,
    )
    if errors:
        raise SeedError("；".join(errors))

    manifest = build_manifest(model, source_model=str(model_file), profile=profile)
    ddl = render_ddl(profile)
    sql = render_sql(manifest, profile=profile)
    assert_sql_target(ddl, profile)
    assert_sql_target(sql, profile)

    out = Path(out_dir)
    current = _load_current(current_path, out)
    diff = diff_manifests(current, manifest) if current is not None else None

    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / MANIFEST_FILENAME
    ddl_path = out / DDL_FILENAME
    sql_path = out / SQL_FILENAME
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    ddl_path.write_text(ddl, encoding="utf-8")
    sql_path.write_text(sql, encoding="utf-8")

    paths: dict[str, str] = {
        "manifest": str(manifest_path),
        "ddl": str(ddl_path),
        "sql": str(sql_path),
    }
    if diff is not None:
        diff_path = out / DIFF_FILENAME
        diff_path.write_text(
            json.dumps(diff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        paths["diff"] = str(diff_path)

    return {"manifest": manifest, "ddl": ddl, "sql": sql, "diff": diff, "paths": paths}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "B1 权限播种：把 config/rbac_permission_model.json 转为声明式种子清单 + 幂等 SQL + "
            "差异报告（默认 dry-run；不连库、不写库；落点 = 目标系统自身表结构）"
        )
    )
    parser.add_argument(
        "--model", default=str(DEFAULT_MODEL), help="权限模型 JSON（默认 config/rbac_permission_model.json）"
    )
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="产物输出目录（默认 doc/design/generated/）")
    parser.add_argument("--current", default=None, help="既有种子清单 JSON（可选；用于差异报告）")
    parser.add_argument(
        "--target", default=None, help="覆盖逻辑目标（默认取模型 target_system；须已登记在目标档案表）"
    )
    parser.add_argument(
        "--schema", default=None, help="覆盖目标 schema（须与目标档案一致；不一致即硬失败）"
    )
    parser.add_argument("--json", action="store_true", help="追加打印清单 JSON 到 stdout")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 入口；返回统一退出码（0=PASS / 1=FAIL）."""
    args = _build_parser().parse_args(argv)
    try:
        result = run(
            args.model,
            args.out_dir,
            current_path=args.current,
            schema=args.schema,
            target_system=args.target,
        )
    except SeedError as exc:
        print(f"[ERROR] 校验/输入失败：{exc}", file=sys.stderr)
        return EXIT_FAIL

    manifest = result["manifest"]
    diff = result["diff"]
    print(
        f"[{TOOL}] mode=dry-run applied=False target={manifest.get('target_system')} "
        f"schema={manifest.get('target_schema')} "
        f"roles={len(manifest['roles'])} permissions={len(manifest['permissions'])} "
        f"role_permissions={len(manifest['role_permissions'])} user_role={len(manifest['user_role'])}"
    )
    print(f"  清单：{result['paths']['manifest']}")
    print(f"  DDL ：{result['paths']['ddl']}（前置结构变更；由目标仓结构变更通道先执行）")
    print(f"  SQL ：{result['paths']['sql']}（纯 DML，幂等；由目标仓执行）")
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
