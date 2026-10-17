"""Q1 方案 A：出站 `X-Subject-ID` 装配契约（2026-10-17）.

裁定：外部主体键 = ``{tenant_code}_{user_id}``，经专用头传输；
``X-User-ID`` 保持 username/主体原义不变。

本组用例锁定：
1. 有主体 + 有租户 → 注入 ``{tenant_code}_{user_id}``；
2. 值使用**未互译**的 OpenBase tenant_code（目标系统映射不影响主体键）；
3. 无租户 / 无身份 → 不注入（零破坏）；
4. 头名纳入入站裁剪集（防伪造）。
"""

from __future__ import annotations

from openbase.modules.protocol_headers.constants import (
    HEADER_SUBJECT_ID,
    HEADER_TENANT_ID,
    HEADER_USER_ID,
    INBOUND_IDENTITY_HEADERS,
)
from openbase.modules.protocol_headers.inject import build_outbound_headers


def test_subject_id_uses_tenant_and_user() -> None:
    headers = build_outbound_headers(
        user_ctx={"id": "1", "tenant_code": "tenant-1", "role": "admin"},
        target_system="llm",
    )
    assert headers[HEADER_SUBJECT_ID] == "tenant-1_1"
    # X-User-ID 语义不变
    assert headers[HEADER_USER_ID] == "1"


def test_subject_id_not_translated_by_target_maps() -> None:
    """主体键取 OpenBase 事实源，不受目标系统码值互译影响。"""
    headers = build_outbound_headers(
        user_ctx={"id": "admin", "tenant_code": "tenant-1", "role": "admin"},
        target_system="dps",
        tenant_value_map={"tenant-1": "dps-tenant-001"},
        org_value_map={"tenant-1": "dps-org-001"},
    )
    assert headers[HEADER_TENANT_ID] == "dps-tenant-001"
    assert headers[HEADER_SUBJECT_ID] == "tenant-1_admin"


def test_no_subject_id_without_tenant() -> None:
    headers = build_outbound_headers(
        user_ctx={"id": "admin", "role": "admin"}, target_system="llm"
    )
    assert HEADER_SUBJECT_ID not in headers


def test_no_subject_id_for_anonymous() -> None:
    headers = build_outbound_headers(user_ctx=None, target_system="llm")
    assert HEADER_SUBJECT_ID not in headers


def test_subject_id_is_inbound_stripped() -> None:
    """Q6：客户端直连带该头应被视为伪造嫌疑（纳入入站裁剪集）。"""
    assert HEADER_SUBJECT_ID in INBOUND_IDENTITY_HEADERS
