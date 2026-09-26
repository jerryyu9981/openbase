"""智能体对话全链路 E2E 核验（本轮迭代目标）

目标链路（全真实 HTTP，无桩）：
  ① 以**智能体主体**接入（`sk-agent-*` 凭据）：管理员登录 → 创建 agent 主体
     （`tenant_id=1` → `tenant_code='tenant-1'`）→ 取一次性明文密钥
  ② `POST /api/v1/llm-proxy/chat`（OpenBase 统一底座 → Bearer + 身份头注入；
     agent 主体携带 `tenant_code` → 出站 `X-Tenant-ID=tenant-1`）
  ③ OpenLLM `/openllm/v1/chat`（`mode=auto`）→ **自动对接** 三源：
       · DPS 画像（profile_fetch）
       · OpenMemory 记忆（memory）
       · OpenRAG 知识库（rag，**kb_id 自动发现**）
  ④ 科学装配上下文（分段：system/profile/memory/rag/history/query）+ 分段计量
  ⑤ 投喂 LLM → 响应 + `routing_trace`（决策/路径/执行/降级/检索来源/计量回执/回执）

> **主体选择依据（本轮迭代实测）**：`admin`（JWT）无 `tenant_code` → 出站不带
> `X-Tenant-ID` → OpenLLM 回退 org 别名 → OpenRAG 落入**无集合**租户域
> （实测集合列举 200 但 `items=0`）→ 知识库自动对接取空。而 agent 主体
> （`openbase/modules/identity`，`tenant_id` → `tenants.code`）自带
> `tenant_code='tenant-1'`，与知识库所在域一致 —— 即「智能体对话」的**正规接入面**。

硬性判定（不满足即 FAIL）：
  H1 智能体主体就绪（agent 创建 200 且拿到 `sk-agent-*` 明文密钥）
  H2 chat HTTP 200 且 `code == 0`
  H3 `content` 非空
  H4 `degraded == []`（组件均未降级）
  H5 `executed ⊇ {memory, rag, llm}`（auto 决策路径 C：记忆+知识库+LLM）
  H6 `rag_source == "external"`（知识库命中**真实** OpenRAG，非 builtin/skipped）
  H7 `kb_id_source ∈ {registry, external}`（知识库**自动发现**生效，未依赖调用方传参）
  H8 `context_metrics.counted == True`（分段计量已接线）
  H9 `context_metrics.rag.injected_items >= 1` 且 `segment_tokens.rag > 0`
     （知识库内容**真实进入 Prompt** —— 「装配后投喂」的强证据）

观察项（仅记录，不判定）：记忆注入量、DPS 画像分段 token、归因 A、三路回写回执、
各步骤时间线（auth/profile_fetch/memory/rag/llm/writeback_dispatch）。

用法::

    python agent_context_e2e.py [--base-url http://127.0.0.1:8000] [--out DIR] [--query "..."]

退出码：0=PASS / 1=FAIL / 2=PENDING（依赖服务不可达，非功能缺陷）
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_BASE = "http://127.0.0.1:8000"
DEFAULT_OUT = Path(__file__).resolve().parent
ADMIN = ("admin", "admin123")

# 查询同时命中 R001（记忆关键词「我的」）、R002（知识库关键词「知识库/资料」，
# 需 kb_id 非空 —— 由本轮自动发现补足）、R004（偏好词「偏好」+ 实体）
DEFAULT_QUERY = "请结合我的偏好和知识库资料，说明会话编排的前置与回写闭环是怎么设计的？"

# 依赖服务健康端点（PENDING 判定用；不可达属环境问题，非功能缺陷）
DEPENDENCIES = {
    "openbase": "http://127.0.0.1:8000/openapi.json",
    "openllm": "http://127.0.0.1:8001/openllm/v1/health",
    "openrag": "http://127.0.0.1:8010/api/v1/system/health",
    "openmemory": "http://127.0.0.1:8020/health",
    "dps": "http://127.0.0.1:8030/health/liveness",
}

# 知识库样本标识（由 seed_kb_and_verify_rag.py 写入；用于旁证「装配内容来自知识库」）
KB_MARKER = "CONTEXT-BUDGET-4096"

# OpenLLM 网关 API Key（与 OpenBase settings.llm_api_key 同源，仅用于本脚本拉取追踪详情）
OPENLLM_API_KEY = "sk-openllm-openbase-gateway-key"
OPENLLM_BASE = "http://127.0.0.1:8001"


def call(
    method: str,
    url: str,
    body: dict[str, Any] | None = None,
    token: str | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 300,
) -> tuple[int, Any, dict[str, str]]:
    """HTTP 调用（返回 状态码 / 解析后载荷 / 响应头；网络异常返回 -1）"""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Accept", "application/json")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, _decode(resp.read()), dict(resp.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, _decode(exc.read()), dict(exc.headers or {})
    except Exception as exc:  # noqa: BLE001 - 网络层异常统一降为 -1
        return -1, f"{type(exc).__name__}: {exc}", {}


def _decode(raw: bytes) -> Any:
    text = raw.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _dig(payload: Any, *path: str, default: Any = None) -> Any:
    """安全取嵌套键（任一层缺失即返回 default）"""
    cursor = payload
    for key in path:
        if not isinstance(cursor, dict):
            return default
        cursor = cursor.get(key)
        if cursor is None:
            return default
    return cursor


def probe_dependencies() -> dict[str, Any]:
    """依赖服务连通性预检（不可达 → PENDING，非缺陷）"""
    report: dict[str, Any] = {}
    for name, url in DEPENDENCIES.items():
        status, _payload, _headers = call("GET", url, timeout=10)
        report[name] = status
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=os.environ.get("OB_BASE", DEFAULT_BASE))
    parser.add_argument("--out", default="")
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--mode", default="auto")
    parser.add_argument(
        "--nonce",
        default="none",
        help="查询取号（默认 none＝不注入）。auto 模式已由缓存准入收口豁免语义缓存，"
        "通常无需取号；需要强制区分查询时传入自定义值。",
    )
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    out_dir = Path(args.out) if args.out else DEFAULT_OUT
    out_dir.mkdir(parents=True, exist_ok=True)

    # 语义缓存短路规避：同一查询二次请求会命中 LLM 响应缓存（实测 716ms、无编排），
    # 使「装配 → 计量 → 投喂」链路的取证失效。此处默认注入一次性取号，**不改变**
    # 命中的路由关键词（我的 / 知识库 / 资料 / 偏好），仅保证缓存未命中。
    if args.nonce == "none":
        query_sent = args.query
        nonce = ""
    else:
        nonce = args.nonce or f"{int(time.time() * 1000):x}"
        query_sent = f"（本轮联调取号 {nonce}）{args.query}"

    evidence: dict[str, Any] = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "base_url": base,
        "mode": args.mode,
        "query": args.query,
        "query_sent": query_sent,
        "nonce": nonce,
        "dependencies": probe_dependencies(),
        "steps": [],
        "verdict": {},
    }

    unreachable = [
        name for name, status in evidence["dependencies"].items() if status != 200
    ]
    if unreachable:
        evidence["verdict"] = {
            "status": "PENDING",
            "reason": f"依赖服务不可达：{unreachable}",
            "exit_code": 2,
        }
        _write(out_dir, evidence)
        print(f"[PENDING] 依赖服务不可达：{unreachable}")
        return 2

    # ① 智能体主体接入：管理员登录 → 创建 agent（tenant_id=1 → tenant_code='tenant-1'）
    status, payload, _ = call(
        "POST", f"{base}/api/v1/auth/login",
        {"username": ADMIN[0], "password": ADMIN[1]},
    )
    admin_token = _dig(payload, "access_token") or _dig(
        payload, "data", "access_token"
    )
    evidence["steps"].append(
        {"step": "admin_login", "http": status, "token": bool(admin_token)}
    )
    if status != 200 or not admin_token:
        evidence["verdict"] = {
            "status": "FAIL", "reason": f"管理员登录失败 http={status}",
            "login_response": payload, "exit_code": 1,
        }
        _write(out_dir, evidence)
        print(f"[FAIL] 管理员登录失败 http={status}: {str(payload)[:300]}")
        return 1

    agent_username = f"ob_agent_ctx_{int(time.time()) % 1000000}"
    agent_status, agent_payload, _ = call(
        "POST",
        f"{base}/api/v1/identity/agents",
        {
            "username": agent_username,
            "display_name": "智能体对话全链路联调主体",
            "tenant_id": 1,
            "role": "admin",
            "key_name": "agent-ctx-e2e",
        },
        token=admin_token,
    )
    agent_key = _dig(agent_payload, "api_key", "raw_key")
    agent_info = {
        "step": "provision_agent",
        "http": agent_status,
        "username": agent_username,
        "agent_id": _dig(agent_payload, "agent_id"),
        "tenant_id": _dig(agent_payload, "tenant_id"),
        "tenant_code": _dig(agent_payload, "tenant_code"),
        "key_issued": bool(agent_key),
    }
    evidence["steps"].append(agent_info)
    if agent_status not in (200, 201) or not agent_key:
        evidence["verdict"] = {
            "status": "FAIL",
            "reason": f"智能体主体创建失败 http={agent_status}",
            "agent_response": agent_payload,
            "exit_code": 1,
        }
        _write(out_dir, evidence)
        print(f"[FAIL] 智能体主体创建失败 http={agent_status}: {str(agent_payload)[:300]}")
        return 1

    token = agent_key
    evidence["subject"] = {
        "kind": "agent",
        "username": agent_username,
        "tenant_code": agent_info["tenant_code"],
        "bearer": "sk-agent-***",
    }
    print(
        f"[1] 智能体主体就绪 agent_id={agent_info['agent_id']} "
        f"tenant_code={agent_info['tenant_code']}"
    )

    # ②③④⑤ 对话（mode=auto）
    started = time.perf_counter()
    status, payload, headers = call(
        "POST",
        f"{base}/api/v1/llm-proxy/chat",
        {"mode": args.mode, "query": query_sent, "output_mode": "llm_response"},
        token=token,
    )
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    evidence["steps"].append(
        {
            "step": "chat",
            "http": status,
            "elapsed_ms": elapsed_ms,
            "x_request_id": headers.get("X-Request-Id"),
        }
    )
    evidence["chat_response"] = payload

    checks: dict[str, Any] = {"chat_http": status}
    failures: list[str] = []

    if status != 200:
        # 上游超时/不可达在此显式区分，避免与功能缺陷混淆
        failures.append(f"H2 chat http={status}（响应={str(payload)[:200]}）")
        evidence["verdict"] = {
            "status": "FAIL", "checks": checks, "failures": failures, "exit_code": 1,
        }
        _write(out_dir, evidence)
        print(f"[FAIL] chat http={status} elapsed={elapsed_ms}ms")
        print(json.dumps(payload, ensure_ascii=False, indent=2)[:1500])
        return 1

    data = payload.get("data") if isinstance(payload, dict) else {}
    data = data or {}
    trace = data.get("routing_trace") or {}
    components = trace.get("components") or {}
    metrics = trace.get("context_metrics") or {}
    segment_tokens = metrics.get("segment_tokens") or {}
    rag_snapshot = metrics.get("rag") or {}
    memory_snapshot = metrics.get("memory") or {}
    content = str(data.get("content") or "")
    executed = list(trace.get("executed") or [])
    degraded = list(trace.get("degraded") or [])

    checks.update(
        {
            "code": payload.get("code"),
            "mode": data.get("mode"),
            "pipeline": data.get("pipeline"),
            "path": trace.get("path"),
            "decision": trace.get("decision"),
            "content_chars": len(content),
            "executed": executed,
            "degraded": degraded,
            "rag_source": components.get("rag_source"),
            "kb_id_source": components.get("kb_id_source"),
            "need_memory": components.get("need_memory"),
            "need_rag": components.get("need_rag"),
            "model": _dig(data, "model"),
            "usage": data.get("usage"),
            "context_metrics": metrics,
            "timeline": trace.get("timeline"),
            "writeback": trace.get("writeback"),
            "kb_marker_in_answer": KB_MARKER in content,
        }
    )

    # ---- 附：尽力拉取 OpenLLM 追踪详情（含时间线 spans；失败不影响判定） ----
    inner_request_id = data.get("request_id")
    if inner_request_id:
        trace_status, trace_payload, _ = call(
            "GET",
            f"{OPENLLM_BASE}/openllm/v1/trace/{inner_request_id}",
            headers={"Authorization": f"Bearer {OPENLLM_API_KEY}"},
            timeout=30,
        )
        evidence["openllm_trace"] = {"http": trace_status, "payload": trace_payload}
        if trace_status == 200:
            spans = _dig(trace_payload, "data", "timeline") or _dig(
                trace_payload, "data", "spans"
            )
            checks["timeline"] = spans

    # ---- 硬性判定 ----
    if payload.get("code") != 0:
        failures.append(f"H2 code={payload.get('code')}（应为 0）")
    if not content.strip():
        failures.append("H3 content 为空")
    if degraded:
        failures.append(f"H4 存在降级组件：{degraded}")
    missing = [name for name in ("memory", "rag", "llm") if name not in executed]
    if missing:
        failures.append(f"H5 实际执行组件缺 {missing}（executed={executed}）")
    if components.get("rag_source") != "external":
        failures.append(
            f"H6 rag_source={components.get('rag_source')}（应为 external）"
        )
    if components.get("kb_id_source") not in ("registry", "external"):
        failures.append(
            f"H7 kb_id_source={components.get('kb_id_source')}（应为 registry/external）"
        )
    if metrics.get("counted") is not True:
        failures.append(f"H8 分段计量未接线（counted={metrics.get('counted')}）")
    if int(rag_snapshot.get("injected_items") or 0) < 1 or int(
        segment_tokens.get("rag") or 0
    ) < 1:
        failures.append(
            "H9 知识库内容未进入 Prompt"
            f"（rag.injected_items={rag_snapshot.get('injected_items')}, "
            f"segment_tokens.rag={segment_tokens.get('rag')}）"
        )

    verdict = "PASS" if not failures else "FAIL"
    evidence["verdict"] = {
        "status": verdict,
        "checks": checks,
        "failures": failures,
        "exit_code": 0 if verdict == "PASS" else 1,
    }
    _write(out_dir, evidence)

    print("=== 智能体对话全链路 E2E ===")
    print(f"  status={verdict} http={status} elapsed={elapsed_ms}ms")
    print(
        f"  path={checks['path']} executed={executed} degraded={degraded}"
    )
    print(
        f"  need_memory={checks['need_memory']} need_rag={checks['need_rag']} "
        f"rag_source={checks['rag_source']} kb_id_source={checks['kb_id_source']}"
    )
    print(f"  model={checks['model']} usage={checks['usage']}")
    print(
        f"  segment_tokens={segment_tokens} contexts_tokens={metrics.get('contexts_tokens')}"
    )
    print(
        f"  rag.injected_items={rag_snapshot.get('injected_items')} "
        f"memory.injected_items={memory_snapshot.get('injected_items')}"
    )
    print(f"  attribution={metrics.get('attribution_a')}")
    print(f"  writeback={checks['writeback']}")
    print(f"  timeline={checks['timeline']}")
    print(f"  content[:200]={content[:200]!r}")
    if failures:
        print("  failures:")
        for item in failures:
            print(f"    - {item}")
    print(f"  evidence: {out_dir / 'agent-context-e2e.json'}")
    return int(evidence["verdict"]["exit_code"])


def _write(out_dir: Path, payload: dict[str, Any]) -> None:
    (out_dir / "agent-context-e2e.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    sys.exit(main())
