"""TT-037 输入校验与注入防护专项（v1.4.8 Step 4 剩余项 ⑤）

用例定义（《OpenBase-测试用例-v1.4.8》§6）::

    TT-v1.4.8-037 | 输入校验与注入防护 | 全部 | TD-148-04
    方式：特殊字符 / 超长 / JSON 注入
    通过标准：无 5xx、无异常堆栈外泄

判定口径（本脚本实现，逐项可复算）：

1. **无 5xx**：全部探针响应状态码 < 500（唯一例外：分类为 `H` 的 LLM 上游不可用，
   本脚本在 `--llm-available` 下不设例外，实测环境 LLM 可用故一律要求 < 500）。
2. **无堆栈外泄**：全部响应体不得出现堆栈/内部实现关键字
   （`Traceback (most recent call last)` / `File "` / `site-packages` / `sqlalchemy` /
   `sqlite3` / `asyncpg` / `psycopg` / `DetachedInstanceError` / `<!DOCTYPE html>` / `<html`）。
3. **校验类探针须 4xx**：参数解析/类型/长度/方法/认证类探针须落在 400~499（不得 2xx 放行）。
4. **参数化查询**：`GET /openllm/v1/writeback/receipts` 以**专用注入串**作 `session_id` 时须
   **按字面量过滤**（`total = 0`），且同一时刻**无过滤基线** `D0.total > 0`（证明该端点有数据、
   `total = 0` 非空集假象）；`total` 不等于无过滤基线 ⇒ 注入不可生效。

工具层说明（如实登记，不计为不通过项）：

* `E1` 原设计为「原始 CRLF 头注入」，但**原始 CRLF 属非法头值**，`httpx` 客户端在**发送前**即抛
  `LocalProtocolError` 拦截 → **请求未到达服务端**，故改以**字面量 `%0d%0a`**（合法头值）探针验证
  服务端不回显注入头；原始 CRLF 的处置在**客户端/代理边界**，非本仓服务端行为。
* `D3` 若复用在其他探针中作为 `session_id` 的注入串，会**命中该探针自身刚写入的回执行**（字面量
  精确匹配，属正确行为）→ 故 `D3` 使用**专用注入串**，与其他探针解耦。

用法::

    python tt037-injection-guard-20260926.py

退出码：0＝批次完成（达标与否见输出与 JSON `verdict`）。
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Callable

import httpx

BASE_URL = "http://127.0.0.1:8041"
ACCOUNT = {"username": "v148-perf", "password": "Perf#148aB"}
OUT_DIR = r"D:\Trae CN\myproject\Dev\OpenBase\doc\test\evidence\v148"

LEAK_MARKERS = [
    "Traceback (most recent call last)",
    'File "',
    "site-packages",
    "sqlalchemy",
    "sqlite3",
    "asyncpg",
    "psycopg",
    "DetachedInstanceError",
    "<!DOCTYPE html>",
    "<html",
]

CHAT_BODY = {"mode": "auto", "output_mode": "llm_response"}
SQLI = "'; DROP TABLE traces; --"
D3_INJECTION = "zz' OR '1'='1 -- (tt037-dedicated)"
XSS = "<script>alert('xss')</script>"
TRAVERSAL = "../../../../etc/passwd"
UNION_SQLI = "1' UNION SELECT username, password FROM users --"
NULL_BYTE = "probe\u0000tail"
LONG_QUERY = "A" * 100_000
LONG_HEADER = "h" * 8_000


def _probe_list() -> list[dict[str, Any]]:
    """探针清单（声明式）：每项含 id / 类别 / 期望 / 请求参数"""
    chat = lambda query: {  # noqa: E731 - 局部构造器，保持清单可读
        "method": "POST",
        "path": "/openllm/v1/chat",
        "json": {**CHAT_BODY, "query": query},
    }
    return [
        # ---- A. 特殊字符 / 注入串（业务类：2xx 或 4xx 皆可，不得 5xx）----
        {"id": "A1", "category": "sql-injection", "expect": "2xx_or_4xx", "desc": "对话 query 含 DROP TABLE 注入串", **chat(SQLI)},
        {"id": "A2", "category": "xss", "expect": "2xx_or_4xx", "desc": "对话 query 含 XSS 脚本串", **chat(XSS)},
        {"id": "A3", "category": "path-traversal", "expect": "2xx_or_4xx", "desc": "对话 query 含路径遍历串", **chat(TRAVERSAL)},
        {"id": "A4", "category": "union-sql", "expect": "2xx_or_4xx", "desc": "对话 query 含 UNION SELECT 注入串", **chat(UNION_SQLI)},
        {"id": "A5", "category": "null-byte", "expect": "2xx_or_4xx", "desc": "对话 query 含 NUL 字节", **chat(NULL_BYTE)},
        {"id": "A6", "category": "sql-injection", "expect": "2xx_or_4xx", "desc": "对话 session_id 含注入串",
         "method": "POST", "path": "/openllm/v1/chat",
         "json": {**CHAT_BODY, "query": "TT037 session 注入探针", "session_id": SQLI}},
        # ---- B. 超长输入 ----
        {"id": "B1", "category": "overlong", "expect": "2xx_or_4xx", "desc": "对话 query 100k 字符", **chat(LONG_QUERY)},
        {"id": "B2", "category": "overlong-header", "expect": "2xx_or_4xx", "desc": "X-Request-Id 8k 字符",
         "method": "GET", "path": "/openllm/v1/health", "headers": {"X-Request-Id": LONG_HEADER}},
        # ---- C. JSON 注入 / 畸形结构（校验类：须 4xx）----
        {"id": "C1", "category": "malformed-json", "expect": "4xx", "desc": "截断的 JSON 请求体",
         "method": "POST", "path": "/openllm/v1/chat",
         "content": b'{"query": "x", ', "headers": {"Content-Type": "application/json"}},
        {"id": "C2", "category": "type-mismatch", "expect": "4xx", "desc": "query 传整数（应为字符串）",
         "method": "POST", "path": "/openllm/v1/chat", "json": {"query": 12345}},
        {"id": "C3", "category": "type-mismatch", "expect": "4xx", "desc": "query 传数组（应为字符串）",
         "method": "POST", "path": "/openllm/v1/chat", "json": {"query": ["a", "b"]}},
        {"id": "C4", "category": "payload-shape", "expect": "4xx", "desc": "请求体为 JSON 数组（应为对象）",
         "method": "POST", "path": "/openllm/v1/chat", "json": [1, 2, 3]},
        {"id": "C5", "category": "deep-nesting", "expect": "2xx_or_4xx", "desc": "深层嵌套 JSON（60 层）",
         "method": "POST", "path": "/openllm/v1/chat",
         "content": ("[" * 60 + "]" * 60).encode("utf-8"),
         "headers": {"Content-Type": "application/json"}},
        {"id": "C6", "category": "content-type", "expect": "4xx", "desc": "JSON 体但 Content-Type=text/plain",
         "method": "POST", "path": "/openllm/v1/chat",
         "content": b'{"query": "x"}', "headers": {"Content-Type": "text/plain"}},
        {"id": "C7", "category": "empty-body", "expect": "4xx", "desc": "空请求体（无 JSON）",
         "method": "POST", "path": "/openllm/v1/chat", "content": b""},
        # ---- D. 路径 / 查询串注入（校验类：须 4xx）----
        {"id": "D0", "category": "baseline", "expect": "2xx_or_4xx", "desc": "回执查询无过滤基线（证明端点有数据）",
         "method": "GET", "path": "/openllm/v1/writeback/receipts", "post": "record_total"},
        {"id": "D1", "category": "path-injection", "expect": "4xx", "desc": "trace 路径参数含注入串",
         "method": "GET", "path": f"/openllm/v1/trace/{SQLI}"},
        {"id": "D2", "category": "path-traversal", "expect": "4xx", "desc": "trace 路径参数含遍历串",
         "method": "GET", "path": "/openllm/v1/trace/..%2F..%2Fetc%2Fpasswd"},
        {"id": "D3", "category": "query-injection", "expect": "2xx_or_4xx", "desc": "回执查询 session_id 专用注入串（须参数化）",
         "method": "GET", "path": "/openllm/v1/writeback/receipts", "params": {"session_id": D3_INJECTION},
         "post": "receipts_parameterized"},
        {"id": "D4", "category": "query-injection", "expect": "4xx", "desc": "回执查询 limit 传注入串（数值参数）",
         "method": "GET", "path": "/openllm/v1/writeback/receipts", "params": {"limit": SQLI}},
        {"id": "D5", "category": "method-not-allowed", "expect": "4xx", "desc": "对只读端点发 DELETE",
         "method": "DELETE", "path": "/openllm/v1/writeback/receipts"},
        {"id": "D6", "category": "not-found", "expect": "4xx", "desc": "不存在的路径",
         "method": "GET", "path": "/openllm/v1/__probe__/not-exist"},
        # ---- E. Header 注入 ----
        {"id": "E1", "category": "header-crlf-encoded", "expect": "2xx_or_4xx", "desc": "X-Request-Id 含字面量 %0d%0a（合法头值）",
         "method": "GET", "path": "/openllm/v1/health",
         "headers": {"X-Request-Id": "probe%0d%0aX-Injected: 1"}, "post": "no_header_injection"},
        {"id": "E2", "category": "header-injection", "expect": "2xx_or_4xx", "desc": "X-Request-Id 含脚本串",
         "method": "GET", "path": "/openllm/v1/health", "headers": {"X-Request-Id": XSS}},
        # ---- F. 认证与凭据 ----
        {"id": "F1", "category": "unauthenticated", "expect": "4xx", "desc": "无凭据访问对话端点",
         "method": "POST", "path": "/openllm/v1/chat", "json": {**CHAT_BODY, "query": "x"}, "auth": False},
        {"id": "F2", "category": "bad-token", "expect": "4xx", "desc": "伪造 Bearer 令牌",
         "method": "POST", "path": "/openllm/v1/chat", "json": {**CHAT_BODY, "query": "x"},
         "headers": {"Authorization": "Bearer not-a-real-token"}, "auth": False},
        {"id": "F3", "category": "bad-token", "expect": "4xx", "desc": "SQL 注入串作 Bearer 令牌",
         "method": "POST", "path": "/openllm/v1/chat", "json": {**CHAT_BODY, "query": "x"},
         "headers": {"Authorization": f"Bearer {SQLI}"}, "auth": False},
        # ---- G. 流式端点同类输入 ----
        {"id": "G1", "category": "sql-injection", "expect": "2xx_or_4xx", "desc": "流式端点 query 含注入串",
         "method": "POST", "path": "/openllm/v1/chat/stream",
         "json": {"query": SQLI, "mode": "auto", "max_tokens": 32}, "stream": True},
    ]


def _login(client: httpx.Client) -> str:
    resp = client.post("/api/v1/auth/login", json=ACCOUNT)
    if resp.status_code != 200:
        raise SystemExit(f"登录失败: {resp.status_code} {resp.text[:200]}")
    body = resp.json()
    token = body.get("access_token") or (body.get("data") or {}).get("access_token")
    if not token:
        raise SystemExit("登录响应无 access_token")
    return str(token)


def _run_probe(client: httpx.Client, probe: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    """执行单条探针，返回可复算的观测记录"""
    request_headers = dict(probe.get("headers") or {})
    if probe.get("auth", True):
        request_headers["Authorization"] = headers["Authorization"]
    kwargs: dict[str, Any] = {"headers": request_headers}
    if "json" in probe:
        kwargs["json"] = probe["json"]
    if "content" in probe:
        kwargs["content"] = probe["content"]
    if "params" in probe:
        kwargs["params"] = probe["params"]

    record: dict[str, Any] = {
        "id": probe["id"],
        "category": probe["category"],
        "desc": probe["desc"],
        "expect": probe["expect"],
        "method": probe["method"],
        "path": probe["path"],
    }
    try:
        if probe.get("stream"):
            with client.stream(probe["method"], probe["path"], **kwargs) as resp:
                first = next(resp.iter_bytes(), b"")
                record["status"] = resp.status_code
                record["body_head"] = first[:200].decode("utf-8", "replace")
                record["body_len"] = len(first)
        else:
            resp = client.request(probe["method"], probe["path"], **kwargs)
            record["status"] = resp.status_code
            record["body_head"] = resp.text[:400]
            record["body_len"] = len(resp.text)
            record["resp_headers"] = {
                key: value
                for key, value in resp.headers.items()
                if key.lower() in {"x-injected", "content-type", "x-request-id"}
            }
            if probe.get("post") in {"receipts_parameterized", "record_total"}:
                try:
                    record["total"] = resp.json().get("total")
                except Exception:  # 非 JSON 响应：交由 leak/状态判定
                    record["total"] = None
    except Exception as exc:  # 网络层异常：如实登记，判为不通过（不得静默通过）
        record["status"] = None
        record["error"] = f"{type(exc).__name__}: {exc}"
        record["body_head"] = ""
        record["body_len"] = 0
    return record


def _evaluate(records: list[dict[str, Any]]) -> dict[str, Any]:
    """按四项判定口径复算"""
    baseline_total = next((r.get("total") for r in records if r["id"] == "D0"), None)
    failures: list[dict[str, Any]] = []
    for rec in records:
        status = rec.get("status")
        if status is None:
            failures.append({"id": rec["id"], "rule": "no-5xx", "reason": f"请求异常: {rec.get('error')}"})
            continue
        if status >= 500:
            failures.append({"id": rec["id"], "rule": "no-5xx", "reason": f"status={status}"})
        if rec["expect"] == "4xx" and not (400 <= status < 500):
            failures.append({"id": rec["id"], "rule": "validation-4xx", "reason": f"status={status}"})
        hit = [m for m in LEAK_MARKERS if m.lower() in (rec.get("body_head") or "").lower()]
        if hit:
            failures.append({"id": rec["id"], "rule": "no-leak", "reason": f"命中关键字 {hit}"})
        if rec["id"] == "D0" and not (isinstance(baseline_total, int) and baseline_total > 0):
            failures.append({"id": rec["id"], "rule": "baseline-nonempty",
                             "reason": f"无过滤基线 total={baseline_total}（应为 >0，否则 D3 的 total=0 无判别力）"})
        if rec["id"] == "D3" and rec.get("total") != 0:
            failures.append({"id": rec["id"], "rule": "parameterized",
                             "reason": f"total={rec.get('total')}（专用注入串应字面量过滤为 0；无过滤基线={baseline_total}）"})
        if rec["id"] == "E1":
            if "x-injected" in {k.lower() for k in (rec.get("resp_headers") or {})}:
                failures.append({"id": rec["id"], "rule": "no-header-injection", "reason": "响应头出现 X-Injected"})

    rules = sorted({f["rule"] for f in failures})
    return {
        "pass": not failures,
        "rules_checked": ["no-5xx", "validation-4xx", "no-leak", "parameterized", "baseline-nonempty", "no-header-injection"],
        "failures": failures,
        "failed_rules": rules,
        "status_5xx_count": sum(1 for r in records if (r.get("status") or 0) >= 500),
        "probes": len(records),
        "receipts_baseline_total": baseline_total,
    }


def main() -> None:
    probes = _probe_list()
    with httpx.Client(base_url=BASE_URL, timeout=120.0, follow_redirects=False) as client:
        health = client.get("/openllm/v1/health")
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}
        records = [_run_probe(client, probe, headers) for probe in probes]
        verdict = _evaluate(records)

    for rec in records:
        status = rec.get("status")
        flag = "OK " if status is not None and status < 500 else "!! "
        print(f"{flag}[{rec['id']}] {rec['category']:<18} status={status} len={rec.get('body_len')} | {rec['desc']}")
    print()
    print(f"探针数={verdict['probes']} 5xx={verdict['status_5xx_count']} 不通过项={len(verdict['failures'])}")
    print(f"判定: {json.dumps(verdict, ensure_ascii=False)}")

    out = {
        "case": "TT-037 输入校验与注入防护（无 5xx、无异常堆栈外泄）",
        "date": "2026-09-26",
        "base_url": BASE_URL,
        "health": {"status": health.status_code, "body": health.text[:400]},
        "auth": {"account": ACCOUNT["username"], "login_status": 200},
        "tooling_notes": [
            "E1：原始 CRLF 头值由 httpx 客户端在发送前以 LocalProtocolError 拦截（未到达服务端）→ 改以字面量 %0d%0a 合法头值验证服务端不回显注入头。",
            "D3：使用专用注入串（不复用于其他探针的 session_id），避免命中其他探针自身写入的回执行（字面量精确匹配属正确行为）。",
            "本批次探针会写入少量真实对话/回写回执行（测试数据，非产品数据）。",
        ],
        "probes": records,
        "verdict": verdict,
    }
    path = f"{OUT_DIR}/tt037-injection-guard-20260926.json"
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(out, handle, ensure_ascii=False, indent=2)
    print(f"证据: {path}")


if __name__ == "__main__":
    main()
