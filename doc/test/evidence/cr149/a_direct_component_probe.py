"""W2 探针：**A 直连三组件取数**判定表（含结尾自检）

**用途**：把 W2（《收口方案》v1.5.0 §1.1.4 题 14「**A 侧直连通路验收 —— 三组件均可经 A 直连
取到数据**」）落成可复现的**取数判定表** —— 对 **DPS（画像）/ OpenMemory（记忆）/
OpenRAG（知识库）**逐个「**先经该组件自身接口种入数据 → 再经 A 直连读取**」，断言**确实取到
数据**（Q8 内容口径：「回落 / 回退后**必须确实能取到数据**」），并在结尾**自检**：任一不符即
`FAIL` 且**返回码非 0**。

**A 直连的口径（§1.1.1「关键定性」）**：A ＝ **直连拓扑**（**不经编排**，单独调用三基础设施），
与 B 通道**对接同一批** DPS / OpenMemory / OpenRAG。故本探针**直接调用各组件自身接口**
（**不经 OpenLLM 编排**），并携带 `assemble_a_direct_headers()` 装配的 **A 直连出站头**。

**本探针锁定的四条契约**：

  1. **取数非空（Q8 内容口径）** —— 种入后经 A 直连接读**确实取到数据**（不是「调用成功但为空」）。
  2. **空态如实** —— 未种入时**如实返回 0 条**（**不以空充数、也不伪造数据**）。
  3. **写读闭环** —— 三组件均「组件自身写入接口 → A 直连读取」闭环一致（记忆内容 / KB 文档 /
     画像版本自增）。
  4. **直连拓扑身份面完整** —— 三系统均得 A 直连出站头（`X-Proxy-Source=llm-proxy`），且与 B 通道
     头**身份四头等价**（复用 `ab_identity_equivalent`）⇒ A/B **到达同系统的身份语义等价**。

**承载与边界（如实登记，不伪 PASS）**：本地以 `mock_services/{openmemory,openrag,profile}_stub`
三组件**进程内**承载（`TestClient`，零网络）⇒ 本探针证明「**A 直连取数链路结构贯通且确实取到
数据**」；**真实外部服务**（生产 DPS / OpenMemory / OpenRAG）联调仍属**运行态复核项**。

用法（cwd = OpenLLM/backend）：python <此脚本> [--json]
"""
from __future__ import annotations

import json
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "mock_services"))

from fastapi.testclient import TestClient  # noqa: E402

from app.identity.ab_equivalence import (  # noqa: E402
    SYSTEM_DPS,
    SYSTEM_OPENMEMORY,
    SYSTEM_OPENRAG,
    ab_identity_equivalent,
    assemble_a_direct_headers,
    b_headers_for,
)
from app.identity.protocol_headers import (  # noqa: E402
    PROXY_SOURCE_LLM,
    PROXY_SOURCE_ORCHESTRATOR,
)

# A 直连出站头：A 通道由 llm-proxy 注入身份头（PROXY_SOURCE_LLM）
IDENTITY = SimpleNamespace(
    user_id="acme_u1",
    tenant_code="acme",
    org_id="acme",
    role="viewer",
    agent_id=None,
    request_id="req-w2-adirect-0001",
)


def _client(module_name: str) -> TestClient:
    """进程内加载三组件的本地承载（零网络）"""
    module = __import__(module_name)
    return TestClient(module.app)


def _a_headers(target_system: str) -> dict[str, str]:
    """该系统的 A 直连出站头（复刻 llm-proxy 直连注入语义）"""
    return assemble_a_direct_headers(
        target_system=target_system, identity_context=IDENTITY
    )


