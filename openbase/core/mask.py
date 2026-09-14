"""统一脱敏器（C-18）——响应级观测落盘前的唯一脱敏关口.

设计依据：《OpenBase-人工端到端测试日志记录方案-v1.0.0》v1.1.0
- §11.2 红线（D-5）：默认关闭；**开启时强制脱敏**；单条上限 2KB；生产永久关闭；
- §11.4 脱敏规则：凭据 / 个人隐私（手机号保留后 4 位、证件号、邮箱）/ 画像业务域
  默认整体遮蔽（仅留键名与长度）/ 超限或层级过深 → 摘要 + digest；
- §5 批 4 C-18：本模块为 C-15（网关响应摘要）与 C-16（上游响应摘要）的**共同前置**，
  任何响应摘要落盘前必经 :func:`mask_sensitive`。

三条硬约束（与方案 §11.2 一一对应）：

1. **默认零采集**：本模块不做任何开关判断——开关判断在调用方（C-19）；
2. **允许清单最小化**：``OPENBASE_CAPTURE_FIELD_ALLOWLIST`` 命中的字段路径**保留原值**
   （用于错误归因，如 ``error.code``）；使用允许清单即意味着调用方已确认该字段不含隐私；
3. **超限只留结构**：单条 > ``MAX_SUMMARY_BYTES`` 时只保留 ``digest`` 与**键名清单**，
   不保留任何原文片段。

隐私保护与 digest 说明：

- 手机号（11 位）→ 保留前 3 后 4（``138****8888``）；证件号（18 位）→ 保留前 4 后 4；
  邮箱 → 本地部分仅留首字符（``a***@example.com``）；
- :func:`digest_of` 输出 ``sha256:<16 hex>``：**只用于比对两次响应是否同源**，
  不可逆推原文（不存原文亦可比对）。
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from typing import Any

__all__ = [
    "DEFAULT_REDACTED_DOMAINS",
    "MASKED",
    "MAX_DEPTH",
    "MAX_SUMMARY_BYTES",
    "SENSITIVE_KEY_FRAGMENTS",
    "digest_of",
    "mask_sensitive",
    "observe_payload",
]

# 遮蔽占位与截断标记
MASKED: str = "***"
MAX_DEPTH_REPLACEMENT: str = "<max-depth>"
TRUNCATED_MARKER: str = "<truncated>"

# 单条摘要上限（方案 §11.2-3：2KB）
MAX_SUMMARY_BYTES: int = 2048
# 递归深度上限（方案 §11.4：层级 > 5 层 → 摘要，不存原文）
MAX_DEPTH: int = 5

# 敏感键片段（小写匹配）：凭据类，命中即整体遮蔽为 MASKED
SENSITIVE_KEY_FRAGMENTS: tuple[str, ...] = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "access_key",
    "private_key",
    "authorization",
    "credential",
    "cookie",
    "session_id",
    "jwt",
    "signature",
    "bearer",
)

# 默认整体遮蔽的业务域（方案 §11.4：画像等个人隐私域）
DEFAULT_REDACTED_DOMAINS: tuple[str, ...] = (
    "portrait",
    "portraits",
    "profile",
    "profiles",
    "face",
    "faces",
    "face_image",
    "avatar",
)

# 个人隐私文本正则（作用于字符串值，不作用于键名）
_PHONE_PATTERN = re.compile(r"(?<!\d)(\d{3})\d{4}(\d{4})(?!\d)")
_ID_CARD_PATTERN = re.compile(r"(?<!\d)(\d{4})\d{10}(\d{3}[\dXx])(?!\d)")
_EMAIL_PATTERN = re.compile(r"([^\s@])([^\s@]*)@([^\s@]+)")


def digest_of(payload: bytes | str) -> str:
    """计算内容摘要（``sha256:<16 hex>``）——只用于同源比对，不可逆推原文.

    Args:
        payload: 原始字节或文本（可为空）。

    Returns:
        形如 ``sha256:1f2a3b4c5d6e7f80`` 的摘要串。
    """
    data = payload.encode("utf-8", errors="replace") if isinstance(payload, str) else payload
    return f"sha256:{hashlib.sha256(data).hexdigest()[:16]}"


def _mask_text(value: str) -> str:
    """掩码文本中的个人隐私（手机号 / 证件号 / 邮箱）."""
    masked = _PHONE_PATTERN.sub(r"\1****\2", value)
    masked = _ID_CARD_PATTERN.sub(r"\1**********\2", masked)
    return _EMAIL_PATTERN.sub(lambda m: f"{m.group(1)}{MASKED}@{m.group(3)}", masked)


def _is_sensitive_key(key: str) -> bool:
    """键名是否命中凭据类敏感片段（小写包含匹配）."""
    lowered = key.lower()
    return any(fragment in lowered for fragment in SENSITIVE_KEY_FRAGMENTS)


def _is_redacted_domain(key: str) -> bool:
    """键名是否属于默认整体遮蔽的业务域（精确匹配，避免 ``portrait_count`` 误伤）."""
    return key.lower() in DEFAULT_REDACTED_DOMAINS


def _allowlisted(path: str, allowlist: Sequence[str]) -> bool:
    """字段路径是否在允许清单内（精确匹配或子树前缀匹配）."""
    if not path:
        return False
    for entry in allowlist:
        if not entry:
            continue
        if path == entry or path.startswith(f"{entry}."):
            return True
    return False


def _summary_of_value(value: Any) -> dict[str, Any]:
    """整体遮蔽域的占位摘要（仅留类型与规模，不留内容）."""
    if isinstance(value, dict):
        size = len(value)
        shape = "object"
    elif isinstance(value, (list, tuple)):
        size = len(value)
        shape = "array"
    elif isinstance(value, str):
        size = len(value)
        shape = "string"
    else:
        size = 0 if value is None else 1
        shape = type(value).__name__
    return {"_redacted": "domain", "type": shape, "size": size}


def mask_sensitive(
    value: Any,
    *,
    allowlist: Sequence[str] = (),
    path: str = "",
    depth: int = 0,
) -> Any:
    """递归脱敏（凭据 / 个人隐私 / 隐私业务域 / 超深层级）.

    Args:
        value: 任意待脱敏结构（dict/list/标量）。
        allowlist: 保留原值的字段路径清单（如 ``("error.code", "error.message")``）。
        path: 当前字段路径（内部递归用，外部调用无需传）。
        depth: 当前层级（内部递归用）。

    Returns:
        脱敏后的等价结构；层级超过 :data:`MAX_DEPTH` 时返回 ``"<max-depth>"``。
    """
    if _allowlisted(path, allowlist):
        return value
    if depth > MAX_DEPTH:
        return MAX_DEPTH_REPLACEMENT

    if isinstance(value, dict):
        masked: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}" if path else key_text
            if _is_sensitive_key(key_text):
                masked[key_text] = _summary_of_value(item) if isinstance(item, (dict, list)) else MASKED
            elif _is_redacted_domain(key_text):
                # 隐私业务域：**任何类型**都只留类型与规模（含标量，避免单值型隐私字段泄漏）
                masked[key_text] = _summary_of_value(item)
            else:
                masked[key_text] = mask_sensitive(
                    item, allowlist=allowlist, path=child_path, depth=depth + 1
                )
        return masked

    if isinstance(value, (list, tuple)):
        return [
            mask_sensitive(item, allowlist=allowlist, path=f"{path}[]", depth=depth + 1)
            for item in value
        ]

    if isinstance(value, str):
        return _mask_text(value)

    return value


def _max_depth(value: Any, depth: int = 0) -> int:
    """计算结构的最大嵌套层级（标量记 0；用于「层级过深 → 不存原文」判定）."""
    if isinstance(value, dict):
        if not value:
            return depth
        return max(_max_depth(item, depth + 1) for item in value.values())
    if isinstance(value, (list, tuple)):
        if not value:
            return depth
        return max(_max_depth(item, depth + 1) for item in value)
    return depth


def _keys_of(decoded: Any) -> list[str]:
    """顶层键名清单（对象 → 键名；数组 → ``[]`` 标记；标量 → 空）."""
    if isinstance(decoded, dict):
        return [str(key) for key in decoded]
    if isinstance(decoded, list):
        return ["[]"]
    return []


def _decode_json(payload: bytes) -> Any | None:
    """尝试解析 JSON（失败 → None，不抛错）."""
    try:
        return json.loads(payload.decode("utf-8", errors="replace"))
    except ValueError:
        return None


def _summary_of_decoded(decoded: Any, allowlist: Sequence[str]) -> dict[str, Any]:
    """按解码结果的类型装箱摘要（对象/数组/标量三类口径统一在函数内）."""
    if isinstance(decoded, dict):
        return {"keys": _keys_of(decoded), "summary": mask_sensitive(decoded, allowlist=allowlist)}
    if isinstance(decoded, list):
        return {
            "keys": ["[]"],
            "summary": {
                "type": "array",
                "size": len(decoded),
                "items": mask_sensitive(decoded, allowlist=allowlist),
            },
        }
    return {
        "keys": [],
        "summary": {"type": "scalar", "value": mask_sensitive(decoded, allowlist=allowlist)},
    }


def observe_payload(
    payload: bytes | None,
    *,
    allowlist: Sequence[str] = (),
    max_bytes: int = MAX_SUMMARY_BYTES,
) -> dict[str, Any]:
    """响应体观测（C-15/C-16 共用口径）：``bytes`` / ``digest`` / ``keys`` / ``summary``.

    口径（方案 §11.2-3、§11.4）：

    - ``digest`` 始终基于**原始字节**计算（可比对，不含明文）；
    - ``keys`` 为 JSON 顶层键名清单（超限/过深时唯一保留的结构信息）；
    - ``summary`` 仅在**未超限且层级不过深**时产出，且必经 :func:`mask_sensitive`；
    - 超限（> ``max_bytes``）或层级 > :data:`MAX_DEPTH` 或非 JSON 文本 → ``summary=None``；
      前两者 ``truncated=True`` + ``keys`` 保留（方案 §11.4：不存原文，只留键名与 digest）。

    Args:
        payload: 原始响应字节；None 表示未采集。
        allowlist: 保留原值的字段路径清单。
        max_bytes: 单条摘要上限（字节）。

    Returns:
        ``{"bytes": int, "digest": str, "keys": list[str], "summary": Any|None,
        "truncated": bool, "captured": bool}``。
    """
    if payload is None:
        return {
            "bytes": 0,
            "digest": None,
            "keys": [],
            "summary": None,
            "truncated": False,
            "captured": False,
        }

    size = len(payload)
    result: dict[str, Any] = {
        "bytes": size,
        "digest": digest_of(payload),
        "keys": [],
        "summary": None,
        "truncated": size > max_bytes,
        "captured": True,
    }
    if not payload:
        return result

    decoded = _decode_json(payload)

    # 超限（> max_bytes）或层级过深（> MAX_DEPTH）：只留 digest + 顶层键名清单，不存原文
    if size > max_bytes or (decoded is not None and _max_depth(decoded) > MAX_DEPTH):
        result["truncated"] = True
        result["keys"] = _keys_of(decoded)
        return result

    if decoded is None:
        result["summary"] = {
            "type": "non-json",
            "preview": _mask_text(payload.decode("utf-8", errors="replace"))[:200],
        }
        return result

    result.update(_summary_of_decoded(decoded, allowlist))
    return result
