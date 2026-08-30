"""聚合编排执行器（阶段一代码式，对齐技术方案 §4/ADR-网关-002）.

POST /api/v1/gateway/aggregate：asyncio.gather 并发调 /proxy 转发链路，
支持 2~3 子请求；整体超时 + 单步超时 + 部分失败策略（return_errors 默认）。
阶段二（DSL 执行器/GraphQL）接口不变，可无缝替换。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from openbase.core.errors import BaseError, ErrorCode

logger = logging.getLogger("openbase.gateway.aggregate")

# 并发上限（信号量限流，避免连接池打满，对齐技术方案 §4.4）
MAX_CONCURRENCY = 8
DEFAULT_TIMEOUT_MS = 5000


async def _fetch_step(
    step: dict[str, Any],
    proxy_base: str,
    semaphore: asyncio.Semaphore,
) -> dict[str, Any]:
    """执行单个子请求（经代理转发链路）.

    Args:
        step: 步骤定义（system/path/method/timeout_ms 等）。
        proxy_base: 代理基础路径（如 /api/v1/proxy）。
        semaphore: 并发信号量。

    Returns:
        {"id", "data"} 或 {"id", "error"}。
    """
    system = str(step.get("system", ""))
    path = str(step.get("path", "")).lstrip("/")
    method = str(step.get("method", "GET")).upper()
    timeout_ms = int(step.get("timeout_ms", 2000))

    if not system or not path:
        return {"id": step.get("id"), "error": "invalid step: system/path required"}

    url = f"{proxy_base}/{system}/{path}"
    try:
        async with semaphore:
            async with httpx.AsyncClient(timeout=max(timeout_ms / 1000, 0.01)) as client:
                response = await asyncio.wait_for(
                    client.request(method, url), timeout=max(timeout_ms / 1000, 0.01)
                )
        if response.status_code >= 400:
            return {"id": step.get("id"), "error": f"upstream {system} error {response.status_code}"}
        return {"id": step.get("id"), "data": response.json()}
    except asyncio.TimeoutError:
        error = f"{step.get('id')} timeout after {timeout_ms}ms"
        logger.warning("aggregate step timeout", extra={"step": step.get("id"), "timeout_ms": timeout_ms})
        return {"id": step.get("id"), "error": error}
    except httpx.TimeoutException:
        error = f"{step.get('id')} timeout after {timeout_ms}ms"
        logger.warning("aggregate step timeout", extra={"step": step.get("id"), "timeout_ms": timeout_ms})
        return {"id": step.get("id"), "error": error}
    except httpx.HTTPError as exc:
        error = f"upstream {system} unreachable: {exc}"
        logger.warning("aggregate step upstream error", extra={"system": system, "error": str(exc)})
        return {"id": step.get("id"), "error": error}


def _apply_mapping(mapping: dict[str, str], step_results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """按 mapping 规则合并结果（支持 ${stepId.data.field} 引用）.

    Args:
        mapping: 目标字段 → 表达式（如 "model_total": "${models.data.total}"）。
        step_results: 各步骤结果 {"id": {"data": {...}} 或 {"error": ...}}。

    Returns:
        合并后的结果字典。
    """
    merged: dict[str, Any] = {}
    for target, expr in mapping.items():
        expr_text = str(expr)
        if expr_text.startswith("${") and expr_text.endswith("}"):
            parts = expr_text[2:-1].split(".")
            step_id = parts[0]
            result = step_results.get(step_id, {})
            if "data" not in result:
                merged[target] = None
                continue
            value: Any = result["data"]
            # 支持 ${stepId.data.field}（标准）与 ${stepId.field}（简写）
            fields = parts[2:] if len(parts) > 1 and parts[1] == "data" else parts[1:]
            for field in fields:
                if isinstance(value, dict):
                    value = value.get(field)
                else:
                    value = None
                    break
            merged[target] = value
        else:
            merged[target] = expr
    return merged


async def execute_aggregate(request: dict[str, Any], proxy_base: str = "/api/v1/proxy") -> dict[str, Any]:
    """执行聚合编排请求.

    Args:
        request: AggregateRequest（steps/timeout_ms/on_partial_failure/mapping）。
        proxy_base: 代理基础路径。

    Returns:
        聚合结果；部分失败时含 errors 明细。

    Raises:
        BaseError: 整体超时（SYS_TIMEOUT）或步骤非法（PARAM_AGGREGATE_STEP_INVALID）。
    """
    steps = request.get("steps") or []
    if not steps or not isinstance(steps, list):
        raise BaseError(ErrorCode.PARAM_AGGREGATE_STEP_INVALID, "aggregate steps required")
    if len(steps) > MAX_CONCURRENCY:
        raise BaseError(ErrorCode.PARAM_AGGREGATE_STEP_INVALID, f"too many steps, max {MAX_CONCURRENCY}")

    timeout_ms = int(request.get("timeout_ms", DEFAULT_TIMEOUT_MS))
    on_partial_failure = str(request.get("on_partial_failure", "return_errors"))
    mapping = request.get("mapping") or {}

    semaphore = asyncio.Semaphore(min(len(steps), MAX_CONCURRENCY))
    try:
        results = await asyncio.wait_for(
            asyncio.gather(*(_fetch_step(s, proxy_base, semaphore) for s in steps)),
            timeout=timeout_ms / 1000,
        )
    except asyncio.TimeoutError as exc:
        raise BaseError(ErrorCode.SYS_TIMEOUT, "aggregate overall timeout") from exc

    step_results: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for item in results:
        step_id = str(item.get("id", ""))
        if "error" in item:
            errors.append(str(item["error"]))
            step_results[step_id] = {"error": item["error"]}
        else:
            step_results[step_id] = {"data": item.get("data")}

    if errors:
        if on_partial_failure == "strict":
            raise BaseError(ErrorCode.BIZ_AGGREGATE_PARTIAL_FAILURE, "aggregate strict failure: " + "; ".join(errors))
        # return_errors（默认）/ best_effort：返回成功数据 + errors 明细
        return {"result": _apply_mapping(mapping, step_results), "errors": errors}

    return {"result": _apply_mapping(mapping, step_results), "errors": []}
