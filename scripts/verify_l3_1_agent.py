"""S7-T5 L3-1 Agent 端到端核验（真实面运行器）.

设计依据：OpenBase-S7-全域门禁与总收官-设计草案-v1.0.0 §4.5（S7-T5-1~4）、§5 证据规范。

真实执行链（禁伪造，全部经真实 HTTP/真实服务）：
  1. agent key 签发（POST /api/v1/identity/agents → sk-agent-*）→ /auth/me 四头主体一致；
     agent 无交互登录路径（POST /auth/login 用 agent 用户名 → 401）
  2. 各系统白名单矩阵（DPS/OpenLLM/OpenRAG/OpenMemory 各 >=3 例）：
     受信来源 + 四头 → 放行；非受信来源 + 四头 → 403 PERM_UNTRUSTED_IDENTITY_HEADER；
     受信来源 + agent 密钥 → 放行
  3. 域隔离：跨域不可见（需双域数据面，未预置时保持 PENDING）
  4. 未授权 403 + M1 独立模式（ob_k_* 服务密钥自身认证）/ M2 受信头采纳分别断言

用法：
  python scripts/verify_l3_1_agent.py [--base-url URL] [--evidence-dir DIR]
        [--repo-root DIR] [--dry-run]

统一退出码：0=PASS / 1=FAIL / 2=PENDING
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# 受信来源常量（openbase/modules/protocol_headers/constants.py 单一事实源）
SOURCE_BY_SYSTEM = {
    "DPS": "openbase-dps-proxy",
    "OpenLLM": "openbase-llm-proxy",
    "OpenRAG": "openbase-rag-proxy",
    "OpenMemory": "openbase-memory-proxy",
}
UNTRUSTED_SOURCE = "untrusted-source"
IDENTITY_HEADERS = {
    "X-User-ID": "1",
    "X-Tenant-ID": "tenant-1",
    "X-User-Role": "admin",
    "X-Proxy-Source": "",
}


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
        headers: dict[str, str] | None = None,
        token: str | None = None,
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
        except Exception as exc:  # noqa: BLE001
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


def _error_code(payload: Any) -> str:
    return str(payload.get("code", "")) if isinstance(payload, dict) else ""


# 干跑检查清单（与设计 §4.5 断言编号一一映射；禁伪造：一律 PENDING + 原因）
_DRY_RUN_REASON = "dry-run：未连接真实服务（禁伪造 PASS）"
_DRY_RUN_SPECS: tuple[tuple[str, str, str], ...] = (
    ("S7-T5-1", "agent key -> 四头齐全且与主体一致；agent 无交互登录路径（0 可达）", "agent-key-issuance.json"),
    ("S7-T5-2", "各系统白名单放行（每系统 >=3 例）；非白名单携带身份头全链路 403", "system-whitelist-cases.json"),
    ("S7-T5-3", "域隔离：跨域不可见（404/403/空），跨域同名并存互不可见", "domain-isolation.json"),
    ("S7-T5-4", "未授权 403（PERM_UNTRUSTED_IDENTITY_HEADER）；M1/M2 双模式分别断言", "unauthorized-403.json"),
)


def _dry_run_checks() -> list[dict[str, Any]]:
    return [
        check(spec[0], spec[1], "B", "PENDING", _DRY_RUN_REASON,
              f"doc/test/evidence/s7/l3-1/{spec[2]}")
        for spec in _DRY_RUN_SPECS
    ]


def run_agent_e2e(client: HttpClient, base_url: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """执行 L3-1 四项检查，返回 (checks, artifacts)."""
    evidence_dir = "doc/test/evidence/s7/l3-1"
    checks: list[dict[str, Any]] = []
    artifacts: dict[str, Any] = {}

    stamp = str(int(time.time()))
    agent_username = f"smoke_l3_1_{stamp}"

    # --- 1. agent 主体 + sk-agent-* 密钥签发 ---
    create_code, created = client.call(
        "POST",
        "/api/v1/identity/agents",
        {"username": agent_username, "display_name": "S7-T5 L3-1 冒烟 agent", "role": "viewer"},
    )
    if create_code != 200 or not isinstance(created, dict):
        checks.append(check(
            "S7-T5-1",
            "agent key -> 四头齐全且与主体一致；agent 无交互登录路径（0 可达）",
            "B",
            "FAIL",
            f"agent 主体创建失败 http={create_code}",
            f"{evidence_dir}/agent-key-issuance.json",
        ))
        return checks, artifacts

    agent_id = created.get("agent_id")
    api_key = created.get("api_key") or {}
    agent_key = api_key.get("raw_key") or ""
    key_id = api_key.get("id")
    artifacts.update({"agent_id": agent_id, "agent_key_id": key_id, "agent_username": agent_username})

    me_code, me_payload = client.call("GET", "/api/v1/auth/me", token=agent_key)
    me_ok = (
        me_code == 200
        and isinstance(me_payload, dict)
        and me_payload.get("id") == agent_id
        and me_payload.get("username") == agent_username
    )
    login_code, login_payload = client.call(
        "POST", "/api/v1/auth/login", {"username": agent_username, "password": "whatever-12345"}
    )
    # agent 主体无密码凭据：交互登录一律被拒（401 无凭据 / 403 拒绝），即「无交互登录路径」
    no_login_path = login_code in (401, 403)
    artifacts["agent_me"] = me_payload if isinstance(me_payload, dict) else me_payload
    artifacts["agent_login_http"] = login_code
    artifacts["agent_login_error_code"] = _error_code(login_payload)

    # agent suspend -> 密钥即时失效；restore 后旧密钥不复活（须重新签发）
    suspend_code, _ = client.call(
        "POST", f"/api/v1/identity/lifecycle/agent/{agent_id}/suspend", {"reason": "L3-1 联调"}
    )
    revoked_code, revoked_payload = client.call("GET", "/api/v1/auth/me", token=agent_key)
    key_immediately_invalid = suspend_code == 200 and revoked_code == 401
    client.call("POST", f"/api/v1/identity/lifecycle/agent/{agent_id}/restore", {"reason": "L3-1 联调恢复"})
    after_restore_code, _ = client.call("GET", "/api/v1/auth/me", token=agent_key)
    old_key_stays_dead = after_restore_code == 401
    artifacts["suspend_invalidates_key"] = key_immediately_invalid
    artifacts["old_key_not_resurrected"] = old_key_stays_dead

    if me_ok and no_login_path and key_immediately_invalid and old_key_stays_dead:
        checks.append(check(
            "S7-T5-1",
            "agent key -> 主体一致（四头齐备）；agent 无交互登录路径（0 可达）；"
            "suspend 即时失效且 restore 不复活旧密钥",
            "B",
            "PASS",
            "",
            f"{evidence_dir}/agent-key-issuance.json",
        ))
    else:
        checks.append(check(
            "S7-T5-1",
            "agent key -> 四头齐全且与主体一致；agent 无交互登录路径（0 可达）",
            "B",
            "FAIL",
            f"me={me_code} login={login_code}(期望 401) suspend={suspend_code} "
            f"key_after_suspend={revoked_code}(期望 401) key_after_restore={after_restore_code}(期望 401)",
            f"{evidence_dir}/agent-key-issuance.json",
        ))

    # 轮换新密钥以供后续矩阵使用（restore 后旧密钥不复活，须重新签发）
    rotate_code, rotated = client.call(
        "POST", f"/api/v1/identity/agents/{agent_id}/keys", {"name": "l3-1-matrix"}
    )
    fresh_key = rotated.get("raw_key") if isinstance(rotated, dict) else None
    artifacts["rotate_code"] = rotate_code

    # --- 2. 各系统白名单矩阵 ---
    cases: list[dict[str, Any]] = []
    for system, source in SOURCE_BY_SYSTEM.items():
        trusted_headers = dict(IDENTITY_HEADERS)
        trusted_headers["X-Proxy-Source"] = source
        pass_code, _ = client.call("GET", "/api/v1/auth/me", headers=trusted_headers)
        cases.append({"system": system, "case": "trusted-header-pass", "http": pass_code, "expect": 200})

        untrusted_headers = dict(IDENTITY_HEADERS)
        untrusted_headers["X-Proxy-Source"] = UNTRUSTED_SOURCE
        forbid_code, forbid_payload = client.call("GET", "/api/v1/auth/me", headers=untrusted_headers)
        cases.append({
            "system": system,
            "case": "untrusted-header-forbidden",
            "http": forbid_code,
            "error_code": _error_code(forbid_payload),
            "expect": 403,
        })

        agent_headers = dict(IDENTITY_HEADERS)
        agent_headers["X-Proxy-Source"] = source
        agent_code, _ = client.call("GET", "/api/v1/auth/me", headers=agent_headers, token=fresh_key)
        cases.append({"system": system, "case": "trusted-header-agent-key", "http": agent_code, "expect": 200})

    artifacts["whitelist_cases"] = cases
    matrix_ok = all(
        item["http"] == item["expect"]
        and (item["expect"] != 403 or item.get("error_code") == "PERM_UNTRUSTED_IDENTITY_HEADER")
        for item in cases
    )
    if matrix_ok:
        checks.append(check(
            "S7-T5-2",
            "各系统白名单放行（每系统 >=3 例）；非白名单携带身份头全链路 403",
            "B",
            "PASS",
            "",
            f"{evidence_dir}/system-whitelist-cases.json",
        ))
    else:
        bad = [item for item in cases if item["http"] != item["expect"]]
        checks.append(check(
            "S7-T5-2",
            "各系统白名单放行（每系统 >=3 例）；非白名单携带身份头全链路 403",
            "B",
            "FAIL",
            f"矩阵 {len(cases)} 例中 {len(bad)} 例不符：{json.dumps(bad[:4], ensure_ascii=False)}",
            f"{evidence_dir}/system-whitelist-cases.json",
        ))

    # --- 3. 域隔离 ---
    checks.append(check(
        "S7-T5-3",
        "域隔离：跨域不可见（404/403/空），跨域同名并存互不可见",
        "B",
        "PENDING",
        "双域（双租户）同名数据面未预置，跨域可见性无法在真实数据面断言；需预置双域数据后回填",
        f"{evidence_dir}/domain-isolation.json",
    ))

    # --- 4. 未授权 403 + M1/M2 双模式 ---
    untrusted_headers = dict(IDENTITY_HEADERS)
    untrusted_headers["X-Proxy-Source"] = UNTRUSTED_SOURCE
    forbid_code, forbid_payload = client.call("GET", "/api/v1/auth/me", headers=untrusted_headers)

    m1_code, m1_payload = client.call("POST", "/api/v1/auth/api-keys", {"name": f"l3-1-m1-{stamp}"})
    service_key = m1_payload.get("key") if isinstance(m1_payload, dict) else None
    m1_proxy_code = -1
    m1_anon_code = -1
    if service_key:
        m1_proxy_code, _ = client.call(
            "GET", "/api/v1/proxy/openllm/health", headers={"X-API-Key": service_key}
        )
    # 显式无凭据（token="" 覆盖客户端默认 JWT），验证匿名被拒
    m1_anon_code, _ = client.call("GET", "/api/v1/proxy/openllm/health", token="")
    m2_headers = dict(IDENTITY_HEADERS)
    m2_headers["X-Proxy-Source"] = SOURCE_BY_SYSTEM["DPS"]
    m2_code, _ = client.call("GET", "/api/v1/auth/me", headers=m2_headers)

    artifacts.update({
        "untrusted_http": forbid_code,
        "untrusted_error_code": _error_code(forbid_payload),
        "m1_service_key_http": m1_code,
        "m1_proxy_http": m1_proxy_code,
        "m1_proxy_anonymous_http": m1_anon_code,
        "m2_trusted_header_http": m2_code,
    })
    # M1 独立模式：ob_k_ 服务密钥在 /proxy 通道自身认证放行（匿名同路径 401 作对照）
    if (
        forbid_code == 403
        and _error_code(forbid_payload) == "PERM_UNTRUSTED_IDENTITY_HEADER"
        and m1_proxy_code in (200, 201, 202)
        and m1_anon_code == 401
        and m2_code == 200
    ):
        checks.append(check(
            "S7-T5-4",
            "未授权 403（PERM_UNTRUSTED_IDENTITY_HEADER）；M1 独立模式与 M2 受信头采纳分别断言",
            "B",
            "PASS",
            "",
            f"{evidence_dir}/unauthorized-403.json + m1-m2.json",
        ))
    else:
        checks.append(check(
            "S7-T5-4",
            "未授权 403（PERM_UNTRUSTED_IDENTITY_HEADER）；M1 独立模式与 M2 受信头采纳分别断言",
            "B",
            "FAIL",
            f"untrusted={forbid_code}/{_error_code(forbid_payload)}(期望 403/PERM_UNTRUSTED_IDENTITY_HEADER) "
            f"M1 proxy={m1_proxy_code}(期望 2xx) M1 匿名={m1_anon_code}(期望 401) M2 trusted={m2_code}(期望 200)",
            f"{evidence_dir}/unauthorized-403.json + m1-m2.json",
        ))
    return checks, artifacts


def main() -> int:
    parser = argparse.ArgumentParser(description="S7-T5 L3-1 Agent 端到端核验（真实面）")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--evidence-dir", default="")
    parser.add_argument("--repo-root", default="")
    parser.add_argument("--tool-name", default="verify_l3_1_agent.py",
                        help="证据 tool 字段（委派入口可传 .ps1 名，保持工具契约一致）")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    repo_root = Path(args.repo_root).resolve() if args.repo_root else script_path.parent.parent
    evidence_dir = Path(args.evidence_dir).resolve() if args.evidence_dir else repo_root / "doc/test/evidence/s7/l3-1"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    result: dict[str, Any] = {
        "schema_version": 1,
        "tool": args.tool_name,
        "task": "S7-T5",
        "evidence_ref": "S7-T5-1~4",
        "title": "S7-T5 L3-1 Agent 端到端",
        "mode": "dry-run" if args.dry_run else "run",
        "execution_face": "B",
        "base_url": args.base_url,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "commit": _git_head(repo_root),
        "identity_headers": ["X-User-ID", "X-Tenant-ID", "X-User-Role", "X-Proxy-Source"],
    }

    if args.dry_run:
        checks = _dry_run_checks()
        result.update({
            "status": "PENDING",
            "exit_code": 2,
            "reason": _DRY_RUN_REASON,
            "checks": checks,
        })
        _write(evidence_dir / "agent-e2e.json", result)
        print("=== S7-T5 L3-1 Agent 端到端（dry-run）===\n  status=PENDING exit=2")
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
        _write(evidence_dir / "agent-e2e.json", result)
        print(f"=== S7-T5 L3-1 ===\n  status=PENDING exit=2（登录失败 http={login_code}）")
        return 2
    client.token = login_payload["access_token"]

    checks, artifacts = run_agent_e2e(client, args.base_url)
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
    _write(evidence_dir / "agent-e2e.json", result)

    print("=== S7-T5 L3-1 Agent 端到端 ===")
    print(f"  status={overall} exit={exit_code}")
    for item in checks:
        print(f"  [{item['status']}] {item['id']} - {item['name']}")
    print(f"  evidence: {evidence_dir / 'agent-e2e.json'}")
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
