"""智能体对话**流式**全链路 E2E 核验（`CR-148-030` 双路径收敛验收）

目标链路（全真实 HTTP，无桩；与 `agent_context_e2e.py` 同一主体与同一断言口径）：

  ① 以**智能体主体**接入（`sk-agent-*` 凭据，`tenant_code='tenant-1'`）
  ② `POST /api/v1/llm-proxy/chat/stream`（SSE 逐事件透传 → OpenLLM `/chat/stream`）
  ③ 流式 auto 经**同一组件决策入口**（`AutoOrchestrator.decide` + 知识库自动对接）
     → 自动装配「DPS 画像 + 记忆 + 知识库」并投喂 LLM
  ④ 三路回写（memory / rag / profile）由后台任务入队（`writeback_dispatch` 计量保留）
  ⑤ trace 落库后可回读**权威决策**（path / decision / components / context_metrics /
     回执）—— 流式 `routing` 事件为**首包快照**（P-4 口径约束：决策含外部调用，
     不得前移到首包之前），故本脚本以 **trace 为准**判定。

硬性判定（不满足即 FAIL）：
  S1 智能体主体就绪（agent 创建 200 且拿到 `sk-agent-*` 明文密钥）
  S2 两轮流式 HTTP 200，SSE 事件序列含 `routing` 且含 `done`（契约）
  S3 第 1 轮 trace `routing_trace.path == "C"`（记忆 + 知识库 + LLM）
  S4 第 1 轮 trace `components.need_memory == true` 且 `need_rag == true`
  S5 第 1 轮 trace `components.kb_id_source ∈ {registry, external}`（知识库**自动发现**）
     且 `components.rag_source == "external"`（命中真实 OpenRAG）
  S6 第 1 轮 `timeline` 含 `auto_component_decision`（决策计量）与 `memory`、`rag`
     （组件**真实执行**，而非仅决策）
  S7 第 1 轮 `context_metrics.counted == true` 且 `segment_tokens.rag > 0`
     且 `segment_tokens.profile > 0`（知识库 + 画像**真实进入 Prompt**）
  S8 第 1 轮 trace 内三路回写**入队回执**无 failed / degraded（含 `rag` 路 ——
     缺 kb_id 曾恒 failed）
  S8b 第 1 轮**权威投递真值**（回写队列表 `writeback_queue`）：memory / rag /
     profile 三路均达 `done`（队列状态而非仅入队受理）
  S9 第 2 轮 `segment_tokens.memory > 0`（记忆段**进入 Prompt**；第 1 轮回写沉淀 →
     第 2 轮可读）
  S10 第 1 轮 `context_metrics.memory.injected_items >= 1` 且
     `context_metrics.rag.injected_items >= 1`（**条目级证据**；流式须回传
     `raw_results` 才能与同步同口径 —— `DEF-BE-148-028` 修复项）

用法::

    python agent_context_e2e_stream.py [--base-url http://127.0.0.1:8000] [--turns 2]

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

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agent_context_e2e import (  # noqa: E402
    ADMIN,
    DEFAULT_QUERY,
    _dig,
    _seed_dps_profile,
    call,
    probe_dependencies,
)

STREAM_PATH = "/api/v1/llm-proxy/chat/stream"
WRITEBACK_WAIT_SECONDS = 10.0
WRITEBACK_DELIVERY_WAIT_SECONDS = 30.0
WRITEBACK_POLL_INTERVAL = 1.0
TRACE_RETRIES = 8
TRACE_RETRY_INTERVAL = 1.0
OPENLLM_ENV_FILE = Path(
    r"D:\Trae CN\myproject\Dev\OpenLLM\backend\.env"
)
OPENLLM_SHARED_INFRA_FILE = Path(
    r"D:\Trae CN\myproject\Dev\OpenBase\.env.shared-infra"
)


def _stream_chat(
    base: str, token: str, payload: dict[str, Any], timeout: int = 300
) -> dict[str, Any]:
    """调用流式端点并解析 SSE（返回状态码 / 事件序列 / 回答正文 / request_id）"""
    request = urllib.request.Request(
        f"{base}{STREAM_PATH}",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
    )
    request.add_header("Content-Type", "application/json")
    request.add_header("Accept", "text/event-stream")
    request.add_header("Authorization", f"Bearer {token}")
    events: list[str] = []
    chunks: list[str] = []
    request_id = ""
    current_event = ""
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            for raw in response:
                line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                if line.startswith("event:"):
                    current_event = line.split(":", 1)[1].strip()
                    events.append(current_event)
                elif line.startswith("data:"):
                    body = line.split(":", 1)[1].strip()
                    try:
                        parsed = json.loads(body)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(parsed, dict):
                        continue
                    if current_event == "chunk":
                        chunks.append(str(parsed.get("delta") or ""))
                    if parsed.get("request_id"):
                        request_id = str(parsed["request_id"])
    except urllib.error.HTTPError as exc:
        return {
            "http": exc.code,
            "events": events,
            "content": "".join(chunks),
            "request_id": request_id,
            "error": exc.read().decode("utf-8", errors="replace")[:300],
        }
    except Exception as exc:  # noqa: BLE001 - 网络层异常统一记录
        return {
            "http": -1,
            "events": events,
            "content": "".join(chunks),
            "request_id": request_id,
            "error": f"{type(exc).__name__}: {exc}",
        }
    return {
        "http": status,
        "events": events,
        "content": "".join(chunks),
        "request_id": request_id,
    }


def _openllm_database_url() -> str:
    """解析 OpenLLM 数据库连接串（**只读取既有配置，不落凭据**）"""
    for path in (OPENLLM_ENV_FILE, OPENLLM_SHARED_INFRA_FILE):
        if not path.exists():
            continue
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key == "DATABASE_URL" and value.strip().lower().startswith("postgresql"):
                return value.strip()
            if key == "POSTGRES_URL":
                return value.strip()
    raise RuntimeError("未解析到 OpenLLM DATABASE_URL（PostgreSQL）")


def _load_trace_from_db(request_id: str) -> dict[str, Any]:
    """从 OpenLLM `traces` 表读取**权威落库**的 spans + metadata

    说明（为何不经 `GET /openllm/v1/trace/{id}`）：该端点带资源所有者门禁
    （`P1-1 IDOR 防护`：仅 trace 所有者或平台管理员可读），而本脚本持有的
    OpenLLM 网关 Key 身份与流式请求主体（智能体资源键）不同 → 实测 401/2001。
    证据取数因此直连**同一落库**（表 `traces`，列 `spans`/`metadata`），
    读取口径与端点实现一致（`get_spans()` / `get_metadata().routing_trace`）。
    """
    import psycopg2  # 局部导入：仅本脚本取证用

    connection = psycopg2.connect(_openllm_database_url())
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT spans, metadata FROM traces WHERE trace_id = %s",
                (request_id,),
            )
            row = cursor.fetchone()
    finally:
        connection.close()
    if row is None:
        return {}
    spans_raw, metadata_raw = row
    try:
        spans = json.loads(spans_raw) if spans_raw else []
    except json.JSONDecodeError:
        spans = []
    try:
        metadata = json.loads(metadata_raw) if metadata_raw else {}
    except json.JSONDecodeError:
        metadata = {}
    return {
        "data": {
            "request_id": request_id,
            "mode": metadata.get("mode"),
            "pipeline": metadata.get("pipeline"),
            "timeline": spans,
            "routing_trace": metadata.get("routing_trace"),
        }
    }


def _fetch_trace(request_id: str, attempts: int = TRACE_RETRIES) -> dict[str, Any]:
    """回读 trace（首次落库存在竞态 → 有限重试；取数走落库，见 `_load_trace_from_db`）"""
    last: dict[str, Any] = {"http": -1, "source": "db"}
    for _ in range(attempts):
        try:
            data = _load_trace_from_db(request_id)
        except Exception as exc:  # noqa: BLE001 - 取数异常不抛出，按未就绪处理
            last = {"http": -1, "source": "db", "error": f"{type(exc).__name__}: {exc}"}
            time.sleep(TRACE_RETRY_INTERVAL)
            continue
        if data:
            return {"http": 200, "source": "db", "payload": {"code": 0, **data}}
        time.sleep(TRACE_RETRY_INTERVAL)
    return last


def _writeback_db_path() -> Path:
    """回写队列 SQLite 落库路径（与 `WritebackStore` 默认口径一致）"""
    override = os.environ.get("WRITEBACK_DB_PATH")
    if override:
        return Path(override)
    return Path(
        r"D:\Trae CN\myproject\Dev\OpenLLM\backend\data\writeback.db"
    )


def _writeback_max_id() -> int:
    """当前回写队列表最大行号（作为「本轮新增行」的基线；库不可用返回 0）"""
    import sqlite3

    path = _writeback_db_path()
    if not path.exists():
        return 0
    connection = sqlite3.connect(str(path), timeout=10)
    try:
        row = connection.execute("SELECT COALESCE(MAX(id), 0) FROM writeback_queue").fetchone()
        return int(row[0] or 0)
    finally:
        connection.close()


def _writeback_rows_after(baseline_id: int) -> list[dict[str, Any]]:
    """读取基线行号之后的回写队列行（权威投递状态：pending/done/failed）"""
    import sqlite3

    path = _writeback_db_path()
    if not path.exists():
        return []
    connection = sqlite3.connect(str(path), timeout=10)
    try:
        cursor = connection.execute(
            "SELECT id, request_id, session_id, seq, target, status, retry_count, updated_at"
            " FROM writeback_queue WHERE id > ? ORDER BY id",
            (baseline_id,),
        )
        columns = [item[0] for item in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        connection.close()


def _await_writeback_delivery(baseline_id: int) -> list[dict[str, Any]]:
    """等待本轮新增的回写行**投递完成**（三路均离开 pending/retrying）"""
    deadline = time.monotonic() + WRITEBACK_DELIVERY_WAIT_SECONDS
    rows: list[dict[str, Any]] = []
    while time.monotonic() < deadline:
        rows = _writeback_rows_after(baseline_id)
        unresolved = [
            row for row in rows if row.get("status") in ("pending", "retrying")
        ]
        roads = {str(row.get("target")) for row in rows}
        if rows and not unresolved and {"memory", "rag", "profile"} <= roads:
            return rows
        time.sleep(WRITEBACK_POLL_INTERVAL)
    return rows


def _wait_writeback_receipt(request_id: str) -> dict[str, Any]:
    """等待后台回写任务把逐路回执补写进 trace（权威真值仍以回写队列表为准）"""
    deadline = time.monotonic() + WRITEBACK_WAIT_SECONDS
    trace: dict[str, Any] = {}
    while time.monotonic() < deadline:
        trace = _fetch_trace(request_id, attempts=1)
        routing_trace = _dig(trace, "payload", "data", "routing_trace") or {}
        receipt = routing_trace.get("writeback") or {}
        if any(road in receipt for road in ("memory", "rag", "profile")):
            return trace
        time.sleep(WRITEBACK_POLL_INTERVAL)
    return trace


def _timeline_steps(trace: dict[str, Any]) -> list[str]:
    steps = _dig(trace, "payload", "data", "timeline") or []
    return [str(item.get("step")) for item in steps if isinstance(item, dict)]


def _write(out_dir: Path, payload: dict[str, Any]) -> None:
    (out_dir / "agent-context-e2e-stream.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--out", default=str(Path(__file__).resolve().parent)
    )
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--turns", type=int, default=2)
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    evidence: dict[str, Any] = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "base_url": base,
        "stream_path": STREAM_PATH,
        "query": args.query,
        "turns": args.turns,
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

    status, payload, _ = call(
        "POST", f"{base}/api/v1/auth/login",
        {"username": ADMIN[0], "password": ADMIN[1]},
    )
    admin_token = _dig(payload, "access_token") or _dig(payload, "data", "access_token")
    if status != 200 or not admin_token:
        evidence["verdict"] = {
            "status": "FAIL",
            "reason": f"管理员登录失败 http={status}",
            "exit_code": 1,
        }
        _write(out_dir, evidence)
        print(f"[FAIL] 管理员登录失败 http={status}")
        return 1

    agent_username = f"ob_agent_stream_{int(time.time()) % 1000000}"
    agent_status, agent_payload, _ = call(
        "POST",
        f"{base}/api/v1/identity/agents",
        {
            "username": agent_username,
            "display_name": "流式全链路联调主体",
            "tenant_id": 1,
            "role": "admin",
            "key_name": "agent-ctx-stream",
        },
        token=admin_token,
    )
    agent_key = _dig(agent_payload, "api_key", "raw_key")
    agent_id = _dig(agent_payload, "agent_id")
    evidence["subject"] = {
        "username": agent_username,
        "agent_id": agent_id,
        "tenant_code": _dig(agent_payload, "tenant_code"),
        "key_issued": bool(agent_key),
    }
    evidence["steps"].append(
        {"step": "provision_agent", "http": agent_status, **evidence["subject"]}
    )
    if agent_status not in (200, 201) or not agent_key:
        evidence["verdict"] = {
            "status": "FAIL",
            "reason": f"智能体主体创建失败 http={agent_status}",
            "agent_response": agent_payload,
            "exit_code": 1,
        }
        _write(out_dir, evidence)
        print(f"[FAIL] 智能体主体创建失败 http={agent_status}")
        return 1
    print(f"[1] 智能体主体就绪 agent_id={agent_id}")

    dps_step = _seed_dps_profile(str(agent_id or ""))
    evidence["steps"].append(dps_step)
    print(f"    DPS 画像前置：{dps_step.get('profile') or dps_step.get('reason')}")

    turns: list[dict[str, Any]] = []
    for index in range(1, args.turns + 1):
        # 取号规避语义缓存（auto 模式已豁免，保留以固化「未命中」判据）
        nonce = f"{int(time.time() * 1000):x}-{index}"
        query_sent = f"（流式取号 {nonce}）{args.query}"
        queue_baseline = _writeback_max_id()
        started = time.perf_counter()
        outcome = _stream_chat(
            base,
            agent_key,
            {"mode": "auto", "query": query_sent, "output_mode": "llm_response"},
        )
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        trace = _wait_writeback_receipt(outcome.get("request_id") or "")
        routing_trace = _dig(trace, "payload", "data", "routing_trace") or {}
        components = routing_trace.get("components") or {}
        metrics = routing_trace.get("context_metrics") or {}
        segment_tokens = metrics.get("segment_tokens") or {}
        memory_snapshot = metrics.get("memory") or {}
        # 权威投递真值：回写队列表（trace 内回执仅证明「已入队」）
        queue_rows = _await_writeback_delivery(queue_baseline)
        turn = {
            "turn": index,
            "http": outcome.get("http"),
            "elapsed_ms": elapsed_ms,
            "events": outcome.get("events"),
            "content_chars": len(outcome.get("content") or ""),
            "request_id": outcome.get("request_id"),
            "trace_source": trace.get("source"),
            "trace_http": trace.get("http"),
            "path": routing_trace.get("path"),
            "kb_id_source": components.get("kb_id_source"),
            "rag_source": components.get("rag_source"),
            "need_memory": components.get("need_memory"),
            "need_rag": components.get("need_rag"),
            "writeback": routing_trace.get("writeback"),
            "writeback_queue": [
                {
                    "target": row.get("target"),
                    "status": row.get("status"),
                    "retry_count": row.get("retry_count"),
                    "seq": row.get("seq"),
                    "session_id": row.get("session_id"),
                }
                for row in queue_rows
            ],
            "segment_tokens": segment_tokens,
            "memory_snapshot": memory_snapshot,
            "rag_snapshot": metrics.get("rag") or {},
            "attribution_a": metrics.get("attribution_a"),
            "memory_injected_items": memory_snapshot.get("injected_items"),
            "rag_injected_items": (metrics.get("rag") or {}).get("injected_items"),
            "counted": metrics.get("counted"),
            "timeline": _timeline_steps(trace),
            "content_preview": (outcome.get("content") or "")[:200],
            "error": outcome.get("error"),
        }
        turns.append(turn)
        evidence["steps"].append({"step": f"stream_turn_{index}", **turn})
        print(
            f"[{index + 1}] 流式第 {index} 轮 http={turn['http']} "
            f"elapsed={elapsed_ms}ms events={turn['events']} "
            f"path={turn['path']} seg={segment_tokens}"
        )
        if index < args.turns:
            time.sleep(2.0)  # 给回写队列留出入队/投递窗口（第 2 轮可读前一轮沉淀）

    evidence["turns"] = turns
    failures: list[str] = []
    first = turns[0] if turns else {}
    second = turns[1] if len(turns) > 1 else {}

    if first.get("http") != 200:
        failures.append(f"S2 第 1 轮流式 http={first.get('http')}（{first.get('error')}）")
    if "routing" not in (first.get("events") or []):
        failures.append(f"S2 第 1 轮缺 routing 事件（events={first.get('events')}）")
    if "done" not in (first.get("events") or []):
        failures.append(f"S2 第 1 轮缺 done 事件（events={first.get('events')}）")
    if first.get("path") != "C":
        failures.append(f"S3 第 1 轮 path={first.get('path')}（应为 C）")
    if not (first.get("need_memory") and first.get("need_rag")):
        failures.append(
            f"S4 第 1 轮决策 need_memory={first.get('need_memory')} "
            f"need_rag={first.get('need_rag')}（应均为 true）"
        )
    if first.get("kb_id_source") not in ("registry", "external"):
        failures.append(
            f"S5 第 1 轮 kb_id_source={first.get('kb_id_source')}（应为 registry/external）"
        )
    if first.get("rag_source") != "external":
        failures.append(f"S5 第 1 轮 rag_source={first.get('rag_source')}（应为 external）")
    steps = first.get("timeline") or []
    for required in ("auto_component_decision", "memory", "rag"):
        if required not in steps:
            failures.append(f"S6 第 1 轮 timeline 缺步骤 {required}（steps={steps}）")
    if first.get("counted") is not True:
        failures.append(f"S7 第 1 轮分段计量未接线（counted={first.get('counted')}）")
    seg = first.get("segment_tokens") or {}
    if int(seg.get("rag") or 0) < 1:
        failures.append(f"S7 第 1 轮知识库未进入 Prompt（segment_tokens={seg}）")
    if not dps_step.get("skipped") and int(seg.get("profile") or 0) < 1:
        failures.append(f"S7 第 1 轮 DPS 画像未进入 Prompt（segment_tokens={seg}）")
    receipt = (first.get("writeback") or {})
    for road in ("memory", "rag", "profile"):
        road_state = (receipt.get(road) or {}).get("status")
        if road_state not in ("accepted", "duplicated"):
            failures.append(
                f"S8 第 1 轮 {road} 路回写入队状态={road_state}（receipt={receipt}）"
            )
    # S8b：**权威投递真值**（回写队列表）—— 三路均须投递成功（`done`）
    queue_rows = first.get("writeback_queue") or []
    delivered = {row.get("target"): row.get("status") for row in queue_rows}
    for road in ("memory", "rag", "profile"):
        if delivered.get(road) != "done":
            failures.append(
                f"S8b 第 1 轮 {road} 路回写未投递成功（status={delivered.get(road)}；"
                f"rows={queue_rows}）"
            )
    if args.turns > 1:
        second_seg = second.get("segment_tokens") or {}
        if int(second_seg.get("memory") or 0) < 1:
            failures.append(
                "S9 第 2 轮记忆段未进入 Prompt"
                f"（segment_tokens={second_seg}）"
            )
    # S10：条目级证据（流式须回传 raw_results 才与同步同口径）
    memory_snapshot = first.get("memory_snapshot") or {}
    rag_snapshot = first.get("rag_snapshot") or {}
    for component, snapshot in (("memory", memory_snapshot), ("rag", rag_snapshot)):
        if int(snapshot.get("injected_items") or 0) < 1:
            failures.append(
                f"S10 第 1 轮 {component} 条目级证据缺失"
                f"（injected_items={snapshot.get('injected_items')}；"
                f"snapshot={snapshot}）"
            )

    verdict = "PASS" if not failures else "FAIL"
    evidence["verdict"] = {
        "status": verdict,
        "failures": failures,
        "exit_code": 0 if verdict == "PASS" else 1,
    }
    _write(out_dir, evidence)
    print("=== 智能体对话流式全链路 E2E ===")
    print(f"  status={verdict}")
    for turn in turns:
        print(
            f"  第 {turn['turn']} 轮 http={turn['http']} path={turn['path']} "
            f"kb_id_source={turn['kb_id_source']} rag_source={turn['rag_source']} "
            f"writeback={(turn.get('writeback') or {}).get('_dispatch')}"
        )
    if failures:
        print("  failures:")
        for item in failures:
            print(f"    - {item}")
    print(f"  evidence: {out_dir / 'agent-context-e2e-stream.json'}")
    return int(evidence["verdict"]["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