# ---------------------------------------------------------------- ① 记忆（OpenMemory）
def _memory_case() -> dict:
    client = _client("openmemory_stub")
    headers = _a_headers(SYSTEM_OPENMEMORY)
    user_id = IDENTITY.user_id
    marker = "画像偏好：偏好通俗解释与类比"

    empty = client.post(
        "/openmemory/v1/search",
        json={"user_id": user_id, "query": marker, "top_k": 5},
        headers=headers,
    )
    empty_total = empty.json().get("total", 0)

    written = client.post(
        "/openmemory/v1/write",
        json={"user_id": user_id, "query": "解释一下通道", "response": marker},
        headers=headers,
    )
    read = client.post(
        "/openmemory/v1/search",
        json={"user_id": user_id, "query": marker, "top_k": 5},
        headers=headers,
    )
    items = read.json().get("results", [])

    checks = {
        "empty_state_honest": empty.status_code == 200 and empty_total == 0,
        "write_accepted": written.status_code == 200
        and written.json().get("status") == "accepted",
        "read_http_ok": read.status_code == 200,
        "data_retrieved_non_empty": len(items) >= 1,
        "content_matches": bool(items) and marker in items[0].get("content", ""),
        "a_direct_header_present": headers.get("X-Proxy-Source") == PROXY_SOURCE_LLM,
    }
    return {
        "component": "OpenMemory（记忆）",
        "target_system": SYSTEM_OPENMEMORY,
        "endpoint_read": "POST /openmemory/v1/search",
        "endpoint_seed": "POST /openmemory/v1/write",
        "empty_total": empty_total,
        "retrieved_total": len(items),
        "checks": checks,
        "ok": all(checks.values()),
    }


# ---------------------------------------------------------------- ② 知识库（OpenRAG）
def _kb_case() -> dict:
    client = _client("openrag_stub")
    headers = _a_headers(SYSTEM_OPENRAG)
    kb_id = "kb-w2-adirect"
    marker = "通道 A 直连拓扑说明"

    empty = client.post(
        "/openrag/v1/search",
        json={"kb_id": kb_id, "query": marker, "top_k": 5},
        headers=headers,
    )
    empty_total = empty.json().get("total", 0)

    ingested = client.post(
        "/openrag/v1/ingest",
        json={
            "kb_id": kb_id,
            "documents": [{"content": f"{marker}：不经编排，单独调用三基础设施。"}],
        },
        headers=headers,
    )
    # A 直连参数面完整：rerank / score_threshold 须被接受（口径同 T3）
    read = client.post(
        "/openrag/v1/search",
        json={
            "kb_id": kb_id,
            "query": marker,
            "top_k": 5,
            "rerank": True,
            "score_threshold": 0.15,
        },
        headers=headers,
    )
    items = read.json().get("results", [])

    checks = {
        "empty_state_honest": empty.status_code == 200 and empty_total == 0,
        "ingest_accepted": ingested.status_code == 200,
        "read_http_ok": read.status_code == 200,
        "data_retrieved_non_empty": len(items) >= 1,
        "rerank_params_accepted": bool(items) and "score" in items[0],
        "score_above_threshold": bool(items) and items[0].get("score", 0) >= 0.15,
        "a_direct_header_present": headers.get("X-Proxy-Source") == PROXY_SOURCE_LLM,
    }
    return {
        "component": "OpenRAG（知识库）",
        "target_system": SYSTEM_OPENRAG,
        "endpoint_read": "POST /openrag/v1/search",
        "endpoint_seed": "POST /openrag/v1/ingest",
        "empty_total": empty_total,
        "retrieved_total": len(items),
        "checks": checks,
        "ok": all(checks.values()),
    }


# ---------------------------------------------------------------- ③ 画像（DPS）
def _profile_case() -> dict:
    client = _client("profile_stub")
    headers = _a_headers(SYSTEM_DPS)
    user_id = IDENTITY.user_id

    read_first = client.get(
        "/profile/v1/get", params={"user_id": user_id}, headers=headers
    )
    first = read_first.json()

    updated = client.post(
        "/profile/v1/update",
        json={"user_id": user_id, "updates": {"person": {"tone": "concise"}}},
        headers=headers,
    )
    read_again = client.get(
        "/profile/v1/get", params={"user_id": user_id}, headers=headers
    )
    second = read_again.json()

    checks = {
        "read_http_ok": read_first.status_code == 200,
        "data_retrieved_non_empty": bool(
            first.get("person") or first.get("business")
        ),
        "version_present": isinstance(first.get("version"), int),
        "update_accepted": updated.status_code == 200 and updated.json().get("ok") is True,
        "write_read_closure": (
            second.get("version", 0) > first.get("version", 0)
            and "tone" in (second.get("updated_tags") or [])
        ),
        "a_direct_header_present": headers.get("X-Proxy-Source") == PROXY_SOURCE_LLM,
    }
    return {
        "component": "DPS（画像）",
        "target_system": SYSTEM_DPS,
        "endpoint_read": "GET /profile/v1/get",
        "endpoint_seed": "POST /profile/v1/update",
        "empty_total": None,
        "retrieved_total": len(second.get("person") or {}),
        "checks": checks,
        "ok": all(checks.values()),
    }


