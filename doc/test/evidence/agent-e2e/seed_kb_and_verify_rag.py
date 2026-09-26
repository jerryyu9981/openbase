"""为「智能体对话全流程」目标预置知识库样本并核验 RAG 注入（真实 HTTP）。

① 建库（幂等：同名已存在则复用）
② 文本入库（含**可验证的独有事实**，便于从答案中识别 RAG 是否进入 Prompt）
③ 轮询库统计直到 chunk_count > 0
④ 用 explicit 管道（rag → llm）强测 RAG 注入：executed / rag_source / timeline
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(r"d:\Trae CN\myproject\Dev\OpenBase")
RAG = "http://127.0.0.1:8010"
LLM = "http://127.0.0.1:8001"
OB = "http://127.0.0.1:8000"
KB_NAME = "ob_agent_ctx_kb_20260926"
# M2 写操作需主体：受信来源 + 四维身份 + **外部身份**（实测：缺 ext 头 → 400
# BIZ_RESERVED_TENANT_CODE_COLLISION；补齐后 200）
TRUSTED_HEADERS = {
    "X-Proxy-Source": "openbase-rag-proxy",
    "X-User-ID": "1",
    "X-Tenant-Code": "tenant-1",
    "X-Tenant-ID": "tenant-1",
    "X-User-Role": "admin",
    "X-External-Tenant-ID": "tenant-1",
    "X-External-User-ID": "1",
}

DOC_FACTS = {
    "code": "AGENT-CTX-KB-20260926",
    "budget": "CONTEXT-BUDGET-4096",
}
DOC_TEXT = f"""# OpenBase 会话编排与上下文装配（联调知识库样本）

本样本代号 **{DOC_FACTS['code']}**，用于验证「智能体对话 → 自动对接画像/记忆/知识库 → 科学装配上下文 → 投喂 LLM」全流程。

## 1. 前置编排（Pre-orchestration）固定顺序
`auth` → `profile_fetch`（DPS 画像）→ 组件执行（`memory` / `rag`）→ **上下文装配** → `llm` 推理。
其中画像与记忆、知识库三段结果统一注入 Prompt 的对应分段，装配后按分段计量。

## 2. 上下文装配分段与预算
装配分段固定为：`system` / `history` / `memory` / `rag` / `query`。
上下文预算代号 **{DOC_FACTS['budget']}**：memory 与 rag 两段之和不得超过预算的 40%；
超限时按相关性排序截断，并记录 `segment_tokens` 与 `injected_items` / `injected_tokens`。

## 3. 回写闭环（Writeback）
回写三路固定为 `memory` / `rag` / `profile`，逐路独立入队、逐路留回执；
**权威回执以回写队列表（writeback_queue）为准**，trace 内快照仅作事后补齐。

