"""B1 影子期观测聚合脚本测试（TDD：先 RED，后实现）.

被测：``scripts/rbac_shadow_observe.py``（交付 B，只读）

职责：把影子期 ``rbac_decision=would_deny`` 日志（JSON Lines）聚合为
「端点 × 角色 × 权限码」清单 + 计数 + 代表性 request_id 样例 + 消化率
（相对 ``role_to_permissions`` 判定调用方按模型是否本应被允许）。

TDD 用例（需求 §交付B.4）：
1. 正常聚合计数（``test_aggregate_counts_by_endpoint_role_permission``）；
2. 消化率计算（``test_digestion_rate_and_model_allow_split``）；
3. 脏行/缺字段容错（``test_tolerates_dirty_lines_and_missing_fields``）；
4. --json 落盘证据（``test_json_evidence_written_to_file``）；
5. 内置样例 fixture 可被消费（``test_builtin_fixture_is_consumable``）。
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "rbac_shadow_observe.py"
MODEL_PATH = ROOT / "config" / "rbac_permission_model.json"
FIXTURE = ROOT / "tests" / "fixtures" / "rbac_shadow_sample.jsonl"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("rbac_shadow_observe", SCRIPT)
    assert spec and spec.loader, f"无法加载观测脚本: {SCRIPT}"
    module = importlib.util.module_from_spec(spec)
    sys.modules["rbac_shadow_observe"] = module
    spec.loader.exec_module(module)
    return module


def _would_deny(
    *,
    request_id: str,
    endpoint: str,
    role: str,
    permission: str,
    subject: str = "alice",
    method: str = "POST",
) -> str:
    return json.dumps(
        {
            "ts": "2026-10-08T02:00:00.000+00:00",
            "level": "WARNING",
            "service": "openllm",
            "message": "rbac.permission_check",
            "rbac_decision": "would_deny",
            "method": method,
            "endpoint": endpoint,
            "role": role,
            "subject": subject,
            "required_permission": permission,
            "request_id": request_id,
        },
        ensure_ascii=False,
    )


def _write_sample(tmp_path: Path) -> Path:
    """内置样例日志：7 条 would_deny + 1 条 allow + 1 条脏行。

    - (users, org_admin, user:write) × 2  → 模型本应允许（org_admin 有 user:write）
    - (users, viewer, user:write) × 1     → 模型本应拒绝（viewer 只读）
    - (kb, user, knowledge_base:write) × 2 → 模型本应拒绝（user 只读）
    - (users, unknown_role, user:write) × 1 → 未归类调用方
    - 缺字段行（仅 rbac_decision + request_id）→ 端点/角色缺省为 <unknown>
    """
    lines = [
        _would_deny(
            request_id="req-1",
            endpoint="/api/v1/users",
            role="org_admin",
            permission="user:write",
        ),
        _would_deny(
            request_id="req-2",
            endpoint="/api/v1/users",
            role="org_admin",
            permission="user:write",
        ),
        _would_deny(
            request_id="req-3",
            endpoint="/api/v1/users",
            role="viewer",
            permission="user:write",
        ),
        _would_deny(
            request_id="req-4",
            endpoint="/api/v1/knowledge-bases",
            role="user",
            permission="knowledge_base:write",
        ),
        _would_deny(
            request_id="req-5",
            endpoint="/api/v1/knowledge-bases",
            role="user",
            permission="knowledge_base:write",
        ),
        _would_deny(
            request_id="req-6",
            endpoint="/api/v1/users",
            role="unknown_role",
            permission="user:write",
        ),
        json.dumps(
            {
                "ts": "2026-10-08T02:00:06.000+00:00",
                "level": "INFO",
                "message": "rbac.permission_check",
                "rbac_decision": "allow",
                "endpoint": "/api/v1/users",
                "role": "org_admin",
                "request_id": "req-7",
            },
            ensure_ascii=False,
        ),
        json.dumps(
            {"ts": "2026-10-08T02:00:07.000+00:00", "rbac_decision": "would_deny", "request_id": "req-8"},
            ensure_ascii=False,
        ),
        "this-is-not-json",
    ]
    path = tmp_path / "openllm-shadow.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# ① 正常聚合计数
# ---------------------------------------------------------------------------


def test_aggregate_counts_by_endpoint_role_permission(tmp_path: Path) -> None:
    """按「端点 × 角色 × 权限码」聚合计数。"""
    module = _load_script()
    log_path = _write_sample(tmp_path)

    report = module.observe(log_path, MODEL_PATH)

    # 7 条 would_deny（allow 行不计、脏行跳过）
    assert report["totals"]["would_deny"] == 7
    assert report["skipped_lines"] == 1

    by_key = {
        (group["endpoint"], group["role"], group["permission"]): group
        for group in report["groups"]
    }
    assert by_key[("/api/v1/users", "org_admin", "user:write")]["count"] == 2
    assert by_key[("/api/v1/users", "viewer", "user:write")]["count"] == 1
    assert by_key[("/api/v1/knowledge-bases", "user", "knowledge_base:write")]["count"] == 2
    assert by_key[("/api/v1/users", "unknown_role", "user:write")]["count"] == 1

    # 代表性 request_id 样例
    assert set(by_key[("/api/v1/users", "org_admin", "user:write")]["samples"]) == {"req-1", "req-2"}


# ---------------------------------------------------------------------------
# ② 消化率计算
# ---------------------------------------------------------------------------


def test_digestion_rate_and_model_allow_split(tmp_path: Path) -> None:
    """消化率 = 可归类事件 / 总事件；并区分「本应允许 / 本应拒绝」。"""
    module = _load_script()
    log_path = _write_sample(tmp_path)

    report = module.observe(log_path, MODEL_PATH)
    digestion = report["digestion"]

    # 已知角色事件：req-1/2（org_admin）、req-3（viewer）、req-4/5（user）= 5
    assert digestion["classified_events"] == 5
    # 未归类：req-6（unknown_role）+ 缺字段行（<unknown>）= 2
    assert digestion["unclassified_events"] == 2
    assert digestion["digestion_rate"] == round(5 / 7, 4)

    # 本应允许：仅 org_admin × user:write = 2
    assert digestion["model_allows_events"] == 2
    assert digestion["model_denies_events"] == 3

    assert report["unclassified_roles"]["unknown_role"] == 1


# ---------------------------------------------------------------------------
# ③ 脏行 / 缺字段容错
# ---------------------------------------------------------------------------


def test_tolerates_dirty_lines_and_missing_fields(tmp_path: Path) -> None:
    """脏行跳过计入 skipped；缺字段行不崩溃并以 <unknown> 占位。"""
    module = _load_script()
    log_path = _write_sample(tmp_path)

    report = module.observe(log_path, MODEL_PATH)

    assert report["skipped_lines"] == 1
    unknowns = [
        group for group in report["groups"] if group["endpoint"] == "<unknown>"
    ]
    assert len(unknowns) == 1
    assert unknowns[0]["role"] == "<unknown>"
    assert unknowns[0]["model_allows"] is None


# ---------------------------------------------------------------------------
# ④ --json 落盘证据
# ---------------------------------------------------------------------------


def test_json_evidence_written_to_file(tmp_path: Path) -> None:
    """--json <path> 将报告落盘为 JSON 证据文件。"""
    module = _load_script()
    log_path = _write_sample(tmp_path)
    evidence = tmp_path / "evidence" / "shadow.json"

    exit_code = module.main(
        ["--log", str(log_path), "--model", str(MODEL_PATH), "--json", str(evidence)]
    )

    assert exit_code == 0
    assert evidence.exists()
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    assert payload["totals"]["would_deny"] == 7
    assert "digestion" in payload


# ---------------------------------------------------------------------------
# ⑤ 内置样例 fixture 可被消费
# ---------------------------------------------------------------------------


def test_builtin_fixture_is_consumable() -> None:
    """仓内样例日志（tests/fixtures）须可被脚本解析（防止 fixture 与解析器漂移）。"""
    module = _load_script()
    assert FIXTURE.exists(), f"缺少样例日志: {FIXTURE}"

    report = module.observe(FIXTURE, MODEL_PATH)
    assert report["totals"]["would_deny"] > 0
    assert report["digestion"]["digestion_rate"] > 0
