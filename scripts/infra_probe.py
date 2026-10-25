"""共享基础设施「数据面」探针（stdlib-only）。

用途：供 `scripts/service-orchestrator.ps1` 在**启动服务前**与**周期复检**时判定
主用/备用基础设施是否「真的能用」，而不是只看端口是否监听。

判定层级（每个目标返回 `layer`）：
- `data-plane`：完成了该设施的最小真实读写/查询语义
  - PostgreSQL：`psql -c "select 1"`（TCP + 认证 + 库存在 + 可执行查询）
  - Redis：`AUTH`（可选）→ `PING` → `DBSIZE`
  - Qdrant：`GET /collections`（需要可读集合元数据）
  - Neo4j：`POST /db/<db>/tx/commit` 执行 `RETURN 1 AS ok`
  - MinIO：`GET /minio/health/ready`（服务端就绪含磁盘/集群状态；版本与桶列表需 mc）
- `tcp`：脚本或依赖不可用时的降级判定（会写入 `degraded` 说明，不静默）

用法：
    python scripts/infra_probe.py --spec <spec.json> --out <result.json>

spec 结构（**不含明文口令**：口令一律通过 `*_env` 指向环境变量名）：
    {
      "timeout_sec": 3,
      "psql": "D:\\\\PostgreSQL\\\\17\\\\bin\\\\psql.exe",
      "targets": {
        "pg":      {"primary": {...}, "standby": {...}},
        "redis":   {"primary": {...}, "standby": {...}},
        "qdrant":  {"primary": {...}, "standby": {...}},
        "neo4j":   {"primary": {...}, "standby": {...}},
        "minio":   {"primary": {...}, "standby": {...}}
      }
    }

输出：`{"schema_version":1,"generated_at":...,"probe_mode":...,"degraded":[...],"targets":{...}}`
每个目标：`{ok, layer, latency_ms, detail, extra}`。
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Any

DEFAULT_TIMEOUT_SEC = 3
DEFAULT_PSQL = r"D:\PostgreSQL\17\bin\psql.exe"


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _fail(detail: str, layer: str = "data-plane", latency_ms: int = 0, **extra: Any) -> dict[str, Any]:
    return {"ok": False, "layer": layer, "latency_ms": latency_ms, "detail": detail, "extra": extra}


def _ok(detail: str, latency_ms: int, layer: str = "data-plane", **extra: Any) -> dict[str, Any]:
    return {"ok": True, "layer": layer, "latency_ms": latency_ms, "detail": detail, "extra": extra}


def _env_or(target: dict[str, Any], env_key: str, direct_key: str, default: str = "") -> str:
    """优先从 `*_env` 指定的环境变量取值，避免把口令写进 spec 文件。"""
    env_name = target.get(env_key)
    if env_name:
        value = os.environ.get(str(env_name))
        if value is not None:
            return value
    return str(target.get(direct_key, default))


# ---------------------------------------------------------------------------
# PostgreSQL：psql 子进程（口令经 PGPASSWORD 传递，不出现在命令行）
# ---------------------------------------------------------------------------


def probe_pg(target: dict[str, Any], timeout: int, psql: str) -> dict[str, Any]:
    host = target.get("host", "")
    port = int(target.get("port", 5432))
    if not host:
        return _fail("未配置主机")
    if not os.path.exists(psql):
        return _fail(f"psql 不存在：{psql}", layer="tcp")

    user = _env_or(target, "user_env", "user")
    password = _env_or(target, "password_env", "password")
    database = _env_or(target, "database_env", "database", "postgres")

    env = os.environ.copy()
    env["PGPASSWORD"] = password
    env["PGCONNECT_TIMEOUT"] = str(timeout)
    command = [
        psql,
        "-h",
        host,
        "-p",
        str(port),
        "-U",
        user,
        "-d",
        database,
        "-tA",
        "-v",
        "ON_ERROR_STOP=1",
        "-c",
        "select 1",
        "-c",
        "show server_version",
    ]
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout + 2,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return _fail("psql 超时", latency_ms=_elapsed_ms(started))
    except OSError as exc:
        return _fail(f"psql 调用失败：{exc}", latency_ms=_elapsed_ms(started))

    latency = _elapsed_ms(started)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip().splitlines()
        return _fail(detail[0] if detail else f"psql 退出码 {completed.returncode}", latency_ms=latency)

    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if not lines or lines[0] != "1":
        return _fail("select 1 结果异常", latency_ms=latency)
    server_version = lines[1] if len(lines) > 1 else ""
    return _ok("select 1 ok", latency, server_version=server_version)


# ---------------------------------------------------------------------------
# Redis：最小 RESP 客户端（AUTH → PING → DBSIZE）
# ---------------------------------------------------------------------------


def _resp_encode(*args: str) -> bytes:
    chunks = [b"*%d\r\n" % len(args)]
    for arg in args:
        raw = arg.encode("utf-8")
        chunks.append(b"$%d\r\n%s\r\n" % (len(raw), raw))
    return b"".join(chunks)


def _resp_read(stream) -> Any:
    line = stream.readline()
    if not line:
        raise ConnectionError("连接被关闭")
    prefix, payload = line[:1], line[1:].rstrip(b"\r\n")
    if prefix == b"+":
        return payload.decode("utf-8", "replace")
    if prefix == b"-":
        raise RuntimeError(payload.decode("utf-8", "replace"))
    if prefix == b":":
        return int(payload)
    if prefix == b"$":
        length = int(payload)
        if length < 0:
            return None
        data = stream.read(length + 2)
        return data[:-2].decode("utf-8", "replace")
    if prefix == b"*":
        count = int(payload)
        if count < 0:
            return None
        return [_resp_read(stream) for _ in range(count)]
    raise RuntimeError(f"无法解析的 RESP 前缀：{prefix!r}")


def probe_redis(target: dict[str, Any], timeout: int) -> dict[str, Any]:
    host = target.get("host", "")
    port = int(target.get("port", 6379))
    password = _env_or(target, "password_env", "password")
    if not host:
        return _fail("未配置主机")

    started = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout) as conn:
            conn.settimeout(timeout)
            stream = conn.makefile("rb")
            if password:
                conn.sendall(_resp_encode("AUTH", password))
                reply = _resp_read(stream)
                if reply != "OK":
                    return _fail("AUTH 未返回 OK", latency_ms=_elapsed_ms(started))
            conn.sendall(_resp_encode("PING"))
            if _resp_read(stream) != "PONG":
                return _fail("PING 未返回 PONG", latency_ms=_elapsed_ms(started))
            conn.sendall(_resp_encode("DBSIZE"))
            size = _resp_read(stream)
            conn.sendall(_resp_encode("INFO", "replication"))
            info = _resp_read(stream) or ""
    except (OSError, RuntimeError, ConnectionError) as exc:
        return _fail(str(exc), latency_ms=_elapsed_ms(started))

    role = ""
    link = ""
    for line in str(info).splitlines():
        if line.startswith("role:"):
            role = line.split(":", 1)[1].strip()
        elif line.startswith("master_link_status:"):
            link = line.split(":", 1)[1].strip()
    return _ok("PING+DBSIZE ok", _elapsed_ms(started), keys=int(size or 0), role=role, master_link_status=link)


# ---------------------------------------------------------------------------
# HTTP 类：Qdrant / Neo4j / MinIO
# ---------------------------------------------------------------------------


def _http_json(url: str, timeout: int, method: str = "GET", body: bytes | None = None,
               headers: dict[str, str] | None = None) -> tuple[int, Any]:
    request = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - 仅访问已登记内网端点
        return response.status, json.loads(response.read() or b"{}")


def probe_qdrant(target: dict[str, Any], timeout: int) -> dict[str, Any]:
    url = str(target.get("url", "")).rstrip("/")
    if not url:
        return _fail("未配置 URL")
    api_key = _env_or(target, "api_key_env", "api_key")
    headers = {"api-key": api_key} if api_key else {}
    started = time.perf_counter()
    try:
        status, payload = _http_json(f"{url}/collections", timeout, headers=headers)
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError) as exc:
        return _fail(str(exc), latency_ms=_elapsed_ms(started))
    collections = ((payload or {}).get("result") or {}).get("collections") or []
    if status != 200:
        return _fail(f"HTTP {status}", latency_ms=_elapsed_ms(started))
    version = str(target.get("version_hint", ""))
    return _ok("GET /collections ok", _elapsed_ms(started), collections=len(collections), version_hint=version)


def probe_neo4j(target: dict[str, Any], timeout: int) -> dict[str, Any]:
    host = target.get("host", "")
    port = int(target.get("http_port", 7474))
    database = str(target.get("database", "neo4j"))
    user = _env_or(target, "user_env", "user", "neo4j")
    password = _env_or(target, "password_env", "password")
    if not host:
        return _fail("未配置主机")

    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    body = json.dumps({"statements": [{"statement": "RETURN 1 AS ok"}]}).encode()
    headers = {"Content-Type": "application/json", "Authorization": f"Basic {token}"}
    started = time.perf_counter()
    try:
        status, payload = _http_json(
            f"http://{host}:{port}/db/{database}/tx/commit", timeout, method="POST", body=body, headers=headers
        )
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError) as exc:
        return _fail(str(exc), latency_ms=_elapsed_ms(started))
    errors = (payload or {}).get("errors") or []
    if status != 200 or errors:
        detail = errors[0].get("message") if errors and isinstance(errors[0], dict) else f"HTTP {status}"
        return _fail(str(detail), latency_ms=_elapsed_ms(started))
    rows = ((payload or {}).get("results") or [{}])[0].get("data") or []
    return _ok("RETURN 1 ok", _elapsed_ms(started), rows=len(rows))


def probe_minio(target: dict[str, Any], timeout: int) -> dict[str, Any]:
    host = target.get("host", "")
    port = int(target.get("port", 9000))
    if not host:
        return _fail("未配置主机")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(f"http://{host}:{port}/minio/health/ready", timeout=timeout) as response:  # noqa: S310
            status = response.status
    except (urllib.error.URLError, OSError) as exc:
        return _fail(str(exc), latency_ms=_elapsed_ms(started))
    if status != 200:
        return _fail(f"HTTP {status}", latency_ms=_elapsed_ms(started))
    return _ok("health/ready ok", _elapsed_ms(started), note="就绪探针；桶/对象列表需 mc")


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


PROBES = {
    "pg": probe_pg,
    "redis": probe_redis,
    "qdrant": probe_qdrant,
    "neo4j": probe_neo4j,
    "minio": probe_minio,
}


def run(spec: dict[str, Any]) -> dict[str, Any]:
    timeout = int(spec.get("timeout_sec", DEFAULT_TIMEOUT_SEC))
    psql = str(spec.get("psql") or DEFAULT_PSQL)
    results: dict[str, Any] = {}
    degraded: list[str] = []

    for name, sides in (spec.get("targets") or {}).items():
        probe = PROBES.get(name)
        if probe is None:
            degraded.append(f"{name}: 未知探针类型")
            continue
        for side, target in (sides or {}).items():
            key = f"{name}.{side}"
            if not target:
                results[key] = _fail("未配置端点")
                continue
            if name == "pg":
                results[key] = probe(target, timeout, psql)
            else:
                results[key] = probe(target, timeout)
            if results[key]["layer"] == "tcp":
                degraded.append(f"{key}: {results[key]['detail']}")

    layers = {entry["layer"] for entry in results.values()}
    probe_mode = "data-plane" if layers and layers <= {"data-plane"} else ("partial" if results else "none")
    return {
        "schema_version": 1,
        "generated_at": _now_iso(),
        "probe_mode": probe_mode,
        "degraded": degraded,
        "targets": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="共享基础设施数据面探针")
    parser.add_argument("--spec", required=True)
    parser.add_argument("--out", default="")
    args = parser.parse_args(argv)

    with open(args.spec, encoding="utf-8-sig") as handle:
        spec = json.load(handle)
    payload = run(spec)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
