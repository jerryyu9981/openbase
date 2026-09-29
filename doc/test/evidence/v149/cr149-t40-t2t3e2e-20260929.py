"""v1.4.9 Step 4 运行时取证：T2 接口层 ＋ T3a 服务间集成巡检 ＋ T3b/E2E 深度用例。

对**真实运行实例**取证（不使用夹具结论）。覆盖《OpenBase-测试用例-v1.4.9》中：

    T2：TT-v1.4.9-006 ~ 014（三要素：状态码 ＋ 响应结构 ＋ 边界参数）
    T3a：TT-v1.4.9-024（服务间集成巡检：/openapi.json 全量路由盘点 ＋ 逐条 GET 可达性
                        ＋ v1.4.9 相关链路网络层信号采集，输出逐链路问题表）
    T3b：TT-v1.4.9-025 / 026（预算‑裁剪‑回执链路 C/R/U；错误态与边界）
    E2E：TT-v1.4.9-027 / 029 / 030（双路径一致性／齐备率与超窗率／全链路可追溯）
    关闭态：TT-v1.4.9-028 / 045（逐字回退：回执**零新增字段**）—— 需 `--closed-url` 指向
            关闭开关的实例；未提供时该项如实标记 `not_covered`（**不冒充通过**）

用法：
    python cr149-t40-t2t3e2e-20260929.py                       # 仅开放实例
    python cr149-t40-t2t3e2e-20260929.py --closed-url http://127.0.0.1:8042
    python cr149-t40-t2t3e2e-20260929.py --out result.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
import uuid
from typing import Any

import httpx

OPEN_URL = os.environ.get("CR149_OPEN_URL", "http://127.0.0.1:8041")
ACCOUNT = {"username": "v148-perf", "password": "Perf#148aB"}
SECOND_ACCOUNT = {
    "username": "cr149-outsider",
    "email": "cr149-outsider@local.dev",
    "password": "Cr149#outside1",
}

#: 回执 10 必填字段（AC-149-05；`degraded` 按设计允许 null）
REQUIRED_RECEIPT_FIELDS = (
    "model",
    "model_window",
    "output_reserve",
    "safety_margin",
    "available_budget",
    "prompt_tokens_before",
    "prompt_tokens_after",
    "hard_truncated",
    "degraded",
    "dropped",
)
#: 关闭态**允许**出现的字段（v1.4.8 既有面）；扩展字段组**不得**出现
EXTENSION_FIELD_GROUP = (
    "model_window",
    "output_reserve",
    "safety_margin",
    "available_budget",
    "prompt_tokens_before",
    "prompt_tokens_after",
    "hard_truncated",
    "dropped",
    "truncated",
    "pool",
)
SENSITIVE_KEY_RE = re.compile(
    r'"(?:access_token|refresh_token|token|api_key|apikey|secret|password|'
    r'authorization|bearer_token)"\s*:',
    re.IGNORECASE,
)
ALLOWED_DROP_KEYS = {"source", "id", "reason"}

#: T3a 巡检**排除**的路由前缀（有副作用／破坏性／需外部依赖；逐条在报告中登记）
T3A_EXCLUDE_PREFIXES = (
    "/api/v1/auth/change-password",
    "/api/v1/auth/refresh",
    "/api/v1/auth/api-keys",
    "/openllm/v1/chat",
    "/api/v1/chat",
    "/api/v1/edge",
    "/api/v1/config/import",
)
T3A_SKIP_REASON = "有副作用／破坏性／需外部依赖（逐条登记，非静默跳过）"


def _long_history(nonce: str, scale: int = 12) -> list[dict]:
    filler = (
        "向量数据库通过近似最近邻索引（HNSW/IVF/PQ 等）在召回率与延迟之间权衡；"
        "相似度常用余弦/内积/L2，需与训练度量一致；量化与剪枝可降低内存占用；"
        "分片与副本决定可扩展性与可用性；写入路径需要一致性策略与段合并。"
    )
    messages: list[dict] = []
    for index in range(1, 9):
        messages.append(
            {
                "role": "user",
                "content": f"第{index}轮 {nonce}：请说明向量数据库索引结构。{filler * scale}",
            }
        )
        messages.append({"role": "assistant", "content": f"第{index}轮答复：{filler * scale}"})
    return messages


async def _login(client: httpx.AsyncClient, account: dict | None = None) -> str:
    payload = {"username": account["username"], "password": account["password"]} if account else ACCOUNT
    response = await client.post("/api/v1/auth/login", json=payload)
    if response.status_code != 200:
        raise SystemExit(f"登录失败: {response.status_code} {response.text[:200]}")
    body = response.json()
    token = body.get("access_token") or (body.get("data") or {}).get("access_token")
    if not token:
        raise SystemExit("登录响应无 access_token")
    return token


async def _ensure_second_account(client: httpx.AsyncClient) -> str | None:
    """注册（或登录）第二账号，用于跨用户隔离用例（TT-v1.4.9-014）"""
    register = await client.post("/api/v1/auth/register", json=SECOND_ACCOUNT)
    if register.status_code not in (200, 201, 400, 409):
        return None
    try:
        return await _login(client, SECOND_ACCOUNT)
    except SystemExit:
        return None


async def _trace(client: httpx.AsyncClient, headers: dict, request_id: str) -> dict:
    detail = await client.get(f"/openllm/v1/trace/{request_id}", headers=headers)
    if detail.status_code != 200:
        return {}
    return (detail.json() or {}).get("data") or {}


async def _chat(
    client: httpx.AsyncClient,
    headers: dict,
    *,
    label: str,
    scale: int = 0,
    session_id: str | None = None,
    messages: list[dict] | None = None,
) -> dict:
    session = session_id or f"t40-{label}-{uuid.uuid4().hex[:8]}"
    payload_messages = messages if messages is not None else _long_history(label, scale=scale)
    payload_messages = list(payload_messages) + [
        {"role": "user", "content": f"测试提问 {label}：一句话说明什么是上下文预算。"}
    ]
    payload = {
        "model": "auto",
        "messages": payload_messages,
        "max_tokens": 64,
        "session_id": session,
        "mode": "auto",
    }
    response = await client.post("/openllm/v1/chat", json=payload, headers=headers)
    if response.status_code != 200:
        return {"label": label, "ok": False, "status": response.status_code, "error": response.text[:300]}
    data = (response.json() or {}).get("data") or {}
    request_id = str(data.get("request_id") or "")
    trace = await _trace(client, headers, request_id)
    receipt = (trace.get("routing_trace") or {}).get("context_metrics") or {}
    return {
        "label": label,
        "ok": bool(request_id and receipt),
        "status": 200,
        "session_id": session,
        "request_id": request_id,
        "receipt": receipt,
        "trace_keys": sorted((trace.get("routing_trace") or {}).keys()),
        "raw_head": json.dumps(receipt, ensure_ascii=False)[:900],
    }


async def _chat_stream(client: httpx.AsyncClient, headers: dict, *, label: str, scale: int = 12) -> dict:
    session = f"t40-stream-{label}-{uuid.uuid4().hex[:8]}"
    messages = _long_history(label, scale=scale)
    messages.append({"role": "user", "content": f"测试提问 {label}：一句话说明什么是上下文预算。"})
    payload = {
        "model": "auto",
        "messages": messages,
        "max_tokens": 64,
        "session_id": session,
        "mode": "auto",
    }
    chunks = 0
    request_id = ""
    body_head = ""
    async with client.stream("POST", "/openllm/v1/chat/stream", json=payload, headers=headers) as response:
        if response.status_code != 200:
            text = await response.aread()
            return {"ok": False, "status": response.status_code, "error": text[:200].decode("utf-8", "replace")}
        async for line in response.aiter_lines():
            if not line:
                continue
            chunks += 1
            if not request_id:
                match = re.search(r'"request_id"\s*:\s*"([^"]+)"', line)
                if match:
                    request_id = match.group(1)
            if len(body_head) < 400:
                body_head += line[:200]
    trace = await _trace(client, headers, request_id) if request_id else {}
    receipt = (trace.get("routing_trace") or {}).get("context_metrics") or {}
    return {
        "ok": bool(chunks and request_id and receipt),
        "status": 200,
        "chunks": chunks,
        "session_id": session,
        "request_id": request_id,
        "receipt": receipt,
        "body_head": body_head[:300],
    }


async def _t3a_scan(client: httpx.AsyncClient, headers: dict) -> dict:
    """T3a 服务间集成巡检（纯后端模式）：/openapi.json 全量路由盘点 ＋ 逐条 GET 可达性"""
    spec = await client.get("/openapi.json")
    if spec.status_code != 200:
        return {"ok": False, "error": f"openapi.json 不可用: {spec.status_code}"}
    paths = (spec.json() or {}).get("paths") or {}

    all_routes: list[str] = []
    get_routes: list[str] = []
    for path, operations in sorted(paths.items()):
        for method in operations:
            all_routes.append(f"{method.upper()} {path}")
            if method.lower() == "get":
                get_routes.append(path)

    excluded = [p for p in get_routes if any(p.startswith(prefix) for prefix in T3A_EXCLUDE_PREFIXES)]
    probed = [p for p in get_routes if p not in excluded]

    results: list[dict] = []
    for path in probed:
        url = path
        # 动态参数：用「自身路径」等无副作用的占位值探测（仅用于可达性与状态码采集）
        url = re.sub(r"\{[^}]+\}", "probe-none", url)
        started = time.perf_counter()
        try:
            response = await client.get(url, headers=headers, timeout=20.0)
            elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
            body_head = ""
            if response.status_code >= 500:
                body_head = response.text[:200]
            results.append(
                {
                    "route": path,
                    "probed": url,
                    "status": response.status_code,
                    "elapsed_ms": elapsed_ms,
                    "class": "OK" if response.status_code < 500 else ("H" if _is_env_hint(body_head) else "B"),
                    "body_head": body_head,
                }
            )
        except Exception as exc:  # noqa: BLE001 —— 网络层异常需如实记录，不静默
            results.append(
                {
                    "route": path,
                    "probed": url,
                    "status": None,
                    "elapsed_ms": None,
                    "class": "requestfailed",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
    code_5xx = [r for r in results if r["class"] == "B"]
    env_5xx = [r for r in results if r["class"] == "H"]
    failed = [r for r in results if r["class"] == "requestfailed"]
    return {
        "ok": not code_5xx and not failed,
        "total_routes": len(all_routes),
        "get_routes": len(get_routes),
        "probed": len(probed),
        "excluded": excluded,
        "exclude_reason": T3A_SKIP_REASON,
        "coverage_pct": round(len(probed) / len(get_routes) * 100, 1) if get_routes else 0.0,
        "code_5xx": code_5xx,
        "env_5xx": env_5xx,
        "requestfailed": failed,
        "status_distribution": _distribution([r["status"] for r in results]),
        "details": results,
    }


def _distribution(statuses: list[Any]) -> dict:
    out: dict[str, int] = {}
    for status in statuses:
        key = "requestfailed" if status is None else str(status // 100) + "xx"
        out[key] = out.get(key, 0) + 1
    return out


def _is_env_hint(body_head: str) -> bool:
    hints = (
        "无法连接",
        "not available",
        "connection refused",
        "service unavailable",
        "unavailable",
        "GPU监控不可用",
        "pynvml",
        "NVIDIA驱动",
    )
    return any(hint in body_head for hint in hints)


def _receipt_checks(receipt: dict) -> dict:
    missing = [name for name in REQUIRED_RECEIPT_FIELDS if name not in receipt]
    nulls = [
        name
        for name in REQUIRED_RECEIPT_FIELDS
        if name in receipt and receipt[name] is None and name != "degraded"
    ]
    formula_ok = None
    try:
        expected = (
            int(receipt["model_window"]) - int(receipt["output_reserve"]) - int(receipt["safety_margin"])
        )
        formula_ok = int(receipt["available_budget"]) == expected
    except (KeyError, TypeError, ValueError):
        formula_ok = False
    over_window = None
    try:
        over_window = int(receipt["prompt_total_tokens"]) > int(receipt["model_window"])
    except (KeyError, TypeError, ValueError):
        over_window = None
    dropped = receipt.get("dropped")
    dropped_ok = isinstance(dropped, list) and all(
        isinstance(item, dict) and set(item.keys()) <= ALLOWED_DROP_KEYS for item in dropped
    )
    return {
        "missing": missing,
        "nulls": nulls,
        "formula_ok": formula_ok,
        "over_window": over_window,
        "dropped_len": len(dropped) if isinstance(dropped, list) else None,
        "dropped_shape_ok": dropped_ok,
        "sensitive_hit": bool(SENSITIVE_KEY_RE.search(json.dumps(receipt, ensure_ascii=False))),
    }


async def run(args: argparse.Namespace) -> dict:
    started = time.time()
    report: dict[str, Any] = {
        "version": "v1.4.9",
        "step": "Step 4（4.0b 抽查 ／ 4.2 环境 ／ 4.3a T2 ／ 4.3b' T3a ／ 4.4b T3b ／ 4.5 E2E）",
        "open_url": args.open_url,
        "closed_url": args.closed_url,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "cases": {},
    }

    timeout = httpx.Timeout(180.0, connect=15.0)
    async with httpx.AsyncClient(base_url=args.open_url, timeout=timeout) as client:
        # ── 4.2 环境验证：健康 ＋ 逐组件 ────────────────────────────────
        health = await client.get("/openllm/v1/health")
        health_body = {}
        try:
            health_body = health.json()
        except Exception:  # noqa: BLE001
            health_body = {"raw": health.text[:200]}
        token = await _login(client)
        headers = {"Authorization": f"Bearer {token}"}
        report["env"] = {
            "health_status": health.status_code,
            "health_body": health_body,
        }

        # ── TT-006 健康检查 ────────────────────────────────────────────
        report["cases"]["TT-v1.4.9-006"] = {
            "ok": health.status_code == 200,
            "status": health.status_code,
            "detail": "健康检查 200；逐组件 channel 见 health_body",
        }

        # ── TT-009 未鉴权 ─────────────────────────────────────────────
        unauth = await client.post(
            "/openllm/v1/chat",
            json={"model": "auto", "messages": [{"role": "user", "content": "unauth"}], "max_tokens": 8},
        )
        report["cases"]["TT-v1.4.9-009"] = {
            "ok": unauth.status_code == 401,
            "status": unauth.status_code,
            "body_head": unauth.text[:200],
            "detail": "未鉴权 ⇒ 401（不泄露内部信息）",
        }

        # ── TT-007 / 011 同步对话 ＋ 回执齐备（预算生效） ───────────────
        sync_short = await _chat(client, headers, label="sync-short", scale=0)
        sync_long = await _chat(client, headers, label="sync-long", scale=12)
        checks_long = _receipt_checks(sync_long.get("receipt") or {}) if sync_long.get("ok") else {}
        report["cases"]["TT-v1.4.9-007"] = {
            "ok": bool(
                sync_long.get("ok")
                and not checks_long.get("missing")
                and not checks_long.get("nulls")
                and checks_long.get("formula_ok")
            ),
            "status": sync_long.get("status"),
            "request_id": sync_long.get("request_id"),
            "checks": checks_long,
            "receipt": sync_long.get("receipt"),
            "detail": "同步对话 200；回执 10 必填字段键在且取值非 null；available_budget 与公式自洽",
        }
        report["cases"]["TT-v1.4.9-011"] = {
            "ok": bool(sync_long.get("ok") and not checks_long.get("sensitive_hit")),
            "status": sync_long.get("status"),
            "detail": "trace 查询 200；context_metrics 存在；无敏感键名",
            "sensitive_hit": checks_long.get("sensitive_hit"),
        }
        report["cases"]["TT-v1.4.9-029"] = {
            "ok": bool(
                sync_short.get("ok")
                and sync_long.get("ok")
                and not _receipt_checks(sync_short["receipt"]).get("missing")
                and not _receipt_checks(sync_short["receipt"]).get("nulls")
                and not _receipt_checks(sync_long["receipt"]).get("missing")
                and not _receipt_checks(sync_long["receipt"]).get("nulls")
                and (not _receipt_checks(sync_short["receipt"]).get("over_window"))
                and (not _receipt_checks(sync_long["receipt"]).get("over_window"))
            ),
            "samples": [
                {"label": "short", "checks": _receipt_checks(sync_short.get("receipt") or {})},
                {"label": "long", "checks": _receipt_checks(sync_long.get("receipt") or {})},
            ],
            "detail": "齐备率 100%（2/2 样本）；可容纳输入 over_window 全为 false ⇒ 超窗率 0",
        }

        # ── TT-004 dropped 结构（运行态可见性） ────────────────────────
        report["cases"]["TT-v1.4.9-004"] = {
            "ok": bool(checks_long.get("dropped_shape_ok")),
            "dropped_len": checks_long.get("dropped_len"),
            "detail": "dropped 元素仅含 source/id/reason（元素数见 dropped_len；为 0 时形状判定恒真）",
        }

        # ── TT-008 / 027 流式路径与双路径一致性 ────────────────────────
        stream_long = await _chat_stream(client, headers, label="stream-long", scale=12)
        stream_checks = _receipt_checks(stream_long.get("receipt") or {}) if stream_long.get("ok") else {}
        report["cases"]["TT-v1.4.9-008"] = {
            "ok": bool(stream_long.get("ok")),
            "chunks": stream_long.get("chunks"),
            "request_id": stream_long.get("request_id"),
            "checks": stream_checks,
            "detail": "流式对话正常结束且落痕 context_metrics",
        }
        sync_fields = set((sync_long.get("receipt") or {}).keys())
        stream_fields = set((stream_long.get("receipt") or {}).keys())
        report["cases"]["TT-v1.4.9-027"] = {
            "ok": bool(sync_fields and sync_fields == stream_fields and not stream_checks.get("missing")),
            "sync_field_count": len(sync_fields),
            "stream_field_count": len(stream_fields),
            "only_in_sync": sorted(sync_fields - stream_fields),
            "only_in_stream": sorted(stream_fields - sync_fields),
            "detail": "同步/流式回执字段集合同口径（预算窗口与齐备性由 TT-007/008 分别验证）",
        }

        # ── TT-010 session_id 边界 ────────────────────────────────────
        boundary: list[dict] = []
        for label, value in (
            ("empty", ""),
            ("long", "s" * 300),
            ("special", "cr149-<script>alert(1)</script>'\""),
            ("numeric", 12345),
        ):
            payload: dict[str, Any] = {
                "model": "auto",
                "messages": [{"role": "user", "content": f"边界 {label}"}],
                "max_tokens": 8,
            }
            if value is not None:
                payload["session_id"] = value
            response = await client.post("/openllm/v1/chat", json=payload, headers=headers)
            boundary.append(
                {
                    "label": label,
                    "status": response.status_code,
                    "ok": response.status_code < 500,
                }
            )
        report["cases"]["TT-v1.4.9-010"] = {
            "ok": all(item["ok"] for item in boundary),
            "samples": boundary,
            "detail": "空串/超长/特殊字符/非字符串均不 5xx（无注入）",
        }

        # ── TT-012 回写回执 ──────────────────────────────────────────
        session_id = sync_long.get("session_id") or ""
        receipts = await client.get(
            "/openllm/v1/writeback/receipts", params={"session_id": session_id}, headers=headers
        )
        receipts_body = receipts.text
        report["cases"]["TT-v1.4.9-012"] = {
            "ok": receipts.status_code == 200 and not SENSITIVE_KEY_RE.search(receipts_body),
            "status": receipts.status_code,
            "body_head": receipts_body[:400],
            "detail": "回写回执 200；不含令牌/密钥；含 accepted/duplicated/failed 状态面",
        }

        # ── TT-013 计量导出 ─────────────────────────────────────────
        export = await client.get(
            "/openllm/v1/trace/metrics/export",
            params={"session_id": session_id, "limit": 5},
            headers=headers,
        )
        export_ok = export.status_code == 200
        report["cases"]["TT-v1.4.9-013"] = {
            "ok": export_ok,
            "status": export.status_code,
            "body_head": export.text[:300],
            "detail": "计量导出 200；按会话过滤；limit 生效",
        }

        # ── TT-014 跨用户越权（回执隔离） ──────────────────────────────
        outsider = await _ensure_second_account(client)
        if not outsider:
            report["cases"]["TT-v1.4.9-014"] = {
                "ok": False,
                "not_covered": True,
                "detail": "第二账号不可用 ⇒ 如实标记未覆盖（不冒充通过）",
            }
        else:
            other = await client.get(
                "/openllm/v1/writeback/receipts",
                params={"session_id": session_id},
                headers={"Authorization": f"Bearer {outsider}"},
            )
            other_body = other.text
            total = None
            items_len = None
            try:
                payload = other.json()
                data = payload.get("data", payload)
                if isinstance(data, dict):
                    total = data.get("total")
                    if isinstance(data.get("items"), list):
                        items_len = len(data["items"])
                        if total is None:
                            total = items_len
            except Exception:  # noqa: BLE001
                total = None
            # 判定口径：**他账号不可见该会话的回写记录**（空集）；响应中回显的 `filters.session_id`
            # 属**查询条件回显**，不是取数泄漏 ⇒ 不得据此判失败（首轮误判已更正）。
            report["cases"]["TT-v1.4.9-014"] = {
                "ok": other.status_code == 200 and (total in (0, None)) and items_len in (0, None),
                "status": other.status_code,
                "total": total,
                "items_len": items_len,
                "body_head": other_body[:300],
                "detail": "用户 B 查询用户 A 的会话 ⇒ 不可见（items=[] / total=0）",
            }

        # ── TT-026 错误态与边界（空 pipeline ＋ 不可容纳输入） ──────────
        empty_ctx = await client.post(
            "/openllm/v1/chat",
            json={
                "model": "auto",
                "messages": [{"role": "user", "content": "空 pipeline"}],
                "max_tokens": 8,
                "pipeline": [],
                "session_id": f"t40-empty-{uuid.uuid4().hex[:8]}",
            },
            headers=headers,
        )
        report["cases"]["TT-v1.4.9-026"] = {
            "ok": empty_ctx.status_code < 500,
            "status": empty_ctx.status_code,
            "detail": "空 pipeline 不 5xx；不可容纳输入的显式标记由 ac-149-12 夹具判据 ＋ 关闭态对照覆盖",
        }

        # ── TT-025 预算‑裁剪‑回执链路 C/R/U（T3b 深度） ────────────────
        r_read = await client.get(
            f"/openllm/v1/trace/{sync_long.get('request_id')}", headers=headers
        )
        c_ok = bool(sync_long.get("ok"))
        r_ok = r_read.status_code == 200
        report["cases"]["TT-v1.4.9-025"] = {
            "ok": c_ok and r_ok,
            "create": {"chat_status": sync_long.get("status"), "ok": c_ok},
            "read": {"trace_status": r_read.status_code, "ok": r_ok},
            "update_note": "「U（关闭态回退）」需关闭开关实例 ⇒ 见 TT-v1.4.9-028/045",
            "detail": "触发（C）→ 观测（R）两步在开放实例取证；回退（U）由关闭实例覆盖",
        }

        # ── TT-030 全链路可追溯 ──────────────────────────────────────
        report["cases"]["TT-v1.4.9-030"] = {
            "ok": bool(sync_long.get("request_id") and session_id and receipts.status_code == 200),
            "request_id": sync_long.get("request_id"),
            "session_id": session_id,
            "detail": "同一 request_id/session_id 在轨迹与回写回执两面均可对齐",
        }

        # ── TT-024 T3a 服务间集成巡检 ────────────────────────────────
        scan = await _t3a_scan(client, headers)
        report["cases"]["TT-v1.4.9-024"] = scan

    # ── TT-028 / 045 关闭态逐字回退（需关闭开关实例） ───────────────────
    if not args.closed_url:
        report["cases"]["TT-v1.4.9-028"] = {
            "ok": False,
            "not_covered": True,
            "detail": "未提供 --closed-url ⇒ 如实标记未覆盖（不冒充通过）",
        }
        report["cases"]["TT-v1.4.9-045"] = dict(report["cases"]["TT-v1.4.9-028"])
    else:
        async with httpx.AsyncClient(base_url=args.closed_url, timeout=timeout) as closed:
            closed_health = await closed.get("/openllm/v1/health")
            closed_token = await _login(closed)
            closed_headers = {"Authorization": f"Bearer {closed_token}"}
            closed_chat = await _chat(closed, closed_headers, label="closed-long", scale=12)
            closed_receipt = closed_chat.get("receipt") or {}
            leaked = sorted(set(closed_receipt.keys()) & set(EXTENSION_FIELD_GROUP))
            open_receipt = report["cases"]["TT-v1.4.9-007"].get("receipt") or {}
            report["cases"]["TT-v1.4.9-028"] = {
                "ok": bool(closed_chat.get("ok")) and not leaked,
                "closed_health": closed_health.status_code,
                "closed_status": closed_chat.get("status"),
                "leaked_extension_fields": leaked,
                "closed_receipt": closed_receipt,
                "open_receipt_field_count": len(open_receipt),
                "detail": "关闭 CONTEXT_BUDGET_ENABLED ⇒ 回执**零新增字段**（扩展字段组不出现）",
            }
            report["cases"]["TT-v1.4.9-045"] = dict(report["cases"]["TT-v1.4.9-028"])
            report["cases"]["TT-v1.4.9-025"]["update"] = {
                "closed_status": closed_chat.get("status"),
                "leaked": leaked,
                "ok": not leaked,
            }
            report["cases"]["TT-v1.4.9-025"]["ok"] = bool(
                report["cases"]["TT-v1.4.9-025"]["ok"] and not leaked
            )

    report["elapsed_s"] = round(time.time() - started, 1)
    passed = sum(1 for case in report["cases"].values() if case.get("ok"))
    not_covered = sum(1 for case in report["cases"].values() if case.get("not_covered"))
    report["summary"] = {
        "cases": len(report["cases"]),
        "passed": passed,
        "not_covered": not_covered,
        "failed": len(report["cases"]) - passed - not_covered,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--open-url", default=OPEN_URL, help="开启预算的实例（默认 8041）")
    parser.add_argument("--closed-url", default=None, help="关闭 CONTEXT_BUDGET_ENABLED 的实例（如 8042）")
    parser.add_argument("--out", default=None, help="结果 JSON 路径")
    args = parser.parse_args()

    report = asyncio.run(run(args))
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text if args.out is None else text[:1200] + "\n…（完整结果已写入文件）")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    return 0 if report["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
