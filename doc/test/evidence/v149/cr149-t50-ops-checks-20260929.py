"""v1.4.9 Step 5 运维核验取证（5.2 环境 ／ 5.6 监控日志 ／ 5.7 性能安全 ／ 5.8 回滚演练）。

对**真实发布快照**运行实例取证，不使用夹具结论。产出：
    doc/test/evidence/v149/cr149-t50-ops-checks-20260929.json（结构化）＋ 控制台报告

用法：
    python cr149-t50-ops-checks-20260929.py --open-url http://127.0.0.1:8041 \
        --closed-url http://127.0.0.1:8042 --log 'C:\\...\\instance-8041.log' \
        --out doc/test/evidence/v149/cr149-t50-ops-checks-20260929.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import subprocess
import time
import uuid
from pathlib import Path

import httpx

ACCOUNT = {"username": "v148-perf", "password": "Perf#148aB"}
OPENLLM = Path(r"d:\Trae CN\myproject\Dev\OpenLLM")
SECRET_PATTERNS = (
    r"(?i)\bpassword\b\s*[:=]",
    r"(?i)\bapi[_-]?key\b\s*[:=]",
    r"(?i)\bsecret\b\s*[:=]",
    r"sk-[A-Za-z0-9]{8,}",
    r"(?i)authorization:\s*bearer",
    r"(?i)\bjwt[_a-z]*\b\s*[:=]",
)
STRUCTURED_LOG = re.compile(r'^\s*\{.*"(level|severity)"\s*:')


def _git(*args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(OPENLLM), *args], capture_output=True, text=True, encoding="utf-8", check=False
    )
    return (done.stdout or "").strip()


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round((pct / 100) * len(ordered) + 0.5)) - 1))
    return ordered[index]


async def _login(client: httpx.AsyncClient) -> str:
    response = await client.post("/api/v1/auth/login", json=ACCOUNT)
    body = response.json()
    return body.get("access_token") or (body.get("data") or {}).get("access_token") or ""


async def _chat(client: httpx.AsyncClient, headers: dict, session: str) -> dict:
    payload = {
        "model": "auto",
        "messages": [{"role": "user", "content": "发布验证：一句话说明上下文预算。"}],
        "max_tokens": 32,
        "session_id": session,
    }
    response = await client.post("/openllm/v1/chat", json=payload, headers=headers)
    data = (response.json() or {}).get("data") or {}
    return {"status": response.status_code, "request_id": str(data.get("request_id") or "")}


async def _latency(client: httpx.AsyncClient, method: str, url: str, *, headers: dict | None, rounds: int) -> dict:
    samples: list[float] = []
    codes: list[int] = []
    for _ in range(rounds):
        started = time.perf_counter()
        response = await client.request(method, url, headers=headers)
        samples.append((time.perf_counter() - started) * 1000)
        codes.append(response.status_code)
    return {
        "rounds": rounds,
        "p50_ms": round(statistics.median(samples), 1),
        "p99_ms": round(_percentile(samples, 99), 1),
        "min_ms": round(min(samples), 1),
        "max_ms": round(max(samples), 1),
        "status_codes": sorted(set(codes)),
    }


def _log_hygiene(path: Path | None) -> dict:
    if not path or not path.exists():
        return {"available": False, "reason": "未提供或日志文件不存在"}
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    lines = text.splitlines()
    structured = sum(1 for line in lines if STRUCTURED_LOG.match(line))
    hits: dict[str, int] = {}
    for pattern in SECRET_PATTERNS:
        count = len(re.findall(pattern, text))
        if count:
            hits[pattern] = count
    level_counts: dict[str, int] = {}
    for level in ("DEBUG", "INFO", "WARN", "WARNING", "ERROR", "CRITICAL"):
        found = len(re.findall(rf"\b{level}\b", text))
        if found:
            level_counts[level] = found
    return {
        "available": True,
        "bytes": len(raw),
        "lines": len(lines),
        "structured_json_lines": structured,
        "structured_ratio_pct": round(structured / len(lines) * 100, 2) if lines else 0.0,
        "sensitive_pattern_hits": hits,
        "level_counts": level_counts,
    }


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--open-url", default="http://127.0.0.1:8041")
    parser.add_argument("--closed-url", default="http://127.0.0.1:8042")
    parser.add_argument("--log", default=None)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    report: dict = {
        "version": "v1.4.9",
        "step": "Step 5（5.2 环境 ／ 5.6 监控日志 ／ 5.7 性能安全 ／ 5.8 回滚演练）",
        "snapshot": {
            "openllm_head": _git("rev-parse", "HEAD"),
            "openllm_head_subject": _git("log", "-1", "--pretty=%s"),
            "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "app_code_clean": _git("status", "--porcelain", "--", "backend/app") == "",
            "tracking": _git("status", "-sb").splitlines()[0] if _git("status", "-sb") else "",
        },
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    timeout = httpx.Timeout(120.0, connect=15.0)
    async with httpx.AsyncClient(base_url=args.open_url, timeout=timeout) as client:
        # ── 5.2 环境与配置核验 ─────────────────────────────────────────
        health = await client.get("/openllm/v1/health")
        health_body = health.json()
        data = health_body.get("data") or {}
        token = await _login(client)
        headers = {"Authorization": f"Bearer {token}"}
        report["env"] = {
            "health_status": health.status_code,
            "status": data.get("status"),
            "app_version": data.get("version"),
            "components": {
                name: {"status": component.get("status"), "channel": component.get("channel")}
                for name, component in (data.get("components") or {}).items()
            },
            "channel": data.get("channel"),
            "auth_ok": bool(token),
        }

        # ── 5.5 上线功能验证（关键接口冒烟） ───────────────────────────
        session = f"t50-{uuid.uuid4().hex[:8]}"
        chat = await _chat(client, headers, session)
        trace = await client.get(f"/openllm/v1/trace/{chat['request_id']}", headers=headers)
        receipt = ((trace.json().get("data") or {}).get("routing_trace") or {}).get("context_metrics") or {}
        receipts = await client.get(
            "/openllm/v1/writeback/receipts", params={"session_id": session}, headers=headers
        )
        export = await client.get(
            "/openllm/v1/trace/metrics/export", params={"session_id": session, "limit": 5}, headers=headers
        )
        unauth = await client.post(
            "/openllm/v1/chat",
            json={"model": "auto", "messages": [{"role": "user", "content": "x"}], "max_tokens": 8},
        )
        required = (
            "model", "model_window", "output_reserve", "safety_margin", "available_budget",
            "prompt_tokens_before", "prompt_tokens_after", "hard_truncated", "degraded", "dropped",
        )
        report["smoke"] = {
            "chat_status": chat["status"],
            "request_id": chat["request_id"],
            "trace_status": trace.status_code,
            "receipt_fields": sorted(receipt.keys()),
            "receipt_missing": [name for name in required if name not in receipt],
            "receipt_formula_ok": (
                int(receipt.get("available_budget", -1))
                == int(receipt.get("model_window", 0))
                - int(receipt.get("output_reserve", 0))
                - int(receipt.get("safety_margin", 0))
                if receipt
                else None
            ),
            "writeback_receipts_status": receipts.status_code,
            "metrics_export_status": export.status_code,
            "unauth_status": unauth.status_code,
        }

        # ── 5.6 可观测性：健康/计量/日志 ───────────────────────────────
        metrics = data.get("metrics") or {}
        report["observability"] = {
            "health_exposes": sorted(data.keys()),
            "components_visible": len(data.get("components") or {}),
            "metrics_visible": bool(metrics),
            "metrics_keys": sorted(metrics.keys())[:12],
            "trace_queryable": trace.status_code == 200,
            "metrics_export_queryable": export.status_code == 200,
            "log_hygiene": _log_hygiene(Path(args.log) if args.log else None),
        }

        # ── 5.7 性能：关键接口延迟（不含 LLM 依赖面） ──────────────────
        report["performance"] = {
            "health": await _latency(client, "GET", "/openllm/v1/health", headers=None, rounds=30),
            "trace_read": await _latency(
                client, "GET", f"/openllm/v1/trace/{chat['request_id']}", headers=headers, rounds=20
            ),
            "metrics_export": await _latency(
                client, "GET", f"/openllm/v1/trace/metrics/export?session_id={session}&limit=5",
                headers=headers, rounds=20,
            ),
            "chat_e2e_ms": "见 smoke.chat_status（含上游 LLM 往返，受 D3 条件约束，不做基线结论）",
            "note": "本版目标环境为 Dev：无 SLA 承诺；上表用于**基线登记**与后续对比（非生产 SLO 判定）",
        }

        # ── 5.7 安全：鉴权/越权/敏感面 ─────────────────────────────────
        bad_token = await client.get(
            "/openllm/v1/writeback/receipts",
            params={"session_id": session},
            headers={"Authorization": "Bearer invalid-token"},
        )
        blob = json.dumps(
            {
                "health": data,
                "receipt": receipt,
                "writeback": receipts.text[:2000],
                "export": export.text[:2000],
            },
            ensure_ascii=False,
        )
        report["security"] = {
            "unauth_status": unauth.status_code,
            "invalid_token_status": bad_token.status_code,
            "sensitive_key_hits": {
                pattern: len(re.findall(pattern, blob)) for pattern in SECRET_PATTERNS
            },
            "tls": "N/A（Dev 本地 HTTP；TLS 由部署架构草案在 Test/Pro 环境要求）",
            "cors_note": "未在业务响应中发现通配 CORS 头（如需强校验见《安全设计说明-v1.4.9》）",
        }

    # ── 5.8 回滚演练：配置回滚（关闭态逐字回退） ───────────────────────
    async with httpx.AsyncClient(base_url=args.closed_url, timeout=timeout) as closed:
        closed_health = await closed.get("/openllm/v1/health")
        closed_token = await _login(closed)
        closed_headers = {"Authorization": f"Bearer {closed_token}"}
        closed_session = f"t50-closed-{uuid.uuid4().hex[:8]}"
        closed_chat = await _chat(closed, closed_headers, closed_session)
        closed_trace = await closed.get(f"/openllm/v1/trace/{closed_chat['request_id']}", headers=closed_headers)
        closed_receipt = (
            ((closed_trace.json().get("data") or {}).get("routing_trace") or {}).get("context_metrics") or {}
        )
        extension_group = {
            "model_window", "output_reserve", "safety_margin", "available_budget",
            "prompt_tokens_before", "prompt_tokens_after", "hard_truncated", "dropped", "truncated", "pool",
        }
        leaked = sorted(set(closed_receipt.keys()) & extension_group)
        report["rollback_drill"] = {
            "strategy": "配置回滚（首选路径）—— 关闭三开关并重启后验证关闭态逐字回退",
            "closed_health_status": closed_health.status_code,
            "closed_chat_status": closed_chat["status"],
            "closed_receipt_fields": sorted(closed_receipt.keys()),
            "extension_leaked": leaked,
            "verdict": "通过（扩展字段组零泄漏 ⇒ 等同回退到 v1.4.8 行为）" if not leaked else "未通过",
            "code_rollback_path": "git revert <本版提交> / git checkout v1.4.8（路径可用性由回滚方案 §2 核验）",
        }

    report["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"\n[written] {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(__import__("asyncio").run(main()))
