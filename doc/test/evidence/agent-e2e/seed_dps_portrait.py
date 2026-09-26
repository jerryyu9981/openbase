"""DPS 联调前置种子：为流程主体播种**角色绑定**与**画像行**（幂等）。

**背景（`CR-148-029`，实测 2026-09-26）**：DPS 侧不提供画像 upsert
（`PUT /api/v2/portrait/{person_id}` → 404「画像不存在」；
`POST /api/v2/portrait/calculate` → 404「人员不存在」），且**未绑定主体访问画像由权限
中间件 fail-closed 返回 403**（DPS `seed-shared-infra.py` RA-04：生产绑定必须经总线
显式写入，禁止隐式降级）→ 流程主体必须先具备：① `platform.user_roles` 角色绑定；
② `platform.profile` 画像行。否则画像段按设计**降级跳过**（`segment_tokens.profile=0`）。

本脚本按 DPS 官方共享种子脚本 `DPS/scripts/seed-shared-infra.py` 的**同一表结构、
同一幂等语义**写入（`ON CONFLICT DO NOTHING`），使端到端核验可复跑、不依赖人工准备。

**主体标识口径**：本仓出站 `X-User-ID` 与 DPS `person_id` 均取编排资源键
`{tenant_code}_{openllm_api_key_user_id}`（实测 DPS 访问日志：
`person_id=tenant-1_179fc89c-…`、`operator_id=tenant-1_179fc89c-…`）。

用法::

    # 主体与画像首次准备（幂等，可重复执行）
    python seed_dps_portrait.py --subject-id tenant-1_179fc89c-c76b-47e7-a0b1-9659d03de663

退出码：0=已就绪 / 1=失败
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# 与 DPS 种子脚本保持一致的固定 UUID / 码值（不得本地改写）
ORG_ID = "10000000-0000-0000-0000-000000000001"
TENANT_ID = "20000000-0000-0000-0000-000000000001"
ORG_CODE = "dps-org-001"
TENANT_CODE = "dps-tenant-001"

# 默认联调主体（本仓 OpenLLM 网关 API Key 用户 → 编排资源键；实测自 DPS 访问日志）
DEFAULT_SUBJECT_ID = "tenant-1_179fc89c-c76b-47e7-a0b1-9659d03de663"
DEFAULT_ROLE = "super_admin"
# 画像模板码：对齐本环境既有样例行（`pg_indexes` 唯一键含 template_code）
TEMPLATE_CODE = "dps-correction-v1"

DEFAULT_ATTRS = {
    "tone": "formal",
    "preferences": "结构化、先给结论、可落地",
    "industry": "知识管理",
    "seed": "agent-context-e2e",
}

DPS_ENV_CANDIDATES = (
    r"D:\Trae CN\myproject\Dev\DPS\.env.shared-infra",
    r"D:\Trae CN\myproject\Dev\OpenBase\.env.shared-infra",
)


def load_pg_url() -> str:
    """读取共享 PG 连接串（优先 DPS 仓的 `.env.shared-infra`，回退本仓）"""
    for candidate in DPS_ENV_CANDIDATES:
        path = Path(candidate)
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("POSTGRES_URL="):
                return line.split("=", 1)[1].strip()
    raise RuntimeError("未找到 POSTGRES_URL（DPS/.env.shared-infra 或 OpenBase/.env.shared-infra）")


def seed(
    subject_id: str,
    role: str = DEFAULT_ROLE,
    name: str = "联调主体",
    bind_role: bool = True,
) -> dict[str, str]:
    """幂等播种「角色绑定 + 画像行」（返回各行结果 inserted/exists/missing_role/skipped）

    幂等实现采用**先查后写**（而非 `ON CONFLICT`）：本环境 `platform.profile` 的唯一键为
    `(person_id, tenant_id, template_code)`（实测自 `pg_indexes`），与官方种子脚本注释所述
    的 `(person_id, tenant_id)` 不一致 —— 以唯一约束为准的 `ON CONFLICT` 写法会因
    无匹配仲裁索引而报 `InvalidColumnReference`。故统一以**显式存在性判定**保证幂等，
    不依赖约束形态（同时写入环境既有 `template_code` 约定，避免与样例行不齐）。

    Args:
        subject_id: 主体标识（本仓出站 `X-User-ID`；亦为 DPS `person_id`）
        role: 绑定角色（`bind_role=True` 时生效）
        name: 画像显示名
        bind_role: 是否绑定角色（`:700`）；按 `person_id` 播种画像时为 False
            （画像查询主体为**外部平台身份**，鉴权主体仍为编排资源键）

    Returns:
        dict[str, str]: 各行结果（role_binding / profile）
    """
    import psycopg2

    outcome: dict[str, str] = {}
    with psycopg2.connect(load_pg_url(), connect_timeout=10) as conn:
        with conn.cursor() as cur:
            # ① 角色绑定（未绑定主体 → 权限中间件 fail-closed 403）
            if not bind_role:
                outcome["role_binding"] = "skipped"
            else:
                cur.execute(
                    "SELECT 1 FROM platform.user_roles ur JOIN platform.roles r "
                    "ON r.id = ur.role_id WHERE ur.user_id = %s AND r.name = %s",
                    (subject_id, role),
                )
                if cur.fetchone():
                    outcome["role_binding"] = "exists"
                else:
                    cur.execute(
                        "INSERT INTO platform.user_roles (user_id, role_id) "
                        "SELECT %s, id FROM platform.roles WHERE name = %s",
                        (subject_id, role),
                    )
                    outcome["role_binding"] = (
                        "inserted" if cur.rowcount == 1 else "missing_role"
                    )

            # ② 画像行（唯一键 (person_id, tenant_id, template_code)）
            cur.execute(
                "SELECT 1 FROM platform.profile "
                "WHERE person_id = %s AND tenant_id = %s::uuid AND template_code = %s",
                (subject_id, TENANT_ID, TEMPLATE_CODE),
            )
            if cur.fetchone():
                outcome["profile"] = "exists"
            else:
                cur.execute(
                    "INSERT INTO platform.profile "
                    "(person_id, org_id, tenant_id, name, basic_score, behavioral_score, "
                    " psychological_score, social_score, correction_score, risk_score, "
                    " overall_score, attributes_json, version, status, template_code) "
                    "VALUES (%s, %s::uuid, %s::uuid, %s, %s, %s, %s, %s, %s, %s, %s, "
                    "        %s::jsonb, 1, 'active', %s)",
                    (
                        subject_id,
                        ORG_ID,
                        TENANT_ID,
                        name,
                        72.5,
                        68.0,
                        60.0,
                        70.0,
                        55.0,
                        78.0,
                        36.6,
                        json.dumps(DEFAULT_ATTRS, ensure_ascii=False),
                        TEMPLATE_CODE,
                    ),
                )
                outcome["profile"] = "inserted" if cur.rowcount == 1 else "failed"
    return outcome


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--subject-id",
        default=DEFAULT_SUBJECT_ID,
        help="编排资源键（本仓出站 X-User-ID / DPS person_id）",
    )
    parser.add_argument("--role", default=DEFAULT_ROLE, help="绑定角色（默认 super_admin）")
    parser.add_argument("--name", default="联调主体")
    parser.add_argument(
        "--profile-only",
        action="store_true",
        help="仅播种画像行（不绑定角色；用于按外部平台身份 seed person_id）",
    )
    args = parser.parse_args()
    try:
        outcome = seed(
            args.subject_id, args.role, args.name, bind_role=not args.profile_only
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] DPS 前置种子失败: {type(exc).__name__}: {exc}")
        return 1
    print(
        f"[OK] DPS 前置已就绪 subject_id={args.subject_id} "
        f"role={args.role}({outcome['role_binding']}) "
        f"profile={outcome['profile']} org={ORG_CODE} tenant={TENANT_CODE}"
    )
    return 0 if outcome["role_binding"] != "missing_role" else 1


if __name__ == "__main__":
    sys.exit(main())
