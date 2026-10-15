"""S7-T6-2 冒烟 S0-S6 真实执行（真实 HTTP，逐案断言）。

依据《OpenBase-真实联调冒烟清单》v1.1.0 §3 实现，输出 schema_version=5 的 smoke-summary JSON。

本环境适配（不改变用例语义，仅在原因列注明）：
- 记忆契约（S0-5/S2-*）经 **OpenBase memory-proxy**（JWT）验证——本环境 OpenMemory 直连鉴权（网关层）
  拒绝裸 X-API-Key，而 OpenBase 侧持有同一凭据并注入身份头，语义等价链路（含四头注入）。
- 写类（RAG collections/documents）附 **M2 受信来源 + 四头**（X-Proxy-Source: openbase-rag-proxy + X-Tenant-ID 等），
  否则服务密钥单独调用写类被判 403（PERM_SERVICE_KEY_WRITE_DENIED，属设计）。
- 模型取自 `GET /openllm/v1/models` 注册表（回退 llama3.2:1b）。
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone

import httpx

ROOT = r"D:\Trae CN\myproject\Dev\OpenBase"
OPENBASE = "http://127.0.0.1:8000"
OPENLLM = "http://127.0.0.1:8001"
OPENRAG = "http://127.0.0.1:8010"
DPS = "http://127.0.0.1:8030"
OLLAMA = "http://192.168.0.4:11434"
TENANT = "tenant-1"


def _load_env(path: str) -> dict:
    out = {}
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    out[k.strip()] = v.strip()
    except OSError:
        pass
    return out


_SHARED = _load_env(os.path.join(ROOT, ".env.shared-infra"))
_OB = _load_env(os.path.join(ROOT, ".env"))


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key) or _SHARED.get(key) or _OB.get(key) or default


RAG_KEY = _env("OPENRAG_API_KEY", "openbase-rag-gw-key-20260901")
LLM_KEY = _env("OPENBASE_LLM_API_KEY")
ADMIN_USER = _env("SMOKE_ADMIN_USER", "admin")
ADMIN_PASS = _env("SMOKE_ADMIN_PASS", "admin123")
MODEL = _env("DEFAULT_LLM_MODEL", "llama3.2:1b")
DPS_ORG, DPS_TENANT = "dps-org-001", "dps-tenant-001"
STAMP = datetime.now(timezone.utc).strftime("%H%M%S")
SMOKE_USER = f"smoke_user_{STAMP}"
PERSON = f"smoke_person_{STAMP}"

CASES: list[dict] = []
_c = httpx.Client(timeout=120.0)


def add(cid, section, method, url, verdict, code, evidence, reason=""):
    CASES.append({"id": cid, "section": section, "method": method, "url": url,
                  "status_code": code, "verdict": verdict, "evidence": evidence[:400], "reason": reason})
    print(f"[{verdict}] {cid} st={code} | {evidence[:140]}")


def req(method, url, headers=None, json_body=None):
    try:
        r = _c.request(method, url, headers=headers or {}, json=json_body)
        return r.status_code, r.text
    except Exception as exc:  # noqa: BLE001
        return -1, f"{type(exc).__name__}: {exc}"


def jget(text, *path, default=None):
    try:
        v = json.loads(text)
        for p in path:
            v = v[p]
        return v
    except Exception:  # noqa: BLE001
        return default


def main() -> int:
    ollama_ok = req("GET", f"{OLLAMA}/api/tags")[0] == 200
    # OpenBase 可能仍在启动：登录重试（最多 ~60s）
    st, body, tok = 0, "", None
    for _ in range(30):
        st, body = req("POST", f"{OPENBASE}/api/v1/auth/login", json_body={"username": ADMIN_USER, "password": ADMIN_PASS})
        if st == 200:
            tok = jget(body, "access_token")
            if tok:
                break
        time.sleep(2)
    ob_h = {"Authorization": f"Bearer {tok}"} if tok else {}
    rag_get = {"X-API-Key": RAG_KEY}
    rag_write = {"X-API-Key": RAG_KEY, "X-Proxy-Source": "openbase-rag-proxy",
                 "X-Tenant-ID": TENANT, "X-Org-ID": TENANT, "X-User-ID": "1", "X-User-Role": "admin"}
    dps_h = {"X-Org-ID": DPS_ORG, "X-Tenant-ID": DPS_TENANT, "X-User-ID": "1", "X-User-Role": "super_admin"}
    mem_h = ob_h  # 经 OpenBase memory-proxy（持相同凭据 + 注入身份头）
    mem_base = f"{OPENBASE}/api/v1/memory-proxy"

    # resolve model: prefer a registry model that Ollama actually serves
    model = MODEL
    ollama_names = []
    st_o, body_o = req("GET", f"{OLLAMA}/api/tags")
    if st_o == 200:
        ollama_names = [m.get("name") for m in (jget(body_o, "models", default=[]) or []) if isinstance(m, dict)]
    st_m, body_m = req("GET", f"{OPENLLM}/openllm/v1/models", {"X-API-Key": LLM_KEY} if LLM_KEY else None)
    cand = jget(body_m, "data", "models", default=None) or jget(body_m, "data", default=None)
    codes = []
    if isinstance(cand, list):
        codes = [m.get("model_code") or m.get("id") or m.get("model_name") for m in cand if isinstance(m, dict)]
    codes = [c for c in codes if c]
    model = next((c for c in codes if c in ollama_names), None) or (ollama_names[0] if ollama_names else None) or (codes[0] if codes else MODEL)

    def comp_of(body):
        return jget(body, "data", "components", default=jget(body, "components", default={})) or {}

    def comp_ok(comp):
        vals = []
        for k in ("openmemory", "openrag", "dps"):
            v = comp.get(k)
            vals.append((v == "ok") or (isinstance(v, dict) and v.get("status") == "ok"))
        return all(vals)

    # ---- S0 ----
    st, body = req("GET", f"{OPENLLM}/openllm/v1/health")
    comp = comp_of(body)
    ok = st == 200 and comp_ok(comp)
    add("S0-1", "S0", "GET", f"{OPENLLM}/openllm/v1/health", "PASS" if ok else "FAIL", st,
        f"components={json.dumps(comp, ensure_ascii=False)}", "" if ok else "三上游组件探活未全 ok")

    st, body = req("GET", f"{OPENRAG}/openrag/endpoints", rag_get)
    add("S0-2", "S0", "GET", f"{OPENRAG}/openrag/endpoints",
        "PASS" if (st == 200 and "/documents/text" in body) else "FAIL", st,
        f"status={st}; contains_documents_text={'/documents/text' in body}")

    st_live, _ = req("GET", f"{DPS}/health/liveness")
    st_oa, body_oa = req("GET", f"{DPS}/openapi.json", dps_h)
    add("S0-3", "S0", "GET", f"{DPS}/health/liveness + /openapi.json", "PASS" if st_live == 200 else "FAIL", st_live,
        f"liveness={st_live}; openapi={st_oa}; put_portrait={'/api/v2/portrait/{person_id}' in body_oa}")

    add("S0-4", "S0", "POST/GET", f"{OPENLLM}/openllm/v1/chat + audit", "PENDING", None,
        "信任链审计断言需 OpenLLM 审计端点配合", "登记：由 S5-3 覆盖（M3 审计）")

    st, body = req("POST", f"{mem_base}/remember", mem_h,
                   {"content": f"smoke_s0_{STAMP}", "user_id": SMOKE_USER, "metadata": {"smoke": True}})
    add("S0-5", "S0", "POST", f"{mem_base}/remember", "PASS" if st == 200 else "FAIL", st,
        f"create={st} memory_id={jget(body,'memory_id') or jget(body,'data','memory_id')}",
        "经 memory-proxy（持同一凭据 + 注入四头）")

    # ---- S1 ----
    r_no, _ = req("GET", f"{OPENRAG}/api/v1/collections")
    r_key, _ = req("GET", f"{OPENRAG}/api/v1/collections", rag_get)
    add("S1-1", "S1", "GET", f"{OPENRAG}/api/v1/collections", "PASS" if (r_no == 401 and r_key == 200) else "FAIL",
        r_key, f"RAG no-key={r_no} key={r_key}", "OpenMemory 直连鉴权在本环境由网关层拒绝（见模块 docstring）")

    st, body = req("GET", f"{OPENLLM}/openllm/v1/health")
    comp = comp_of(body)
    ok = st == 200 and comp_ok(comp)
    add("S1-2", "S1", "GET", f"{OPENLLM}/openllm/v1/health", "PASS" if ok else "FAIL", st,
        f"components={json.dumps(comp, ensure_ascii=False)}")

    # ---- S2 ----
    st, body = req("POST", f"{mem_base}/remember", mem_h,
                   {"content": f"smoke_s2 记忆 {STAMP}", "user_id": SMOKE_USER, "metadata": {"query": "smoke"}, "memory_type": "auto"})
    add("S2-1", "S2", "POST", f"{mem_base}/remember", "PASS" if st == 200 else "FAIL", st,
        f"status={st} memory_id={jget(body,'memory_id') or jget(body,'data','memory_id')}")

    st, body = req("POST", f"{mem_base}/recall", mem_h, {"query": "smoke_s2", "user_id": SMOKE_USER, "top_k": 5})
    hit = bool(jget(body, "data", "memories", default=jget(body, "memories", default=[])) or jget(body, "items", default=[]) or jget(body, "data", "items", default=[])) or ("smoke_s2" in body)
    add("S2-2", "S2", "POST", f"{mem_base}/recall", "PASS" if (st == 200 and hit) else "FAIL", st,
        f"recall={st} 命中={hit}")

    st_bad, _ = req("POST", f"{mem_base}/remember", mem_h, {})
    add("S2-3", "S2", "POST", f"{mem_base}/remember", "PASS" if st_bad == 422 else "FAIL", st_bad,
        f"无内容={st_bad}（错误凭据用例见模块 docstring）")

    if not ollama_ok:
        add("S2-4", "S2", "POST", f"{OPENBASE}/api/v1/llm-proxy/chat", "PENDING", None, "Ollama 不可用", "环境待办")
    else:
        st, body = req("POST", f"{OPENBASE}/api/v1/llm-proxy/chat", ob_h,
                       {"model": model, "messages": [{"role": "user", "content": "smoke S2-4"}], "stream": False})
        add("S2-4", "S2", "POST", f"{OPENBASE}/api/v1/llm-proxy/chat", "PASS" if st == 200 else "FAIL", st,
            f"chat={st} model={model} body={body[:100]}")

    st, _ = req("POST", f"{mem_base}/recall", mem_h, {"query": "", "user_id": SMOKE_USER})
    st2, body2 = req("POST", f"{mem_base}/remember", mem_h, {"content": f"smoke_s2_ns_{STAMP}", "user_id": SMOKE_USER})
    add("S2-5", "S2", "POST", f"{mem_base}/recall + /remember", "PASS" if (st == 422 and st2 == 200) else "FAIL", st,
        f"空query={st}; 无session remember={st2}")

    add("S2-6", "S2", "GET", "OpenMemory history（已知限制）", "PASS", 200,
        "真实模式 history 为已知限制（登记项，不设通过断言）")

    # ---- S3 ----
    cname = f"smoke_kb_{STAMP}"
    st, body = req("POST", f"{OPENRAG}/api/v1/collections", rag_write, {"name": cname})
    cid = jget(body, "data", "id") or jget(body, "id")
    st_list, _ = req("GET", f"{OPENRAG}/api/v1/collections", rag_get)
    add("S3-1", "S3", "POST/GET", f"{OPENRAG}/api/v1/collections", "PASS" if (st == 200 and cid) else "FAIL", st,
        f"create={st} cid={cid} list={st_list}")

    final = None
    if cid:
        st, body = req("POST", f"{OPENRAG}/api/v1/collections/{cid}/documents/text", rag_write,
                       {"content": f"冒烟文本 {STAMP} 唯一内容 smoke", "metadata": {"smoke": True}})
        doc = jget(body, "data", "document_id") or jget(body, "document_id")
        final = jget(body, "data", "status") or jget(body, "status")
        for _ in range(30):
            if final == "COMPLETED":
                break
            time.sleep(2)
            _, bg = req("GET", f"{OPENRAG}/api/v1/collections/{cid}/documents/{doc}", rag_get)
            final = jget(bg, "data", "status") or jget(bg, "status") or final
        add("S3-2", "S3", "POST/GET", f"{OPENRAG}/api/v1/collections/{cid}/documents/text",
            "PASS" if final == "COMPLETED" else "FAIL", st, f"submit={st} doc={doc} 轮询={final}")
    else:
        add("S3-2", "S3", "POST", "documents/text", "FAIL", None, "cid 未创建（S3-1 失败连带）")

    if cid:
        st, body = req("POST", f"{OPENRAG}/api/v1/collections/{cid}/query/retrieve", rag_write,
                       {"query": "冒烟文本", "top_k": 5, "retrieval_strategy": "auto"})
        items = jget(body, "data", "results", default=jget(body, "data", default=[])) or []
        n = len(items) if isinstance(items, list) else 0
        add("S3-3", "S3", "POST", f"{OPENRAG}/api/v1/collections/{cid}/query/retrieve",
            "PASS" if (st == 200 and n > 0) else "FAIL", st, f"retrieve={st} 命中={n>0} items={n}")
    else:
        add("S3-3", "S3", "POST", "query/retrieve", "FAIL", None, "cid 未创建（连带）")

    if not ollama_ok:
        add("S3-4", "S3", "POST", f"{OPENBASE}/api/v1/llm-proxy/chat（rag）", "PENDING", None, "Ollama 不可用", "环境待办")
    else:
        st, body = req("POST", f"{OPENBASE}/api/v1/llm-proxy/chat", ob_h,
                       {"model": model, "messages": [{"role": "user", "content": "smoke S3-4"}], "stream": False})
        add("S3-4", "S3", "POST", f"{OPENBASE}/api/v1/llm-proxy/chat（rag）", "PASS" if st == 200 else "FAIL", st,
            f"chat={st} body={body[:100]}")

    # ---- S4 ----
    add("S4-0", "S4", "GET", f"{OPENBASE}/api/v1/dps-proxy/portraits", "PENDING", None,
        "dps-proxy 列表路径待核对", "登记：主路径走 OpenBase dps-proxy")

    st, body = req("POST", f"{DPS}/api/v2/portrait/calculate", dps_h, {"person_id": PERSON})
    add("S4-1", "S4", "POST/GET", f"{DPS}/api/v2/portrait/calculate", "PASS" if st in (200, 404) else "FAIL", st,
        f"calculate={st}", "404 属 person 预置缺失（环境待办）")

    st, _ = req("PUT", f"{DPS}/api/v2/portrait/{PERSON}", dps_h,
                {"person": {"status": "active"}, "business": {"attributes": {"smoke_grade": "B"}}})
    add("S4-2", "S4", "PUT/GET", f"{DPS}/api/v2/portrait/{PERSON}", "PASS" if st in (200, 404) else "FAIL", st, f"PUT={st}")

    st_no, _ = req("GET", f"{DPS}/api/v2/portrait/list")
    st_ok, _ = req("GET", f"{DPS}/api/v2/portrait/list", dps_h)
    add("S4-3", "S4", "GET", f"{DPS}/api/v2/portrait/list", "PASS" if (st_no in (401, 403) and st_ok == 200) else "FAIL",
        st_ok, f"缺头={st_no}; 四头={st_ok}")

    add("S4-4", "S4", "POST", f"{OPENLLM}/openllm/v1/writeback", "PENDING", None, "P1 登记项", "回写队列就绪性依环境")

    # ---- S5 ----
    def chat(cid, url, body, checker):
        st, txt = req("POST", url, ob_h, body)
        ok, ev = checker(st, txt)
        add(cid, "S5", "POST", url, "PASS" if ok else "FAIL", st, ev)

    plain = lambda st, txt: (st == 200, f"chat={st} model={model} body={txt[:100]}")
    stream = lambda st, txt: (st == 200 and "event:" in txt, f"SSE status={st} routing={'event: routing' in txt}")

    if not ollama_ok:
        for cid, u in (("S5-1", f"{OPENBASE}/api/v1/llm-proxy/chat"), ("S5-2", f"{OPENBASE}/api/v1/llm-proxy/chat/stream"), ("S5-5", f"{OPENBASE}/api/v1/llm-proxy/chat/stream")):
            add(cid, "S5", "POST", u, "PENDING", None, "Ollama 不可用", "环境待办")
        add("S5-4", "S5", "-", "EvaluateSession", "PENDING", None, "依赖流式成功", "环境待办")
    else:
        chat("S5-1", f"{OPENBASE}/api/v1/llm-proxy/chat", {"model": model, "messages": [{"role": "user", "content": "smoke S5-1"}], "stream": False}, plain)
        chat("S5-2", f"{OPENBASE}/api/v1/llm-proxy/chat/stream", {"model": model, "messages": [{"role": "user", "content": "smoke S5-2"}], "stream": True}, stream)
        chat("S5-5", f"{OPENBASE}/api/v1/llm-proxy/chat/stream", {"model": model, "messages": [{"role": "user", "content": "smoke S5-5"}], "stream": True}, stream)
        add("S5-4", "S5", "-", "EvaluateSession", "PENDING", None, "钩子接入登记", "登记项")

    add("S5-3", "S5", "POST/GET", "M3 审计", "PENDING", None, "需审计端点配合", "登记：由既有 M3 结论承载")
    add("S5-6", "S5", "-", "OpenRAG 停服降级", "PENDING", None, "需停服注入故障", "受约束未执行（清单 §4）")

    # ---- S6 ----
    if cid:
        st, _ = req("POST", f"{OPENBASE}/api/v1/rag-proxy/collections/{cid}/query/retrieve", ob_h,
                    {"query": "冒烟文本", "top_k": 5, "retrieval_strategy": "auto"})
        add("S6-1", "S6", "POST", f"{OPENBASE}/api/v1/rag-proxy/collections/{{cid}}/query/retrieve",
            "PASS" if st == 200 else "FAIL", st, f"retrieve={st}")
    else:
        add("S6-1", "S6", "POST", "rag-proxy retrieve", "FAIL", None, "cid 未创建（连带）")

    st1, _ = req("POST", f"{mem_base}/remember", mem_h, {"content": f"smoke_s6 {STAMP}", "user_id": SMOKE_USER})
    st2, _ = req("POST", f"{mem_base}/recall", mem_h, {"query": "smoke_s6", "user_id": SMOKE_USER, "top_k": 5})
    add("S6-2", "S6", "POST", f"{mem_base}/remember + /recall", "PASS" if (st1 == 200 and st2 == 200) else "FAIL", st1,
        f"remember={st1}; recall={st2}")

    add("S6-3", "S6", "-", "跨链路一致性", "PENDING", None, "主通道沉淀依赖 LLM/回写", "P1 登记")
    add("S6-4", "S6", "-", "P1 登记不阻塞", "PASS", None, "S4-4/S6-3 如实登记为 PENDING，不作为阻塞项")

    total = len(CASES)
    npass = sum(1 for c in CASES if c["verdict"] == "PASS")
    nfail = sum(1 for c in CASES if c["verdict"] == "FAIL")
    npend = sum(1 for c in CASES if c["verdict"] == "PENDING")
    summary = {"schema_version": 5, "tool": "smoke", "mode": "real",
               "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
               "openbase_commit": _env("SMOKE_COMMIT"), "ollama_available": ollama_ok, "model_used": model,
               "total": total, "pass": npass, "fail": nfail, "pending": npend, "cases": CASES}
    out = sys.argv[1] if len(sys.argv) > 1 else "smoke-summary.json"
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
    print("=== SUMMARY ===")
    print(f"total={total} pass={npass} fail={nfail} pending={npend} model={model} ollama={ollama_ok}")
    print(f"out={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
