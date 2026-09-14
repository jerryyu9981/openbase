"""上游响应专段观测（C-16）——把上游子系统的响应"送进日志".

设计依据：《OpenBase-人工端到端测试日志记录方案-v1.0.0》v1.1.0
- §11.1 实证缺口：代理层原有 5 处日志仅覆盖「绕过审计 / 服务密钥写拒绝 / 上游不可达 /
  上游 402」，上游**正常响应与业务错误响应未留痕** → 无法回答「错误出在网关还是上游」；
- §11.5 归因矩阵（本模块提供字段来源）：401/403 信任链/403 K03 → 网关层；502 → 网络/上游
  不可达；上游 4xx/5xx + ``upstream_error_code`` → 上游子系统；
- §5 批 4 C-16：字段 ``upstream_system``/``upstream_status``/``upstream_error_code``/
  ``upstream_duration_ms``/``upstream_digest``（+ 开关下 ``upstream_body_summary``）；
  **成功与业务错误路径统一补记**，异常路径**复用同一结构**（不新增日志点）。

三条口径：

1. **结构性字段恒记**：状态码/耗时/digest 不涉及隐私（digest 为单向摘要），无需开关；
2. **摘要受红线约束**：``upstream_body_summary`` 仅在 ``OPENBASE_CAPTURE_UPSTREAM=1``
   （且非生产）时产出，产出前必经 :func:`openbase.core.mask.observe_payload` 脱敏；
3. **汇聚到请求级记录**：专段写入 ``request.state.upstream_observation``，由审计中间件并入
   **同一条** L1 记录（C-15 网关观测 + C-16 上游观测同行，归因免跨行 join）。
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from typing import Any

from openbase.core.mask import digest_of, observe_payload

__all__ = [
    "UPSTREAM_SEGMENT_FIELDS",
    "build_upstream_segment",
    "elapsed_ms",
    "extract_upstream_error_code",
    "publish_upstream_observation",
]

# 专段字段（与审计模块 UPSTREAM_FIELD_NAMES 对齐；upstream_keys 为过深/超限时的键名清单）
UPSTREAM_SEGMENT_FIELDS: tuple[str, ...] = (
    "upstream_system",
    "upstream_status",
    "upstream_error_code",
    "upstream_duration_ms",
    "upstream_digest",
    "upstream_body_summary",
    "upstream_keys",
    "upstream_error",
)

# 上游错误码可能出现的键位（兼容各子系统契约：顶层 code / error.code / detail.code）
_ERROR_CODE_PATHS: tuple[tuple[str, ...], ...] = (
    ("error_code",),
    ("code",),
    ("error", "code"),
    ("detail", "code"),
)


def elapsed_ms(start: float) -> int:
    """把 ``time.perf_counter()`` 起点换算为毫秒（统一取整口径）."""
    return int((time.perf_counter() - start) * 1000)


def _dig(obj: Any, path: tuple[str, ...]) -> Any:
    """按键路径取值（中途非 dict → None）."""
    current = obj
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def extract_upstream_error_code(payload: bytes | None) -> str | None:
    """提取上游业务错误码（不解析出结果 → None，不臆造）.

    Args:
        payload: 上游响应体字节（可为空/非 JSON）。

    Returns:
        错误码字符串；仅接受标量（str/int）取值。
    """
    if not payload:
        return None
    import json

    try:
        decoded = json.loads(payload.decode("utf-8", errors="replace"))
    except ValueError:
        return None
    if not isinstance(decoded, dict):
        return None
    for path in _ERROR_CODE_PATHS:
        value = _dig(decoded, path)
        if isinstance(value, (str, int)) and str(value):
            return str(value)
    return None


def build_upstream_segment(
    *,
    system: str,
    reached: bool,
    duration_ms: int,
    status_code: int | None = None,
    content_type: str | None = None,
    payload: bytes | None = None,
    capture: bool = False,
    allowlist: Sequence[str] = (),
    error: str | None = None,
) -> dict[str, Any]:
    """构造上游响应专段（C-16；成功/业务错误/异常三路径共用）.

    Args:
        system: 上游系统标识（openllm/openrag/openmemory/dps）。
        reached: 是否拿到上游响应（False = 网络/连接异常）。
        duration_ms: 上游耗时毫秒。
        status_code: 上游 HTTP 状态码（reached=False 时省略）。
        content_type: 上游响应 ``Content-Type``。
        payload: 上游响应体字节（httpx 已持有；reached=False 时为 None）。
        capture: 是否允许产出响应体摘要（``OPENBASE_CAPTURE_UPSTREAM``）。
        allowlist: 允许保留原值的字段路径清单。
        error: 异常文本（仅异常路径）。

    Returns:
        仅含非空字段的专段字典（键名见 :data:`UPSTREAM_SEGMENT_FIELDS`）。
    """
    fields: dict[str, Any] = {
        "upstream_system": system,
        "upstream_duration_ms": duration_ms,
    }
    if reached:
        fields["upstream_status"] = status_code
        fields["upstream_content_type"] = content_type
        if payload is not None:
            fields["upstream_digest"] = digest_of(payload)
        error_code = extract_upstream_error_code(payload)
        if error_code:
            fields["upstream_error_code"] = error_code
    if error:
        fields["upstream_error"] = error
    if capture and payload:
        observed = observe_payload(payload, allowlist=allowlist)
        if observed["summary"] is not None:
            fields["upstream_body_summary"] = observed["summary"]
        elif observed["keys"]:
            fields["upstream_keys"] = observed["keys"]
    return {key: value for key, value in fields.items() if value is not None}


def publish_upstream_observation(request: Any, segment: dict[str, Any]) -> dict[str, Any]:
    """把专段挂到 ``request.state.upstream_observation``（同行汇聚 + 调用计数）.

    同一请求内多次调用上游（如聚合编排）时：保留**最近一次**的专段字段，并累计
    ``upstream_calls``，便于人工排查「聚合链路中哪一个上游先坏」。

    Args:
        request: 当前请求（Starlette ``Request``）。
        segment: :func:`build_upstream_segment` 产出的专段。

    Returns:
        写入 ``request.state`` 后的合并结果。
    """
    previous = getattr(request.state, "upstream_observation", None)
    calls = int(previous.get("upstream_calls", 0)) + 1 if isinstance(previous, dict) else 1
    merged = dict(segment)
    merged["upstream_calls"] = calls
    request.state.upstream_observation = merged
    return merged
