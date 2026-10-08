"""A 批 A3/A4 登记制品护栏：角色档位锚点表 + 统一错误码映射表.

两件制品是跨仓消费的**单一事实源**（四仓对齐的判据），故必须可机器校验：
结构合法、必填字段齐备、无重复、角色覆盖完整、层枚举受限。

制品位置：`config/role_tier_anchors.json`、`config/error_code_map.json`
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from openbase.modules.protocol_headers.constants import ALLOWED_OPENBASE_ROLE_CODES

ROOT = Path(__file__).resolve().parents[1]
ROLE_ANCHORS = ROOT / "config" / "role_tier_anchors.json"
ERROR_CODE_MAP = ROOT / "config" / "error_code_map.json"

# OpenBase 角色种子码（openbase/core/db/init.py）——与 ALLOWED_OPENBASE_ROLE_CODES 取并集
SEEDED_ROLE_CODES = {"admin", "org_admin", "user", "viewer"}

TARGET_KEYS = {"openbase", "openllm", "openrag", "openmemory", "dps"}


def _load(path: Path) -> dict:
    assert path.exists(), f"缺少制品：{path}"
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# A3 角色档位锚点表
# ---------------------------------------------------------------------------


def test_role_tier_anchors_structure() -> None:
    """结构：schema_version / tiers.order / anchors / unknown_code_policy 齐备."""
    doc = _load(ROLE_ANCHORS)

    assert doc["schema_version"] == 1
    assert doc["artifact"] == "role_tier_anchors"
    assert set(doc["tiers"]["order"]) == {"readonly", "readwrite", "manage"}
    assert doc["tiers"]["order"] == {"readonly": 1, "readwrite": 2, "manage": 3}
    assert "fail-closed" in doc["unknown_code_policy"]


def test_role_tier_anchors_cover_all_openbase_roles() -> None:
    """锚点须覆盖 OpenBase 全部角色码（种子码 ∪ 出站允许码集合）."""
    doc = _load(ROLE_ANCHORS)
    anchors = doc["anchors"]

    missing = (SEEDED_ROLE_CODES | set(ALLOWED_OPENBASE_ROLE_CODES)) - set(anchors)
    assert not missing, f"锚点表缺少角色码：{sorted(missing)}"


def test_role_tier_anchors_values_are_declared_tiers() -> None:
    """锚点取值须为已声明档位（防拼写漂移后目标域解析失败）."""
    doc = _load(ROLE_ANCHORS)
    declared = set(doc["tiers"]["order"])

    invalid = {role: tier for role, tier in doc["anchors"].items() if tier not in declared}
    assert not invalid, f"锚点取值非法：{invalid}"


def test_role_tier_anchors_admin_is_manage() -> None:
    """管理角色须映射到最高档（全权）."""
    doc = _load(ROLE_ANCHORS)

    assert doc["anchors"]["admin"] == "manage"


# ---------------------------------------------------------------------------
# A4 统一错误码映射表
# ---------------------------------------------------------------------------


def test_error_code_map_structure() -> None:
    """结构：schema_version / map / layers 齐备，且层枚举受限."""
    doc = _load(ERROR_CODE_MAP)

    assert doc["schema_version"] == 1
    assert doc["artifact"] == "error_code_map"
    assert isinstance(doc["map"], list) and doc["map"], "映射表不得为空"
    assert set(doc["layers"]) == {"gateway", "upstream", "network"}


def test_error_code_map_entries_are_complete_and_unique() -> None:
    """每条须含 unified/layer/http/meaning/targets，且统一码不重复."""
    doc = _load(ERROR_CODE_MAP)
    allowed_layers = set(doc["layers"])
    seen: set[str] = set()

    for entry in doc["map"]:
        for key in ("unified", "layer", "http", "meaning", "targets"):
            assert key in entry, f"条目缺少字段 {key}：{entry}"
        assert entry["layer"] in allowed_layers, f"层非法：{entry['layer']}"
        assert isinstance(entry["http"], int), f"http 须为整数：{entry}"
        assert entry["unified"] not in seen, f"统一码重复：{entry['unified']}"
        seen.add(entry["unified"])
        assert set(entry["targets"]) == TARGET_KEYS, (
            f"目标键须完整覆盖五系统：{entry['unified']} -> {sorted(entry['targets'])}"
        )


def test_error_code_map_covers_key_cross_system_codes() -> None:
    """须覆盖已知跨系统核心码（本轮实测出现过的族）."""
    doc = _load(ERROR_CODE_MAP)
    unified = {entry["unified"] for entry in doc["map"]}

    required = {
        "PERM_SERVICE_KEY_WRITE_DENIED",
        "PERM_UNTRUSTED_IDENTITY_HEADER",
        "ROLE_UNMAPPED",
        "PERM_FORBIDDEN",
        "BIZ_RESERVED_TENANT_CODE_COLLISION",
        "AUTH_PRINCIPAL_DISABLED",
        # C1 批次新增（B1/C1-b/C1-c 实测落点）
        "AUTH_TENANT_ID_MISSING",
        "BIZ_TENANT_NOT_FOUND",
    }
    missing = required - unified
    assert not missing, f"映射表缺少核心码：{sorted(missing)}"


def test_error_code_map_attribution_rules_present() -> None:
    """须给出归因规则（网关优先 / 上游优先于网关 5xx / 网络层）."""
    doc = _load(ERROR_CODE_MAP)

    rules = " ".join(doc["attribution_rules"])
    assert "gateway" in rules
    assert "upstream" in rules
    assert "network" in rules


@pytest.mark.parametrize("artifact", [ROLE_ANCHORS, ERROR_CODE_MAP])
def test_artifacts_are_valid_utf8_json(artifact: Path) -> None:
    """制品须为合法 UTF-8 JSON（中文可读，禁乱码）."""
    text = artifact.read_text(encoding="utf-8")

    assert "\\u" not in text, "出现转义中文，请以 UTF-8 原样保存"
    json.loads(text)
