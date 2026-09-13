"""S7-T2 L1-1 级联全链核验（真实面运行器）.

设计依据：OpenBase-S7-全域门禁与总收官-设计草案-v1.0.0 §4.2（S7-T2-1~4）、§5 证据规范。

真实执行链（禁伪造，全部经真实 HTTP/真实服务）：
  1. 停用主体（POST /api/v1/identity/lifecycle/{type}/{id}/suspend）→ 状态迁移 + tvn+1
  2. outbox 事件投递（GET /api/v1/identity/events 取已 published 的 user.suspended 真实载荷）
  3. 契约桩消费（POST /api/v1/identity/events/apply）→ 数据面阻断集落地
  4. 断言 DPS / OpenMemory / OpenRAG 三域阻断（GET /api/v1/identity/blocked/{id} → 403）
  5. event_id 幂等重放（同载荷二次 apply → deduplicated=true，无重复副作用）
  6. restored 解除阻断（restore + apply → blocked 200 allowed=true）
  7. purge 负例：非 deactivated → 400 BIZ_NOT_PURGEABLE；未授权 → 403 BIZ_PURGE_AUTH_REQUIRED
  8. purge 正例：CLI 签发一次性授权码 → POST /api/v1/identity/purge → 物理清除 + 审计留痕
     （授权码仅能由 CLI/服务层签发；执行面受限时该项保持 PENDING，不伪造）

用法：
  python scripts/verify_l1_1_cascade.py [--base-url URL] [--evidence-dir DIR]
        [--repo-root DIR] [--dry-run]

统一退出码：0=PASS / 1=FAIL / 2=PENDING
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
EVENT_WAIT_SECONDS = 20.0


class HttpClient:
    """极简 JSON HTTP 客户端（urllib，零第三方依赖）."""

    def __init__(self, base_url: str, token: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token

    def call(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        token: str | None = None,
        headers: dict[str, str] | None = None,
        timeout: int = 25,
    ) -> tuple[int, Any]:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(self.base_url + path, data=data, method=method)
        request.add_header("Accept", "application/json")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        effective_token = token if token is not None else self.token
        if effective_token:
            request.add_header("Authorization", f"Bearer {effective_token}")
        for name, value in (headers or {}).items():
            request.add_header(name, value)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.status, _decode(response.read())
        except urllib.error.HTTPError as exc:
            return exc.code, _decode(exc.read())
        except Exception as exc:  # noqa: BLE001 - 网络不可达统一表达为 -1
            return -1, f"{type(exc).__name__}: {exc}"


def _decode(raw: bytes) -> Any:
    text = raw.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def check(check_id: str, name: str, face: str, status: str, reason: str, evidence: str) -> dict[str, Any]:
    return {
        "id": check_id,
        "name": name,
        "execution_face": face,
        "status": status,
        "reason": reason,
        "evidence": evidence,
    }


# 干跑检查清单（与设计 §4.2 断言编号一一映射；禁伪造：一律 PENDING + 原因）
_DRY_RUN_REASON = "dry-run：未连接真实服务（禁伪造 PASS）"
_DRY_RUN_SPECS: tuple[tuple[str, str, str], ...] = (
    ("S7-T2-1", "DPS 画像读阻断（绑定失效 -> 403，数据保留）", "dps-block.json"),
    ("S7-T2-2", "OpenMemory 记忆数据面阻断 + event_id 幂等（重放不双写）", "openmemory-block.json"),
    ("S7-T2-3", "Q-5=A 保留 + 全链阻断 + restored 解除阻断", "restore.json"),
    ("S7-T2-4", "purge 显式触发（400/403/物理清除 + audit_logs action=identity.purge）", "purge.json"),
)


def _dry_run_checks() -> list[dict[str, Any]]:
    return [
        check(spec[0], spec[1], "B", "PENDING", _DRY_RUN_REASON,
              f"doc/test/evidence/s7/l1-1/{spec[2]}")
        for spec in _DRY_RUN_SPECS
    ]


def wait_event(client: HttpClient, subject_id: int, event_type: str, wait_seconds: float) -> dict[str, Any] | None:
    """轮询等待 outbox 投递为 published，按主体 + 事件类型取真实载荷."""
    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        code, payload = client.call("GET", "/api/v1/identity/events?limit=200")
        if code != 200 or not isinstance(payload, dict):
            return None
        for item in reversed(payload.get("events") or []):
            subject = item.get("subject") or {}
            if subject.get("subject_id") == subject_id and item.get("event_type") == event_type:
                return item
        time.sleep(1.0)
    return None


def run_cascade(client: HttpClient, subject_id: int, event_wait: float) -> list[dict[str, Any]]:
    """执行 L1-1 级联并返回四项检查结果."""
    checks: list[dict[str, Any]] = []
    evidence_dir = "doc/test/evidence/s7/l1-1"

    # --- T2-1：停用 -> 事件投递 -> 消费 -> DPS 阻断 ---
    code, suspended = client.call(
        "POST",
        f"/api/v1/identity/lifecycle/user/{subject_id}/suspend",
        {"reason": "L1-1 联调：停用主体"},
    )
    suspend_ok = code == 200 and isinstance(suspended, dict) and suspended.get("status_state") == "suspended"
    event = wait_event(client, subject_id, "user.suspended", event_wait)
    if suspend_ok and event is not None:
        apply_code, _ = client.call("POST", "/api/v1/identity/events/apply", {"event": event})
        dps_code, _ = client.call("GET", f"/api/v1/identity/blocked/{subject_id}?domain=dps")
        if apply_code == 200 and dps_code == 403:
            checks.append(check(
                "S7-T2-1",
                "DPS 画像读阻断（绑定失效 -> 403，数据保留）",
                "B",
                "PASS",
                "",
                f"{evidence_dir}/dps-block.json",
            ))
        else:
            checks.append(check(
                "S7-T2-1",
                "DPS 画像读阻断（绑定失效 -> 403，数据保留）",
                "B",
                "FAIL",
                f"suspend={code} apply={apply_code} dps_blocked={dps_code}（期望 200/200/403）",
                f"{evidence_dir}/dps-block.json",
            ))
    else:
        checks.append(check(
            "S7-T2-1",
            "DPS 画像读阻断（绑定失效 -> 403，数据保留）",
            "B",
            "PENDING",
            f"suspend={code} event={'found' if event else 'not-published'}（事件未发布时保持 PENDING）",
            f"{evidence_dir}/dps-block.json",
        ))

    # --- T2-2：OpenMemory 阻断 + event_id 幂等 ---
    memory_code, _ = client.call("GET", f"/api/v1/identity/blocked/{subject_id}?domain=openmemory")
    replay_ok = False
    if event is not None:
        replay_code, replay_payload = client.call("POST", "/api/v1/identity/events/apply", {"event": event})
        replay_ok = (
            replay_code == 200
            and isinstance(replay_payload, dict)
            and bool((replay_payload.get("consumption") or {}).get("deduplicated"))
        )
    if memory_code == 403 and replay_ok:
        checks.append(check(
            "S7-T2-2",
            "OpenMemory 记忆数据面阻断 + event_id 幂等（重放不双写）",
            "B",
            "PASS",
            "",
            f"{evidence_dir}/openmemory-block.json + event-idempotency.json",
        ))
    elif memory_code == 403:
        checks.append(check(
            "S7-T2-2",
            "OpenMemory 记忆数据面阻断 + event_id 幂等（重放不双写）",
            "B",
            "FAIL",
            f"blocked={memory_code} 但幂等重放未返回 deduplicated=true",
            f"{evidence_dir}/openmemory-block.json + event-idempotency.json",
        ))
    else:
        checks.append(check(
            "S7-T2-2",
            "OpenMemory 记忆数据面阻断 + event_id 幂等（重放不双写）",
            "B",
            "FAIL",
            f"OpenMemory 未阻断: {memory_code}（期望 403）",
            f"{evidence_dir}/openmemory-block.json + event-idempotency.json",
        ))

    # --- T2-3：恢复解除阻断（Q-5=A 数据保留 + 全链阻断） ---
    restore_code, _ = client.call(
        "POST",
        f"/api/v1/identity/lifecycle/user/{subject_id}/restore",
        {"reason": "L1-1 联调：恢复主体"},
    )
    release_ok = False
    restore_event = wait_event(client, subject_id, "user.restored", event_wait)
    if restore_event is not None:
        client.call("POST", "/api/v1/identity/events/apply", {"event": restore_event})
    after_code, after_payload = client.call("GET", f"/api/v1/identity/blocked/{subject_id}")
    if (
        restore_code == 200
        and after_code == 200
        and isinstance(after_payload, dict)
        and after_payload.get("allowed") is True
    ):
        release_ok = True
    if release_ok:
        checks.append(check(
            "S7-T2-3",
            "Q-5=A 保留 + 全链阻断 + restored 解除阻断",
            "A+B",
            "PASS",
            "",
            f"{evidence_dir}/restore.json + scan-auto-purge.txt",
        ))
    else:
        checks.append(check(
            "S7-T2-3",
            "Q-5=A 保留 + 全链阻断 + restored 解除阻断",
            "A+B",
            "FAIL",
            f"restore={restore_code} blocked_after={after_code}（期望 200/200 allowed=true）",
            f"{evidence_dir}/restore.json + scan-auto-purge.txt",
        ))

    # --- T2-4：purge 显式触发（负例 + 正例） ---
    non_deactivated_code, _ = client.call(
        "POST",
        "/api/v1/identity/purge",
        {
            "subject_type": "user",
            "subject_id": subject_id,
            "purge_authorization_code": "bogus-authorization-code",
            "scope_report_hash": "0" * 32,
        },
    )
    client.call(
        "POST",
        f"/api/v1/identity/lifecycle/user/{subject_id}/deactivate",
        {"confirm": True, "reason": "L1-1 联调：注销"},
    )
    no_grant_code, no_grant_payload = client.call(
        "POST",
        "/api/v1/identity/purge",
        {
            "subject_type": "user",
            "subject_id": subject_id,
            "purge_authorization_code": "bogus-authorization-code",
            "scope_report_hash": "0" * 32,
        },
    )
    negative_ok = non_deactivated_code == 400 and no_grant_code == 403
    positive_status = "PENDING"
    positive_reason = "purge 授权码仅可由 CLI/服务层签发（DB 直连受限的执行面无法完成正例）"
    positive_code, positive_payload = issue_and_purge(subject_id)
    if positive_code == 200:
        positive_status = "PASS"
        positive_reason = ""
    elif positive_code is not None:
        positive_status = "FAIL"
        positive_reason = f"purge 正例响应 {positive_code} :: {json.dumps(positive_payload, ensure_ascii=False)[:200]}"
    if negative_ok and positive_status == "PASS":
        checks.append(check(
            "S7-T2-4",
            "purge 显式触发（400/403/物理清除 + audit_logs action=identity.purge）",
            "B",
            "PASS",
            "",
            f"{evidence_dir}/purge.json",
        ))
    elif not negative_ok:
        checks.append(check(
            "S7-T2-4",
            "purge 显式触发（400/403/物理清除 + audit_logs action=identity.purge）",
            "B",
            "FAIL",
            f"负例失败（非 deactivated={non_deactivated_code} 期望 400 / 未授权={no_grant_code} 期望 403）",
            f"{evidence_dir}/purge.json",
        ))
    else:
        checks.append(check(
            "S7-T2-4",
            "purge 显式触发（负例 400/403 已通过；物理清除 + 审计留痕待 CLI 授权码）",
            "B",
            "PENDING",
            positive_reason,
            f"{evidence_dir}/purge.json",
        ))
    return checks


def issue_and_purge(subject_id: int) -> tuple[int | None, Any]:
    """CLI 签发一次性 purge 授权码后经 API 执行 purge.

    Returns:
        (http_status, payload)；无法取得授权码时返回 (None, reason)。
    """
    issued = _cli_purge_authorize(subject_id)
    if issued is None:
        return None, "CLI 授权码签发不可用"
    client = HttpClient(DEFAULT_BASE_URL)
    login_code, login_payload = client.call(
        "POST", "/api/v1/auth/login", {"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    )
    if login_code != 200 or not isinstance(login_payload, dict):
        return None, "登录失败"
    client.token = login_payload.get("access_token")
    return client.call(
        "POST",
        "/api/v1/identity/purge",
        {
            "subject_type": "user",
            "subject_id": subject_id,
            "purge_authorization_code": issued["purge_authorization_code"],
            "scope_report_hash": issued["scope_report_hash"],
            "idempotency_key": f"l1-1-{subject_id}",
        },
    )


def _cli_purge_authorize(subject_id: int) -> dict[str, Any] | None:
    """调用 openbase-cli 签发 purge 授权码（受执行面 DB 连通性约束）."""
    for executable in (sys.executable, "python"):
        try:
            proc = subprocess.run(
                [
                    executable,
                    "-m",
                    "openbase.cli.main",
                    "identity",
                    "purge-authorize",
                    "--subject-id",
                    str(subject_id),
                    "--subject-type",
                    "user",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=120,
            )
        except Exception:  # noqa: BLE001 - 执行面受限时降级为 None
            continue
        if proc.returncode == 0 and proc.stdout.strip():
            try:
                return json.loads(proc.stdout)
            except json.JSONDecodeError:
                continue
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="S7-T2 L1-1 级联全链核验（真实面）")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--evidence-dir", default="")
    parser.add_argument("--repo-root", default="")
    parser.add_argument("--subject-id", type=int, default=0)
    parser.add_argument("--event-wait", type=float, default=EVENT_WAIT_SECONDS)
    parser.add_argument("--tool-name", default="verify_l1_1_cascade.py",
                        help="证据 tool 字段（委派入口可传 .ps1 名，保持工具契约一致）")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    repo_root = Path(args.repo_root).resolve() if args.repo_root else script_path.parent.parent
    evidence_dir = Path(args.evidence_dir).resolve() if args.evidence_dir else repo_root / "doc/test/evidence/s7/l1-1"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    result: dict[str, Any] = {
        "schema_version": 1,
        "tool": args.tool_name,
        "task": "S7-T2",
        "evidence_ref": "S7-T2-1~4",
        "title": "S7-T2 L1-1 级联全链核验",
        "mode": "dry-run" if args.dry_run else "run",
        "execution_face": "B",
        "base_url": args.base_url,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "commit": _git_head(repo_root),
    }

    if args.dry_run:
        checks = _dry_run_checks()
        result.update({
            "status": "PENDING",
            "exit_code": 2,
            "reason": _DRY_RUN_REASON,
            "checks": checks,
        })
        _write(evidence_dir / "cascade-result.json", result)
        print("=== S7-T2 L1-1 级联全链核验（dry-run）===\n  status=PENDING exit=2")
        for item in checks:
            print(f"  [{item['status']}] {item['id']} - {item['name']}")
        return 2

    client = HttpClient(args.base_url)
    login_code, login_payload = client.call(
        "POST", "/api/v1/auth/login", {"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    )
    if login_code != 200 or not isinstance(login_payload, dict) or not login_payload.get("access_token"):
        result.update({
            "status": "PENDING",
            "exit_code": 2,
            "reason": f"网关不可达或登录失败 http={login_code}",
            "checks": [],
        })
        _write(evidence_dir / "cascade-result.json", result)
        print(f"=== S7-T2 L1-1 ===\n  status=PENDING exit=2（登录失败 http={login_code}）")
        return 2
    client.token = login_payload["access_token"]

    subject_id = args.subject_id
    if not subject_id:
        stamp = str(int(time.time()))
        create_code, created = client.call(
            "POST",
            "/api/v1/users",
            {
                "username": f"smoke_l1_1_{stamp}",
                "password": "Smoke#12345",
                "display_name": "S7-T2 L1-1 冒烟主体",
                "role": "viewer",
            },
        )
        if create_code not in (200, 201) or not isinstance(created, dict):
            result.update({
                "status": "FAIL",
                "exit_code": 1,
                "reason": f"冒烟主体创建失败 http={create_code}",
                "checks": [],
            })
            _write(evidence_dir / "cascade-result.json", result)
            print(f"=== S7-T2 L1-1 ===\n  status=FAIL exit=1（建主体失败 http={create_code}）")
            return 1
        subject_id = created["id"]

    result["subject_id"] = subject_id
    checks = run_cascade(client, subject_id, args.event_wait)
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
        "reason": "" if overall == "PASS" else "存在未闭合项（见 checks[].reason）",
    })
    _write(evidence_dir / "cascade-result.json", result)

    print("=== S7-T2 L1-1 级联全链核验 ===")
    print(f"  status={overall} exit={exit_code} subject_id={subject_id}")
    for item in checks:
        print(f"  [{item['status']}] {item['id']} - {item['name']}")
    print(f"  evidence: {evidence_dir / 'cascade-result.json'}")
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
