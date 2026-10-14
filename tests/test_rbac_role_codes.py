"""角色码集合一致性测试（2026-10-14，MTAUTH 走查 F2 缺陷回归）.

锁定「角色码单一事实源」：`config/role_tier_anchors.json` 的
`canonical_role_codes.set`（五码）必须与
① 角色表种子 `openbase.core.db.init.SEEDED_ROLE_CODES`、
② 用户分配受控枚举 `openbase.modules.users.ALLOWED_ROLES`
逐一致，杜绝走查发现的「org_member 未播种 → 404 BIZ_404」与
「user 不可分配 → 400 PARAM_INVALID」两类漂移。
"""

from __future__ import annotations

import json
from pathlib import Path

from openbase.core.db.init import SEEDED_ROLE_CODES
from openbase.modules.users import ALLOWED_ROLES

_CONFIG = Path(__file__).resolve().parents[1] / "config" / "role_tier_anchors.json"


def _canonical_codes() -> set[str]:
    with _CONFIG.open(encoding="utf-8") as fh:
        payload = json.load(fh)
    return set(payload["canonical_role_codes"]["set"])


def test_canonical_anchors_cover_five_role_codes() -> None:
    """锚点表本身为五码集合（回归护栏：锚点被误删码即失败）."""
    assert _canonical_codes() == {"admin", "org_admin", "org_member", "user", "viewer"}


def test_seeded_role_codes_match_canonical() -> None:
    """角色表种子集合 == 锚点 canonical 集合（防「未播种某码」）."""
    seeded = [code for code, _name, _desc in SEEDED_ROLE_CODES]
    assert len(seeded) == len(set(seeded)), f"角色种子存在重复码：{seeded}"
    assert set(seeded) == _canonical_codes(), f"种子={sorted(seeded)} 与锚点不一致"


def test_assignable_roles_match_canonical() -> None:
    """可分配枚举 == 锚点 canonical 集合（防「已播种但不可分配 / 可分配但未播种」）."""
    assert set(ALLOWED_ROLES) == _canonical_codes(), f"ALLOWED_ROLES={sorted(ALLOWED_ROLES)} 与锚点不一致"


def test_every_assignable_role_has_seed() -> None:
    """每个可分配角色码都有对应角色种子（防止分配时 BIZ_404 role not found）."""
    seeded = {code for code, _name, _desc in SEEDED_ROLE_CODES}
    missing = set(ALLOWED_ROLES) - seeded
    assert not missing, f"可分配但未播种：{sorted(missing)}"