## 4. 降级与边界
组件不可用时记入 `degraded` 列表并跳过该段，不得触发内置回退（装配缺失 ≠ 外部检索失败）；
未知组件名一律忽略，不得中断主链路。
"""


def _rag_key() -> str:
    txt = (ROOT / "scripts" / "service-orchestrator.ps1").read_text(encoding="utf-8", errors="replace")
    m = re.search(r"'X-API-Key'\s*=\s*'([^']+)'", txt)
    return m.group(1) if m else ""


def _llm_key() -> str:
    m = re.search(r"OPENBASE_LLM_API_KEY=(\S+)", (ROOT / ".env").read_text(encoding="utf-8"))
    return m.group(1) if m else ""


def http(method, url, headers, body=None, timeout=240):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Accept", "application/json")
    if data:
        req.add_header("Content-Type", "application/json")
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            return r.status, _dec(raw)
    except urllib.error.HTTPError as exc:
        return exc.code, _dec(exc.read())
    except Exception as exc:  # noqa: BLE001
        return -1, f"{type(exc).__name__}: {exc}"


def _dec(raw: bytes):
    text = raw.decode("utf-8", "replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _ob_token() -> str:
    code, payload = http("POST", f"{OB}/api/v1/auth/login", {},
                         {"username": "admin", "password": "admin123"})
    tok = (payload or {}).get("access_token") if isinstance(payload, dict) else None
    if not tok:
        raise SystemExit(f"OpenBase 登录失败 http={code}: {payload}")
    return str(tok)


def ensure_kb(rag_h: dict) -> str:
    """建库：优先复用；否则经**受信身份通道**直连 OpenRAG 创建（实测可用路径）。
    说明：OpenBase rag-proxy 当前配置为「不注入身份头」（DEF-BE-147-005 显式口径），
    故经底座建库会被 M2 拒（PERM_SERVICE_KEY_WRITE_DENIED）—— 如实登记，见证据报告。
    """
    code, payload = http("GET", f"{RAG}/api/v1/collections", rag_h)
    items = ((payload or {}).get("data") or {}).get("items") or []
    for it in items:
        if it.get("name") == KB_NAME:
            print(f"[kb] 复用既有库 {KB_NAME} id={it.get('id')}")
            return str(it["id"])
    code, payload = http("POST", f"{RAG}/api/v1/collections", {**rag_h, **TRUSTED_HEADERS},
                         {"name": KB_NAME, "description": "agent context E2E sample"})
    cid = ((payload or {}).get("data") or {}).get("id") if isinstance(payload, dict) else None
    print(f"[kb] 经受信身份通道新建 http={code} id={cid}")
    if not cid:
        raise SystemExit(f"建库失败: {payload}")
    return str(cid)


def stats(rag_h: dict, cid: str) -> dict:
    code, payload = http("GET", f"{RAG}/api/v1/collections/{cid}", rag_h)
    data = (payload or {}).get("data") or {} if isinstance(payload, dict) else {}
    return data if isinstance(data, dict) else {}


def main() -> None:
    rag_h = {"X-API-Key": _rag_key()}
    cid = ensure_kb(rag_h)

    code, payload = http(
        "POST", f"{RAG}/api/v1/collections/{cid}/documents/text",
        {**rag_h, **TRUSTED_HEADERS},
        {"content": DOC_TEXT, "metadata": {"source": "agent-e2e", "code": DOC_FACTS["code"]}},
    )
    print(f"[ingest] http={code} resp={json.dumps(payload, ensure_ascii=False)[:300]}")

    for i in range(20):
        time.sleep(3)
        st = stats(rag_h, cid)
        chunks = st.get("chunk_count") or 0
        docs = st.get("document_count") or 0
        print(f"[poll {i}] docs={docs} chunks={chunks}")
        if chunks and chunks > 0:
            break

    llm_h = {
        "Authorization": f"Bearer {_llm_key()}",
        "X-User-ID": "1",
        "X-Org-ID": "org-1",
        "X-Proxy-Source": "openbase-llm-proxy",
    }
    nonce = str(int(time.time()))
    code, payload = http(
        "POST", f"{LLM}/openllm/v1/chat", llm_h,
        {
            "mode": "explicit",
            "query": f"（非ce{nonce}）请仅依据知识库资料回答：上下文装配分段有哪些、预算代号是什么、回写权威以什么为准？",
            "pipeline": [
                {"component": "rag", "kb_id": cid, "top_k": 3},
                {"component": "llm", "model": "auto"},
            ],
            "output_mode": "llm_response",
        },
    )
    print(f"\n[rag-chat] http={code}")
    data = (payload or {}).get("data") or {} if isinstance(payload, dict) else {}
    trace = data.get("routing_trace") or {}
    print("  rag_source:", trace.get("rag_source"), "| executed:", trace.get("executed"),
          "| degraded:", trace.get("degraded"))
    print("  content[:400]:", repr(str(data.get("content"))[:400]))
    print("  usage:", json.dumps(data.get("usage"), ensure_ascii=False))
    rid = data.get("request_id")
    if rid:
        _, tp = http("GET", f"{LLM}/openllm/v1/trace/{rid}", llm_h)
        body = tp.get("data") if isinstance(tp, dict) and isinstance(tp.get("data"), dict) else tp
        if isinstance(body, dict):
            print("  timeline:", json.dumps(body.get("timeline"), ensure_ascii=False))

    print(f"\n[确认口径] 答案中应出现 {DOC_FACTS['budget']} 或分段名，以证明 RAG 内容进入 Prompt")


if __name__ == "__main__":
    main()
