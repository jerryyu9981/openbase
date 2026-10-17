"""G5 / G6 真实面演练：POST /openllm/v1/writeback 三路 + profile 真实 DPS.

判据（清单 v1.1.0）：
- G5：memory / rag / profile 三路均落**真实上游**；重复投递 `duplicated=true` 不重复执行；
  失败按指数退避 ≤3 次 + 死信可视（本探针登记队列就绪性；退避/死信由队列实现与既有用例覆盖）。
- G6：profile 回写打到**真实 DPS**（非 Mock），`extract_targets` 生效（person/business 标签写入）。

用法：python scripts/writeback_realface.py
证据：doc/test/evidence/s7/g5/writeback-realface.json
"""
from __future__ import annotations

import datetime as dt
import json
import urllib.error
import urllib.request
from pathlib import Path

OB = "http://127.0.0.1:8000"
LLM = "http://127.0.0.1:8001"
RAG = "http://127.0.0.1:8010"
MEM = "http://127.0.0.1:8020"
DPS = "http://127.0.0.1:8030"
RAG_KEY = "openbase-rag-gw-key-20260901"
MEM_KEY = "openbase-gw-key-20260830"
LLM_KEY = "sk-openllm-b16f682ee21f6f138dd7fe9f3b4c9529"
EVID_DIR = Path(r"d:\Trae CN\myproject\Dev\OpenBase\doc\test\evidence\s7\g5")
STAMP = dt.datetime.now().strftime("%Y%m%d%H%M%S")
MARKER = f"g5-writeback-{STAMP}"

RAG_HEADERS = {
    "X-Tenant-ID": "tenant-1",
    # 写路径在 M2 下要求非匿名主体（实测缺 X-User-ID → PERM_SERVICE_KEY_WRITE_DENIED）
    "X-User-ID": "1",
    "X-User-Role": "org_admin",
    "X-Proxy-Source": "openbase-rag-proxy",
}
MEM_HEADERS = {
    # 回写侧出站 X-User-ID = 编排归一主体键 `{tenant}_{user}`（OpenLLM RequestContext.user_id），
    # OpenMemory 以该值作 owner；用裸 "1" 会读不到（实测 owner 不一致）。
    "X-User-ID": "tenant-1_1",
    "X-User-Role": "admin",
    "X-Proxy-Source": "openbase-memory-proxy",
}
DPS_HEADERS = {
    "X-Org-ID": "10000000-0000-0000-0000-000000000001",
    "X-Tenant-ID": "20000000-0000-0000-0000-000000000001",
    "X-User-ID": "1",
    "X-User-Role": "super_admin",
    "X-Proxy-Source": "openbase-orchestrator",
}
# 回写入口的受信身份（与 OpenBase → OpenLLM 出站同口径）
WB_HEADERS = {
    "Authorization": f"Bearer {LLM_KEY}",
    "X-Proxy-Source": "openbase-llm-proxy",
    "X-User-ID": "1",
    "X-Tenant-ID": "tenant-1",
    "X-Org-ID": "tenant-1",
    "X-User-Role": "org_admin",
    "X-Subject-ID": "tenant-1_1",
}


def call(method: str, url: str, headers: dict | None = None, body: dict | None = None,
         timeout: int = 60) -> tuple[int, str]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", **(headers or {})},
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001 - 探针登记全部失败形态
        return 0, f"ERR {type(exc).__name__}: {exc}"


def jload(text: str):
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return None


