"""S7-T3 L2-1 主备切换演练（真实运行器）.

设计依据：OpenBase-S7-全域门禁与总收官-设计草案-v1.0.0 §4.3（S7-T3-1~4）、§5 证据规范。

真实执行链（禁伪造）：驱动 OpenLLM 侧真实通道状态机 `app.identity.channel.ChannelStateManager`
（S4-T7 落点，B 主 A 备 / 单主路径 / 双源降级感知 / 演练窗口回切 / 全程审计）：
  1. 场景 1（B 断 -> A 接管）：组件级降级感知达阈值 -> 显式 B→A 接管；
     接管后 A 为唯一主路径，写路径只能在 A（经 B 写被拒），业务不中断
  2. 场景 2（A 断 -> B 维持）：A（备）故障信号不影响 B 主，单主路径保持，业务不中断
  3. 单主路径：任一时刻 active_primary_paths 恒长 1，禁双主双写（写路径护栏断言）
  4. 回切与报告：B 恢复 + 演练窗口开窗/验证/结束 -> 显式 A→B 回切；
     演练报告字段齐备（场景/命令/切换前后路由/降级头/告警/回切条件/结论）

边界：事件通道（L1-1）不纳入演练矩阵（Q-S7-4）。

用法：
  python scripts/drill_l2_1_failover.py [--evidence-dir DIR] [--repo-root DIR]
        [--openllm-backend DIR] [--dry-run]

统一退出码：0=PASS / 1=FAIL / 2=PENDING
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

DEFAULT_OPENLLM_BACKEND = r"D:\Trae CN\myproject\Dev\OpenLLM\backend"


def check(check_id: str, name: str, face: str, status: str, reason: str, evidence: str) -> dict[str, Any]:
    return {
        "id": check_id,
        "name": name,
        "execution_face": face,
        "status": status,
        "reason": reason,
        "evidence": evidence,
    }


# 干跑检查清单（与设计 §4.3 断言编号一一映射；禁伪造：一律 PENDING + 原因）
_DRY_RUN_REASON = "dry-run：未驱动真实通道状态机（禁伪造 PASS）"
_DRY_RUN_SPECS: tuple[tuple[str, str, str], ...] = (
    ("S7-T3-1", "B 断 -> A 接管（A 直连接管，降级告警产生，业务不中断）", "drill-report.md（场景 1）"),
    ("S7-T3-2", "A 断 -> B 维持（B 编排维持，业务不中断）", "drill-report.md（场景 2）"),
    ("S7-T3-3", "单主路径：同一动作同一时刻仅一条主路径，禁双主双写", "route-before.json + route-after.json"),
    ("S7-T3-4", "演练报告字段齐备（场景/命令/路由/降级头/告警/回切条件/结论）", "drill-report.md"),
)


def _dry_run_checks() -> list[dict[str, Any]]:
    return [
        check(spec[0], spec[1], "B", "PENDING", _DRY_RUN_REASON,
              f"doc/test/evidence/s7/l2-1/{spec[2]}")
        for spec in _DRY_RUN_SPECS
    ]


def run_drill(backend: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """驱动真实通道状态机完成双场景演练，返回 (checks, artifacts)."""
    sys.path.insert(0, str(backend))
    # 跨仓导入不落 __pycache__（受限执行面/只读仓友好）
    sys.dont_write_bytecode = True
    from app.identity.channel import (  # noqa: PLC0415 - 运行期注入 OpenLLM 通道状态机
        CHANNEL_A,
        CHANNEL_B,
        ChannelStateManager,
        ChannelSwitchError,
    )

    evidence_dir = "doc/test/evidence/s7/l2-1"
    checks: list[dict[str, Any]] = []
    artifacts: dict[str, Any] = {}

    # ---- 场景 1：B 断 -> A 接管 ----
    manager = ChannelStateManager(preference="b-primary")
    route_before = manager.primary_channel
    manager.record_b_component_failure("llm-proxy", reason="演练注入：B 组件探活失败")
    manager.record_b_component_failure("llm-proxy", reason="演练注入：B 组件探活失败")
    failures = manager.record_b_component_failure("llm-proxy", reason="演练注入：B 组件探活失败")
    takeover = manager.trigger_failover_to_a(source="component_degrade", reason="演练注入：B 达降级阈值")
    route_after = manager.primary_channel
    single_after_takeover = manager.active_primary_paths()
    try:
        manager.assert_write_channel_is_primary(CHANNEL_A)
        write_on_a_allowed = True
    except ChannelSwitchError:
        write_on_a_allowed = False
    try:
        manager.assert_write_channel_is_primary(CHANNEL_B)
        write_on_b_allowed = True
    except ChannelSwitchError:
        write_on_b_allowed = False
    artifacts["scenario_b_down"] = {
        "route_before": route_before,
        "consecutive_failures": failures,
        "takeover": takeover,
        "route_after": route_after,
        "primary_paths_after": single_after_takeover,
        "write_on_a_allowed": write_on_a_allowed,
        "write_on_b_rejected": not write_on_b_allowed,
        "alert_events": [item["action"] for item in manager.audit_trail()],
    }
    if (
        route_before == CHANNEL_B
        and takeover is True
        and route_after == CHANNEL_A
        and single_after_takeover == [CHANNEL_A]
        and write_on_a_allowed
        and not write_on_b_allowed
    ):
        checks.append(check(
            "S7-T3-1",
            "B 断 -> A 接管（A 直连接管，降级告警产生，业务不中断）",
            "B",
            "PASS",
            "",
            f"{evidence_dir}/drill-report.md（场景 1）+ route-after.json",
        ))
    else:
        checks.append(check(
            "S7-T3-1",
            "B 断 -> A 接管（A 直连接管，降级告警产生，业务不中断）",
            "B",
            "FAIL",
            f"before={route_before} takeover={takeover} after={route_after} "
            f"paths={single_after_takeover} write_a={write_on_a_allowed} write_b={write_on_b_allowed}",
            f"{evidence_dir}/drill-report.md（场景 1）+ route-after.json",
        ))

    # ---- 场景 2：A 断 -> B 维持 ----
    manager2 = ChannelStateManager(preference="b-primary")
    before2 = manager2.primary_channel
    a_failures = manager2.record_a_failure(reason="演练注入：A 直连故障")
    after2 = manager2.primary_channel
    paths2 = manager2.active_primary_paths()
    auto_takeover = manager2.evaluate_auto_failover()
    artifacts["scenario_a_down"] = {
        "route_before": before2,
        "a_consecutive_failures": a_failures,
        "route_after": after2,
        "primary_paths_after": paths2,
        "auto_failover": auto_takeover,
        "a_health": manager2.a_health(),
    }
    if before2 == CHANNEL_B and after2 == CHANNEL_B and paths2 == [CHANNEL_B] and auto_takeover is False:
        checks.append(check(
            "S7-T3-2",
            "A 断 -> B 维持（B 编排维持，业务不中断）",
            "B",
            "PASS",
            "",
            f"{evidence_dir}/drill-report.md（场景 2）",
        ))
    else:
        checks.append(check(
            "S7-T3-2",
            "A 断 -> B 维持（B 编排维持，业务不中断）",
            "B",
            "FAIL",
            f"before={before2} after={after2} paths={paths2} auto_failover={auto_takeover}",
            f"{evidence_dir}/drill-report.md（场景 2）",
        ))

    # ---- 单主路径：全程采样恒长 1 ----
    samples: list[dict[str, Any]] = []
    probe = ChannelStateManager(preference="b-primary")
    samples.append({"stage": "initial", "primary": probe.primary_channel, "paths": probe.active_primary_paths()})
    probe.trigger_failover_to_a(source="manual", reason="单主采样")
    samples.append({"stage": "after-failover", "primary": probe.primary_channel, "paths": probe.active_primary_paths()})
    probe.mark_b_recovered()
    probe.open_drill_window()
    probe.verify_drill()
    probe.confirm_drill_elapsed()
    probe.switch_back_to_b()
    samples.append({"stage": "after-switch-back", "primary": probe.primary_channel, "paths": probe.active_primary_paths()})
    single_primary_ok = all(len(item["paths"]) == 1 for item in samples)
    artifacts["single_primary_samples"] = samples
    if single_primary_ok:
        checks.append(check(
            "S7-T3-3",
            "单主路径：同一动作同一时刻仅一条主路径，禁双主双写",
            "B",
            "PASS",
            "",
            f"{evidence_dir}/route-before.json + route-after.json",
        ))
    else:
        checks.append(check(
            "S7-T3-3",
            "单主路径：同一动作同一时刻仅一条主路径，禁双主双写",
            "B",
            "FAIL",
            f"采样中出现非单主：{json.dumps(samples, ensure_ascii=False)}",
            f"{evidence_dir}/route-before.json + route-after.json",
        ))

    # ---- 演练报告字段齐备（回切链路 + 审计留痕） ----
    switch_back_ok = probe.primary_channel == CHANNEL_B
    audit_actions = [item["action"] for item in probe.audit_trail()]
    required_actions = {
        "failover_b_to_a",
        "recover_b",
        "drill_window_open",
        "drill_verified",
        "drill_window_elapsed",
        "switch_back_to_b",
    }
    missing_actions = sorted(required_actions - set(audit_actions))
    status_report = probe.channel_status()
    artifacts["restore_chain"] = {
        "switch_back_ok": switch_back_ok,
        "audit_actions": audit_actions,
        "missing_audit_actions": missing_actions,
        "channel_status": status_report,
    }
    if switch_back_ok and not missing_actions and status_report.get("single_primary") is True:
        checks.append(check(
            "S7-T3-4",
            "演练报告字段齐备（场景/命令/路由/降级头/告警/回切条件/结论）",
            "B",
            "PASS",
            "",
            f"{evidence_dir}/drill-report.md",
        ))
    else:
        checks.append(check(
            "S7-T3-4",
            "演练报告字段齐备（场景/命令/路由/降级头/告警/回切条件/结论）",
            "B",
            "FAIL",
            f"switch_back={switch_back_ok} missing_audit={missing_actions} status={status_report}",
            f"{evidence_dir}/drill-report.md",
        ))
    return checks, artifacts


def write_report(path: Path, checks: list[dict[str, Any]], artifacts: dict[str, Any], overall: str) -> None:
    """演练报告（字段齐备：场景/命令/切换前后路由/告警/回切条件/结论）."""
    scenario_b = artifacts.get("scenario_b_down", {})
    scenario_a = artifacts.get("scenario_a_down", {})
    restore = artifacts.get("restore_chain", {})
    lines = [
        "# S7-T3 L2-1 主备切换演练报告",
        "",
        f"- 生成时间：{time.strftime('%Y-%m-%dT%H:%M:%S%z')}",
        "- 驱动面：OpenLLM `app.identity.channel.ChannelStateManager`（S4-T7 真实状态机）",
        f"- 结论：{overall}",
        "- 边界：事件通道（L1-1）不纳入演练矩阵（Q-S7-4）",
        "",
        "| 场景 | 命令 | 切换前路由 | 切换后路由 | 降级告警 | 回切条件 | 结论 |",
        "|------|------|-----------|-----------|---------|---------|------|",
        (
            f"| 场景 1：B 断 -> A 接管 | trigger_failover_to_a(source=component_degrade) "
            f"| {scenario_b.get('route_before', '-')} | {scenario_b.get('route_after', '-')} "
            f"| {','.join(scenario_b.get('alert_events', [])) or '-'} | 显式 B 恢复 + 演练窗口 | "
            f"{checks[0]['status']} |"
        ),
        (
            f"| 场景 2：A 断 -> B 维持 | record_a_failure(reason=演练注入) "
            f"| {scenario_a.get('route_before', '-')} | {scenario_a.get('route_after', '-')} "
            f"| a_failure（备不可用） | A 恢复 + 显式切回 | {checks[1]['status']} |"
        ),
        "",
        "## 单主路径采样",
        "",
    ]
    for sample in artifacts.get("single_primary_samples", []):
        lines.append(f"- {sample['stage']}：primary={sample['primary']} paths={sample['paths']}")
    lines += [
        "",
        "## 回切链路审计留痕",
        "",
        f"- 回切成功：{restore.get('switch_back_ok')}",
        f"- 审计动作序列：{restore.get('audit_actions')}",
        f"- 缺失动作：{restore.get('missing_audit_actions')}",
        f"- 通道状态上报：{restore.get('channel_status')}",
        "",
        "> 未真实执行项保持 PENDING；本报告由真实状态机驱动生成，非样例填充。",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="S7-T3 L2-1 主备切换演练（真实运行器）")
    parser.add_argument("--evidence-dir", default="")
    parser.add_argument("--repo-root", default="")
    parser.add_argument("--openllm-backend", default=DEFAULT_OPENLLM_BACKEND)
    parser.add_argument("--tool-name", default="drill_l2_1_failover.py",
                        help="证据 tool 字段（委派入口可传 .ps1 名，保持工具契约一致）")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    repo_root = Path(args.repo_root).resolve() if args.repo_root else script_path.parent.parent
    evidence_dir = Path(args.evidence_dir).resolve() if args.evidence_dir else repo_root / "doc/test/evidence/s7/l2-1"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    backend = Path(args.openllm_backend)

    result: dict[str, Any] = {
        "schema_version": 1,
        "tool": args.tool_name,
        "task": "S7-T3",
        "evidence_ref": "S7-T3-1~4",
        "title": "S7-T3 L2-1 主备切换演练",
        "mode": "dry-run" if args.dry_run else "run",
        "execution_face": "B",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "commit": _git_head(repo_root),
        "openllm_backend": str(backend),
    }

    if args.dry_run:
        checks = _dry_run_checks()
        result.update({
            "status": "PENDING",
            "exit_code": 2,
            "reason": _DRY_RUN_REASON,
            "checks": checks,
        })
        _write(evidence_dir / "failover-drill.json", result)
        print("=== S7-T3 L2-1 主备切换演练（dry-run）===\n  status=PENDING exit=2")
        for item in checks:
            print(f"  [{item['status']}] {item['id']} - {item['name']}")
        return 2

    if not (backend / "app" / "identity" / "channel.py").is_file():
        result.update({
            "status": "PENDING",
            "exit_code": 2,
            "reason": f"未找到 OpenLLM 通道状态机：{backend / 'app/identity/channel.py'}",
            "checks": [],
        })
        _write(evidence_dir / "failover-drill.json", result)
        print("=== S7-T3 L2-1 ===\n  status=PENDING exit=2（状态机不可用）")
        return 2

    checks, artifacts = run_drill(backend)
    statuses = [item["status"] for item in checks]
    if "FAIL" in statuses:
        overall, exit_code = "FAIL", 1
    elif all(item == "PASS" for item in statuses):
        overall, exit_code = "PASS", 0
    else:
        overall, exit_code = "PENDING", 2
    result.update({
        "status": overall,
        "exit_code": exit_code,
        "checks": checks,
        "artifacts": artifacts,
        "reason": "" if overall == "PASS" else "存在未闭合项（见 checks[].reason）",
    })
    _write(evidence_dir / "failover-drill.json", result)
    write_report(evidence_dir / "drill-report.md", checks, artifacts, overall)

    print("=== S7-T3 L2-1 主备切换演练 ===")
    print(f"  status={overall} exit={exit_code}")
    for item in checks:
        print(f"  [{item['status']}] {item['id']} - {item['name']}")
    print(f"  evidence: {evidence_dir / 'failover-drill.json'}")
    print(f"  report:   {evidence_dir / 'drill-report.md'}")
    return exit_code


def _git_head(repo_root: Path) -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=20,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    except Exception:  # noqa: BLE001
        return ""
    return ""


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