# ---------------------------------------------------------------- ④ 直连拓扑身份面
def _identity_case() -> dict:
    rows: list[dict] = []
    for system in (SYSTEM_DPS, SYSTEM_OPENMEMORY, SYSTEM_OPENRAG):
        a_headers = _a_headers(system)
        b_headers = b_headers_for(target_system=system, identity_context=IDENTITY)
        equivalent = ab_identity_equivalent(b_headers, a_headers)
        rows.append(
            {
                "system": system,
                "a_proxy_source": a_headers.get("X-Proxy-Source"),
                "b_proxy_source": b_headers.get("X-Proxy-Source"),
                "a_request_id": a_headers.get("X-Request-Id"),
                "ab_identity_equivalent": equivalent,
                "a_headers": a_headers,
            }
        )
    checks = {
        # A 直连来源＝llm-proxy 注入；B 编排来源＝orchestrator（**拓扑不同是设计允许的**）
        "a_source_is_llm_proxy": all(
            row["a_proxy_source"] == PROXY_SOURCE_LLM for row in rows
        ),
        "b_source_is_orchestrator": all(
            row["b_proxy_source"] == PROXY_SOURCE_ORCHESTRATOR for row in rows
        ),
        "topology_distinguishable": all(
            row["a_proxy_source"] != row["b_proxy_source"] for row in rows
        ),
        "request_id_carried": all(row["a_request_id"] is not None for row in rows),
        # 同系统到达时**身份语义等价**（AC-T13-2；来源头允许不同）
        "ab_identity_equivalent_all": all(
            row["ab_identity_equivalent"] for row in rows
        ),
    }
    return {
        "component": "直连拓扑身份面（三系统）",
        "target_system": "dps/openmemory/openrag",
        "endpoint_read": "—",
        "endpoint_seed": "—",
        "empty_total": None,
        "retrieved_total": len(rows),
        "rows": [
            {key: value for key, value in row.items() if key != "a_headers"} for row in rows
        ],
        "checks": checks,
        "ok": all(checks.values()),
    }


def build_cases() -> list[dict]:
    """W2 判定表（**纯函数式**：可由执行器 T15 直接复用，避免判据与探针分叉）"""
    return [_memory_case(), _kb_case(), _profile_case(), _identity_case()]


def main() -> int:
    cases = build_cases()

    payload = {
        "probe": "a_direct_component",
        "ruling": (
            "W2：**A 直连三组件取数** —— A ＝ 直连拓扑（不经编排，单独调用三基础设施）；"
            "三组件（DPS 画像 / OpenMemory 记忆 / OpenRAG 知识库）**种入后经 A 直连均确实取到数据**"
            "（Q8 内容口径）；未种入时**如实为空**（不伪造）；A 直连出站头（`X-Proxy-Source=llm-proxy`）"
            "与 B 通道**身份四头等价**"
        ),
        "carrier": "mock_services/{openmemory,openrag,profile}_stub（进程内 TestClient，零网络）",
        "runtime_pending": (
            "真实外部服务（生产 DPS / OpenMemory / OpenRAG）联调与真实契约路由（`OPENLLM_*_REAL=true`）"
            "仍属**运行态复核项** —— 本探针不据此宣称生产已贯通"
        ),
        "cases": cases,
    }
    failures = [item["component"] for item in cases if not item["ok"]]
    payload["summary"] = {
        "total": len(cases),
        "failed": len(failures),
        "failed_cases": failures,
        "verdict": "PASS" if not failures else "FAIL",
    }

    if "--json" in sys.argv:
        target = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "a_direct_component_probe-result.json"
        )
        with open(target, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        print(f"已落盘：{target}")

    for item in cases:
        bad = [name for name, ok in item["checks"].items() if not ok]
        print(
            f"{'OK ' if item['ok'] else 'BAD'} {item['component']} "
            f"[A 直连 {item['endpoint_read']}] ⇒ "
            f"空态={item['empty_total']} 取到={item['retrieved_total']} "
            f"不符={bad}"
        )
    print(f"\n判定: {payload['summary']['verdict']}（{len(cases)} 例 / 不符 {len(failures)}）")
    print(f"承载: {payload['carrier']}")
    print(f"运行态挂起项: {payload['runtime_pending']}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())