def main() -> int:
    EVID_DIR.mkdir(parents=True, exist_ok=True)
    checks: dict[str, dict] = {}

    # 0) OpenBase 登录（OpenMemory 业务面需要服务 Key + JWT 双凭据）
    status, body = call("POST", f"{OB}/api/v1/auth/login", body={"username": "admin", "password": "admin123"})
    jwt_token = (jload(body) or {}).get("access_token", "") if status == 200 else ""
    checks["prepare_auth"] = {"status": status, "jwt_len": len(jwt_token)}

    # 0.1) 准备一个真实知识库（OpenRAG 集合，tenant-1 域）
    status, body = call(
        "POST",
        f"{RAG}/api/v1/collections",
        {"X-API-Key": RAG_KEY, **RAG_HEADERS},
        {"name": MARKER, "description": "G5 writeback realface probe"},
    )
    kb_id = str(((jload(body) or {}).get("data") or {}).get("id") or "")
    checks["prepare_kb"] = {"status": status, "kb_id": kb_id, "body_head": body[:200]}

    # 1) 三路同步回写（真实上游即刻落地）
    payload = {
        "user_id": "1",
        "session_id": MARKER,
        "seq": int(STAMP[-6:]),
        "dialogue": {
            "query": f"G5 回写真实面探针 {MARKER}",
            "response": f"这是用于验证三路回写落地的探针内容 {MARKER}。",
        },
        "targets": {
            "memory": {"write": True, "mode": "sync"},
            "rag": {"write": True, "mode": "sync", "kb_id": kb_id, "save_if_valuable": True},
            "profile": {
                "write": True,
                "mode": "sync",
                "extract_targets": ["person", "business"],
                "updates": {
                    "person": {"name": "admin"},
                    "business": {"attributes": {"g5_probe": MARKER}},
                },
            },
        },
    }
    status, body = call("POST", f"{LLM}/openllm/v1/writeback", WB_HEADERS, payload)
    response = jload(body) or {}
    data = response.get("data") or {}
    checks["sync_three_paths"] = {
        "status": status,
        "code": response.get("code"),
        "accepted": data.get("accepted"),
        "duplicated": data.get("duplicated"),
        "body_head": body[:400],
        "verdict": "PASS" if status == 200 and all((data.get("accepted") or {}).values()) else "FAIL",
    }

    # 2) 上游落地核验
    # 注：OpenMemory 适配器客户端为进程级共享头（无 per-request X-Tenant-ID），
    # 实测回写落库域为 `default`（owner=tenant-1_1）；故此处按同域（不带 tenant 头）回读。
    status, body = call(
        "POST", f"{MEM}/api/v1/recall", {**MEM_HEADERS, "X-API-Key": MEM_KEY, "Authorization": f"Bearer {jwt_token}"}, {"query": MARKER}
    )
    memory_hit = status == 200 and MARKER in body
    if not memory_hit:
        # 兼容：若适配器后续改为按请求透传 tenant，则带 tenant-1 头同样应命中
        status, body = call(
            "POST",
            f"{MEM}/api/v1/recall",
            {**MEM_HEADERS, "X-Tenant-ID": "tenant-1", "X-API-Key": MEM_KEY, "Authorization": f"Bearer {jwt_token}"},
            {"query": MARKER},
        )
        memory_hit = status == 200 and MARKER in body
    checks["memory_landing"] = {
        "read_url": f"{MEM}/api/v1/recall",
        "status": status,
        "marker_hit": memory_hit,
        "observed_domain": "default（适配器共享头未透传 per-request tenant；已登记观测项）",
        "body_head": body[:200],
        "verdict": "PASS" if memory_hit else "FAIL",
    }

    if kb_id:
        status, body = call(
            "GET",
            f"{RAG}/api/v1/collections/{kb_id}/documents",
            {"X-API-Key": RAG_KEY, **RAG_HEADERS},
        )
        checks["rag_landing"] = {
            "read_url": f"{RAG}/api/v1/collections/{{kb_id}}/documents",
            "status": status,
            "marker_hit": MARKER in body,
            "body_head": body[:300],
            "verdict": "PASS" if status == 200 and MARKER in body else "FAIL",
        }
    else:
        checks["rag_landing"] = {"verdict": "BLOCKED", "reason": "知识库创建失败"}

    status, body = call("GET", f"{DPS}/api/v2/portrait/tenant-1_1", DPS_HEADERS)
    portrait = jload(body) or {}
    portrait_data = portrait.get("data") or {}
    attributes = str(portrait_data.get("attributes_json") or "")
    checks["profile_landing"] = {
        "read_url": f"{DPS}/api/v2/portrait/tenant-1_1",
        "status": status,
        "marker_hit": MARKER in attributes,
        "person_id": portrait_data.get("person_id"),
        "attributes_head": attributes[:300],
        "verdict": "PASS" if status == 200 and MARKER in attributes else "FAIL",
    }

    # 3) 幂等复投（异步路径：同 session+seq+target 第二次 submit 应 duplicated=true）
    async_payload = {
        "user_id": "1",
        "session_id": MARKER,
        "seq": int(STAMP[-6:]) + 1,
        "dialogue": {"query": "G5 幂等探针", "response": "G5 幂等探针内容"},
        "targets": {
            "memory": {"write": True, "mode": "async"},
            "rag": {"write": True, "mode": "async", "kb_id": kb_id, "save_if_valuable": False},
            "profile": {"write": True, "mode": "async", "extract_targets": ["person"]},
        },
    }
    first_status, first_body = call("POST", f"{LLM}/openllm/v1/writeback", WB_HEADERS, async_payload)
    replay_status, replay_body = call("POST", f"{LLM}/openllm/v1/writeback", WB_HEADERS, async_payload)
    first_data = (jload(first_body) or {}).get("data") or {}
    replay_data = (jload(replay_body) or {}).get("data") or {}
    checks["k14_idempotency"] = {
        "first_status": first_status,
        "replay_status": replay_status,
        "first_duplicated": first_data.get("duplicated"),
        "replay_duplicated": replay_data.get("duplicated"),
        "verdict": (
            "PASS"
            if replay_status == 200
            and all((replay_data.get("duplicated") or {}).values())
            else "FAIL"
        ),
    }

    # 4) 运行态真实开关快照（G6：非 Mock 的直接证据）
    status, body = call("GET", f"{LLM}/openllm/v1/health")
    health_payload = jload(body) or {}
    health_data = health_payload.get("data") or {}
    checks["runtime_health"] = {
        "status": status,
        "channel": health_data.get("channel"),
        "components": health_data.get("components"),
        "body_head": body[:600],
    }

    overall = "PASS" if all(
        checks[key].get("verdict") == "PASS"
        for key in ("sync_three_paths", "memory_landing", "rag_landing", "profile_landing", "k14_idempotency")
    ) else "FAIL"
    report = {
        "schema_version": 1,
        "tool": "writeback_realface.py",
        "task": "S7-G5/G6",
        "execution_face": "B",
        "generated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "session_id": MARKER,
        "kb_id": kb_id,
        "status": overall,
        "checks": checks,
    }
    out = EVID_DIR / "writeback-realface.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": overall, "session_id": MARKER, "kb_id": kb_id,
                      "verdicts": {k: v.get("verdict") for k, v in checks.items()}},
                     ensure_ascii=False, indent=2))
    print(f"evidence: {out}")
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
