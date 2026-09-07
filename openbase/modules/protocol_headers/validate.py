"""协议头校验与入站白名单分类（P2-1 §3.4/§3.8/§5.4）.

K02 行为矩阵（M1 语义）与 OpenBase 试点共用：
- :func:`validate_identity_headers`：规范头格式/长度校验（非法 → 400
  ``PARAM_HEADER_FORMAT_INVALID``，§3.8 错误码）。
- :func:`assert_trusted_source` / :func:`classify_inbound`：受信来源白名单判定
  （非受信来源携带身份头 → 伪造；门禁后 403 ``PERM_UNTRUSTED_IDENTITY_HEADER``）。
- :func:`strip_untrusted_identity_headers`：剥离期物理剥除入站身份头（§5.4）。
"""
from __future__ import annotations

import logging
from collections.abc import Iterable
from enum import Enum
from typing import Any

from openbase.core.errors import BaseError, ErrorCode
from openbase.modules.protocol_headers.constants import (
    HEADER_PROXY_SOURCE,
    IDENTITY_HEADER_LENGTH_LIMITS,
    INBOUND_IDENTITY_HEADERS,
    header_value_allows,
)

logger = logging.getLogger("openbase.protocol_headers.validate")

__all__ = [
    "InboundClassification",
    "assert_trusted_source",
    "classify_inbound",
    "inbound_identity_headers_present",
    "strip_untrusted_identity_headers",
    "trusted_source_of",
    "validate_header_value",
    "validate_identity_headers",
]


class InboundClassification(str, Enum):
    """入站身份头分类（§3.4 行为矩阵四态）.

    - TRUSTED：白名单来源 + 带身份头（可采纳透传）；
    - SELF_AUTH：无身份头 / 白名单来源无头（自身认证）；
    - FORBIDDEN：非白名单 + 带身份头（enforce 开启 → 403）；
    - IGNORED：非白名单 + 带身份头（过渡期不采信 + 审计标注）。
    """

    TRUSTED = "trusted"
    SELF_AUTH = "self_auth"
    FORBIDDEN = "403"
    IGNORED = "ignored"


def trusted_source_of(request: Any, trusted_sources: Iterable[str] | None = None) -> str | None:
    """读取请求 X-Proxy-Source 来源标识（缺失返回 None）."""
    proxy_source = request.headers.get(HEADER_PROXY_SOURCE) if request is not None else None
    if not proxy_source:
        return None
    return str(proxy_source)


def assert_trusted_source(source: str | None, trusted_sources: Iterable[str]) -> bool:
    """白名单判定：source ∈ trusted_sources 返回 True，否则 False（§3.4/§5.3）.

    Args:
        source: 待判定来源标识（X-Proxy-Source 值；None 视为非受信）。
        trusted_sources: settings.trusted_proxy_sources 解析出的白名单可迭代对象。

    Returns:
        命中白名单返回 True；非白名单/缺失返回 False。
    """
    if not source:
        return False
    whitelist = {str(item) for item in (trusted_sources or [])}
    return source in whitelist


def inbound_identity_headers_present(request: Any) -> bool:
    """入站请求是否携带任意身份头（§3.4 伪造判定输入）."""
    if request is None:
        return False
    for header_name in INBOUND_IDENTITY_HEADERS:
        if request.headers.get(header_name):
            return True
    return False


def classify_inbound(
    request: Any,
    trusted_sources: Iterable[str] | None = None,
    enforce: bool = False,
) -> InboundClassification:
    """K02 行为矩阵 M1 分类（§3.4/§3.9 校验函数）.

    Args:
        request: Starlette Request（读 X-Proxy-Source 与身份头）。
        trusted_sources: 受信来源白名单。
        enforce: 强校验开关（enforce_inbound_identity_headers）。

    Returns:
        见 :class:`InboundClassification`。
    """
    source = trusted_source_of(request)
    is_trusted = assert_trusted_source(source, trusted_sources or [])
    has_identity_headers = inbound_identity_headers_present(request)
    if not has_identity_headers:
        return InboundClassification.SELF_AUTH
    if is_trusted:
        return InboundClassification.TRUSTED
    return (
        InboundClassification.FORBIDDEN if enforce else InboundClassification.IGNORED
    )


def validate_header_value(header_name: str, value: object) -> str:
    """单头值格式校验（§3.8：超长/非法字符 → 400 ``PARAM_HEADER_FORMAT_INVALID``）.

    Args:
        header_name: 头名（HEADER_* 常量，用于取长度上限）。
        value: 头值（None/空/超长/含 CR/LF → 非法）。

    Returns:
        原值（合法）。

    Raises:
        BaseError: 格式非法 → 400 PARAM_HEADER_FORMAT_INVALID。
    """
    text = "" if value is None else str(value)
    if not header_value_allows(text, header_name):
        upper_limit = IDENTITY_HEADER_LENGTH_LIMITS.get(header_name)
        raise BaseError(
            ErrorCode.PARAM_HEADER_FORMAT_INVALID,
            f"invalid {header_name} header value",
            detail={
                "header": header_name,
                "max_length": upper_limit,
                "value_length": len(text),
                "reason": "empty/too-long/control-chars" if text else "empty",
            },
        )
    return text


def validate_identity_headers(headers: Any) -> dict[str, str]:
    """对映射/请求中的规范身份头做整体格式校验（§3.8 校验矩阵）.

    校验范围：入站身份头全集（四头 + X-Agent-Id/X-On-Behalf-Of）。对每个存在且
    非空的身份头执行 :func:`validate_header_value`；首个非法头即抛 400
    ``PARAM_HEADER_FORMAT_INVALID``。合法头原样返回。

    Args:
        headers: 支持 ``.get(name)`` 的对象（request.headers / dict）。

    Returns:
        合法头（name→value）字典。

    Raises:
        BaseError: 任一身份头格式非法 → 400 PARAM_HEADER_FORMAT_INVALID。
    """
    validated: dict[str, str] = {}
    if headers is None:
        return validated
    for header_name in INBOUND_IDENTITY_HEADERS:
        value = headers.get(header_name)
        if value is None:
            continue
        text = str(value)
        if not text:
            continue
        validated[header_name] = validate_header_value(header_name, text)
    return validated


def strip_untrusted_identity_headers(
    header_items: Iterable[tuple[bytes, bytes]],
) -> list[tuple[bytes, bytes]]:
    """剥离非受信入站身份头（§5.4 剥离期；对 scope['headers'] 字节对过滤）.

    Args:
        header_items: ASGI scope headers（bytes 二元组可迭代）。

    Returns:
        过滤后的头列表（身份头被剥除；其余保留）。
    """
    lower_identity = {name.lower().encode("latin-1") for name in INBOUND_IDENTITY_HEADERS}
    filtered: list[tuple[bytes, bytes]] = []
    for name, value in header_items:
        if name.lower() in lower_identity:
            continue
        filtered.append((name, value))
    return filtered
