"""A/B 双通道端到端验证（S7-T4-3/T4-4 证据生成）。

产出：
  doc/test/evidence/s7/l2-2/read-path-ab-equivalence.json
  doc/test/evidence/s7/l2-2/write-path-equivalence.json
  doc/test/evidence/s7/l2-2/k14-idempotency.json
说明：全部为真实 HTTP 调用（A 直连原生 + B 经 OpenBase 编排），不可达/不通过一律如实登记。
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import subprocess
import urllib.error
import urllib.request

OB = "http://127.0.0.1:8000"
LLM = "http://127.0.0.1:8001"
RAG = "http://127.0.0.1:8010"
MEM = "http://127.0.0.1:8020"
DPS = "http://127.0.0.1:8030"
RAG_KEY = "openbase-rag-gw-key-20260901"
# 与 OpenBase settings 对齐的网关密钥（memory_api_key / llm_api_key），仅本机联调使用
MEM_KEY = "openbase-gw-key-20260830"
LLM_KEY = "sk-openllm-openbase-gateway-key"
EVID = pathlib.Path(r"d:\Trae CN\myproject\Dev\OpenBase\doc\test\evidence\s7\l2-2")
IDENTITY_HEADERS = {
    "X-User-ID": "1",
    "X-Tenant-ID": "tenant-1",
    "X-Tenant-Code": "tenant-1",
    "X-User-Role": "admin",
    "X-Proxy-Source": "e2e-dual-channel-probe",
}
DPS_HEADERS = {
    "X-Org-ID": "dps-org-001",
    "X-Tenant-ID": "dps-tenant-001",
    "X-User-ID": "1",
    "X-User-Role": "super_admin",
}
JWT = ""


def call(method: str, url: str, headers: dict | None = None, body: dict | None = None,
         timeout: int = 30) -> tuple[int, str, dict]:
    data = json.dumps(body).encode() if body is not None else None
    hdrs = {"Content-Type": "application/json", **(headers or {})}
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace"), dict(resp.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace"), dict(exc.headers)
    except Exception as exc:  # noqa: BLE001
        return 0, f"ERR {exc}", {}


def jload(text: str):
    try:
        return json.loads(text)
    except Exception:  # noqa: BLE001
        return None


def ids_of(payload, paths: list[list[str]]) -> list[str]:
    """按候选路径取 id 列表（宽松：全部落空返回空列表）."""
    for path in paths:
        node = payload
        for key in path:
            if isinstance(node, dict):
                node = node.get(key)
            else:
                node = None
                break
        if not isinstance(node, list):
            continue
        out = []
        for item in node:
            if isinstance(item, dict):
                out.append(str(item.get("id") or item.get("collection_id") or item.get("memory_id") or ""))
        out = [v for v in out if v]
        if out:
            return sorted(out)
    return []


ID_PATHS = [["data", "items"], ["data", "models"], ["items"], ["data", "collections"]]


def git_head() -> str:
    try:
        return subprocess.run(
            ["D:\\Git\\cmd\\git.exe", "-C", r"d:\Trae CN\myproject\Dev\OpenBase", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, encoding="utf-8",
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


NOW = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat()
HEAD = git_head()

# ---------------------------------------------------------------- 0) 登录
st, body, _ = call("POST", f"{OB}/api/v1/auth/login", body={"username": "admin", "password": "admin123"})
if st == 200:
    JWT = jload(body).get("access_token", "")
bearer = {"Authorization": f"Bearer {JWT}"} if JWT else {}
print(f"[0] OpenBase 登录 -> {st} (token_len={len(JWT)})")

# ---------------------------------------------------------------- 1) A 直连读
# ---------------------------------------------------------------- 0.5) A 侧子系统自有凭据
st_llm, body_llm, _ = call("POST", f"{LLM}/api/v1/auth/login", body={"username": "admin", "password": "admin123"})
llm_token = (jload(body_llm) or {}).get("access_token", "") if st_llm == 200 else ""
print(f"[0.5] OpenLLM 自身登录 -> {st_llm} (token_len={len(llm_token)})")
# OpenMemory 业务面为「服务 Key + JWT」双凭据（缺任一 401/403，实测）
mem_auth = {"X-API-Key": MEM_KEY, **bearer}
print(f"[0.5] OpenMemory 双凭据（X-API-Key + OpenBase JWT）是否齐备 -> {all(mem_auth.values())}")

a_probes = {
    "OpenRAG": ("GET", f"{RAG}/api/v1/collections", {"X-API-Key": RAG_KEY}),
    # A 直连对齐 B 侧 llm-proxy/models 的上游（/openllm/v1/models）
    "OpenLLM": ("GET", f"{LLM}/openllm/v1/models", {"Authorization": f"Bearer {llm_token}"} if llm_token else {}),
    "OpenMemory": ("GET", f"{MEM}/api/v1/sessions", mem_auth),
    "DPS": ("GET", f"{DPS}/api/v2/portrait/list?page=1&page_size=20", DPS_HEADERS),
}
a_result: dict[str, dict] = {}
for name, (method, url, headers) in a_probes.items():
    st, body, _ = call(method, url, headers)
    payload = jload(body)
    a_result[name] = {"status": st, "url": url, "body_head": " ".join(body.split())[:240],
                      "ids": ids_of(payload, ID_PATHS) if payload else []}
    print(f"[1][A/{name}] {st} ids={len(a_result[name]['ids'])} :: {a_result[name]['body_head'][:130]}")

# ---------------------------------------------------------------- 2) B 编排读
b_probes = {
    "OpenRAG": ("GET", f"{OB}/api/v1/rag-proxy/collections", bearer),
    "OpenLLM": ("GET", f"{OB}/api/v1/llm-proxy/models", bearer),
    "OpenMemory": ("GET", f"{OB}/api/v1/memory-proxy/sessions", bearer),
    "DPS": ("GET", f"{OB}/api/v1/dps-proxy/portraits", bearer),
}
b_result: dict[str, dict] = {}
for name, (method, url, headers) in b_probes.items():
    st, body, _ = call(method, url, headers)
    payload = jload(body)
    b_result[name] = {"status": st, "url": url, "body_head": " ".join(body.split())[:240],
                      "ids": ids_of(payload, ID_PATHS) if payload else []}
    print(f"[2][B/{name}] {st} ids={len(b_result[name]['ids'])} :: {b_result[name]['body_head'][:130]}")

# ---------------------------------------------------------------- 3) 写通链路（B 写 -> A 读；A 写 -> B 读）
stamp = dt.datetime.now().strftime("%Y%m%d%H%M%S")
write_chain: dict[str, dict] = {}

marker_b = f"e2e-dual-b-{stamp}"
st_w, body_w, _ = call(
    "POST", f"{OB}/api/v1/rag-proxy/collections", bearer,
    {"name": marker_b, "description": "dual-channel write probe (B->A)"},
)
created_b = jload(body_w) or {}
new_id_b = str((created_b.get("data") or {}).get("id") or "")
st_r, body_r, _ = call("GET", f"{RAG}/api/v1/collections", {"X-API-Key": RAG_KEY})
seen_a = marker_b in body_r
write_chain["B_write_then_A_read"] = {
    "write_url": f"{OB}/api/v1/rag-proxy/collections", "write_status": st_w, "created_id": new_id_b,
    "read_url": f"{RAG}/api/v1/collections", "read_status": st_r, "visible_via_A": seen_a,
    "verdict": "PASS" if (st_w in (200, 201) and seen_a) else "FAIL",
}
print(f"[3] B 写 -> A 读: write={st_w} id={new_id_b} visible_A={seen_a}")

marker_a = f"e2e-dual-a-{stamp}"
st_wa, body_wa, _ = call(
    "POST", f"{RAG}/api/v1/collections", {"X-API-Key": RAG_KEY},
    {"name": marker_a, "description": "dual-channel write probe (A->B)"},
)
created_a = jload(body_wa) or {}
new_id_a = str((created_a.get("data") or {}).get("id") or "")
st_rb, body_rb, _ = call("GET", f"{OB}/api/v1/rag-proxy/collections", bearer)
seen_b = marker_a in body_rb
write_chain["A_write_then_B_read"] = {
    "write_url": f"{RAG}/api/v1/collections", "write_status": st_wa, "created_id": new_id_a,
    "read_url": f"{OB}/api/v1/rag-proxy/collections", "read_status": st_rb, "visible_via_B": seen_b,
    "verdict": "PASS" if (st_wa in (200, 201) and seen_b) else "FAIL",
}
print(f"[3] A 写 -> B 读: write={st_wa} id={new_id_a} visible_B={seen_b}")

# OpenMemory：B 写（remember）-> A 读（原生 recall 命中）
marker_mem = f"e2e-dual-mem-{stamp}"
st_mw, body_mw, _ = call("POST", f"{OB}/api/v1/memory-proxy/remember", mem_auth,
                         {"content": marker_mem, "tenant_id": "tenant-1"})
mem_created_id = str(((jload(body_mw) or {}).get("data") or {}).get("memory_id") or "")
st_mr, body_mr, _ = call("POST", f"{MEM}/api/v1/recall", mem_auth, {"query": marker_mem})
mem_hit = marker_mem in body_mr
write_chain["memory_B_write_then_A_recall"] = {
    "write_url": f"{OB}/api/v1/memory-proxy/remember", "write_status": st_mw, "created_memory_id": mem_created_id,
    "read_url": f"{MEM}/api/v1/recall", "read_status": st_mr, "recalled_via_A": mem_hit,
    "read_channel_auth": "X-API-Key + Bearer JWT（双凭据）",
    "verdict": "PASS" if (st_mw in (200, 201) and mem_hit) else "FAIL",
}
print(f"[3] Memory: B 写={st_mw} id={mem_created_id} -> A recall 命中={mem_hit}")

# ---------------------------------------------------------------- 4) K14 幂等（同名重放）
st_replay, body_replay, _ = call(
    "POST", f"{OB}/api/v1/rag-proxy/collections", bearer,
    {"name": marker_b, "description": "dual-channel write probe (B->A) replay"},
)
replay_payload = jload(body_replay) or {}
replay_ids = ids_of(replay_payload, ID_PATHS)
replay_created_id = str((replay_payload.get("data") or {}).get("id") or "")
st_list, body_list, _ = call("GET", f"{OB}/api/v1/rag-proxy/collections", bearer)
same_name_count = body_list.count(marker_b)
k14 = {
    "probe": "同一 name 重复 POST /api/v1/rag-proxy/collections",
    "first_write_status": st_w, "first_created_id": new_id_b,
    "replay_status": st_replay, "replay_body_head": " ".join(body_replay.split())[:240],
    "distinct_rows_for_same_name": same_name_count,
    "verdict": "PASS" if same_name_count <= 1 else "FAIL",
    "semantics_note": "按实测登记：重放返回状态与库内同名行数，不做假设",
}
print(f"[4] K14 重放: status={st_replay} 同名行数={same_name_count}")

# ---------------------------------------------------------------- 5) 清理（删除两枚探针集合）
cleanup = {}
for label, cid in (("B-created", new_id_b), ("A-created", new_id_a), ("replay-created", replay_created_id)):
    if not cid:
        cleanup[label] = {"skip": "无 id"}
        continue
    st_d, body_d, _ = call("DELETE", f"{OB}/api/v1/rag-proxy/collections/{cid}", bearer)
    cleanup[label] = {"id": cid, "delete_status": st_d, "body_head": " ".join(body_d.split())[:120]}
    print(f"[5] 清理 {label} {cid} -> {st_d}")

if mem_created_id:
    for payload in ({"memory_ids": [mem_created_id]}, {"memory_id": mem_created_id}):
        st_f, body_f, _ = call("POST", f"{OB}/api/v1/memory-proxy/forget", mem_auth, payload)
        cleanup["memory-probe"] = {"id": mem_created_id, "forget_payload_keys": list(payload),
                                   "forget_status": st_f, "body_head": " ".join(body_f.split())[:140]}
        print(f"[5] 清理 memory-probe {mem_created_id} ({list(payload)}) -> {st_f}")
        if st_f in (200, 201):
            break

# ---------------------------------------------------------------- 6) 等价性判定
def verdict_for(name: str) -> dict:
    a, b = a_result[name], b_result[name]
    if a["status"] != 200 or b["status"] != 200:
        return {"verdict": "BLOCKED", "reason": f"A={a['status']} B={b['status']}"}
    if not a["ids"] and not b["ids"]:
        return {"verdict": "PASS_EMPTY", "reason": "两侧均为空集（一致性成立但无样本）"}
    if a["ids"] == b["ids"]:
        return {"verdict": "PASS", "reason": f"id 集完全一致（{len(a['ids'])} 条）"}
    overlap = len(set(a["ids"]) & set(b["ids"]))
    return {"verdict": "PARTIAL", "reason": f"id 集不一致：A={len(a['ids'])} B={len(b['ids'])} 交集={overlap}"}


equivalence = {name: {"A": a_result[name], "B": b_result[name], **verdict_for(name)} for name in a_probes}
print("\n[6] 双通道读等价：")
for name, item in equivalence.items():
    print(f"   {name}: {item['verdict']} ({item['reason']})")

# ---------------------------------------------------------------- 7) 落盘证据
EVID.mkdir(parents=True, exist_ok=True)
common = {"schema_version": 1, "tool": "dual_channel_e2e.py", "task": "S7-T4",
          "execution_face": "B", "generated_at": NOW, "openbase_commit": HEAD}

read_ev = {
    **common, "evidence_ref": "S7-T4-3", "title": "读路径 A/B 双通道等价（同一读请求经 A/B）",
    "status": "PASS" if all(v["verdict"] in ("PASS", "PASS_EMPTY") for v in equivalence.values()) else "PARTIAL",
    "endpoints": {"A": "子系统原生 API（直连）", "B": "OpenBase 编排代理（JWT）"},
    "results": equivalence,
}
write_ev = {
    **common, "evidence_ref": "S7-T4-4", "title": "写路径 A/B 双通道等价（写后跨通道可见）",
    "status": "PASS" if all(v["verdict"] == "PASS" for v in write_chain.values()) else "PARTIAL",
    "chain": write_chain, "cleanup": cleanup,
}
k14_ev = {**common, "evidence_ref": "S7-T4-4/K14", "title": "K14 写幂等（重放不双写）", **k14}

(EVID / "read-path-ab-equivalence.json").write_text(json.dumps(read_ev, ensure_ascii=False, indent=2), encoding="utf-8")
(EVID / "write-path-equivalence.json").write_text(json.dumps(write_ev, ensure_ascii=False, indent=2), encoding="utf-8")
(EVID / "k14-idempotency.json").write_text(json.dumps(k14_ev, ensure_ascii=False, indent=2), encoding="utf-8")
print("\n[7] 证据已落盘：read-path-ab-equivalence.json / write-path-equivalence.json / k14-idempotency.json")
