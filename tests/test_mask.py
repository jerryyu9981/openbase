"""C-18 统一脱敏器测试（openbase/core/mask.py）.

覆盖方案《OpenBase-人工端到端测试日志记录方案》§11.2 红线与 §11.4 脱敏规则：

- 凭据类键（password/token/secret/api_key/...）→ ``***``；
- 个人隐私：手机号保留前 3 后 4、证件号保留前 4 后 4、邮箱本地部掩码；
- 画像业务域整体遮蔽（仅留类型与规模，不留内容）；
- 层级 > 5 或单条 > 2KB → 只留 digest + 键名清单（不存原文）；
- 允许清单字段路径保留原值（默认空 = 全脱敏）；
- ``digest_of`` 稳定且不可逆推（只用于同源比对）。
"""

from __future__ import annotations

from openbase.core.mask import (
    DEFAULT_REDACTED_DOMAINS,
    MASKED,
    MAX_SUMMARY_BYTES,
    digest_of,
    mask_sensitive,
    observe_payload,
)

# ---- 凭据类 ----

def test_sensitive_keys_are_masked() -> None:
    """凭据类键 → MASKED（含大小写与片段包含匹配）."""
    masked = mask_sensitive(
        {
            "password": "p@ssw0rd",
            "api_key": "sk-live-123",
            "Authorization": "Bearer abc.def",
            "refresh_token": "rt-1",
            "user": "alice",
        }
    )
    assert masked["password"] == MASKED
    assert masked["api_key"] == MASKED
    assert masked["Authorization"] == MASKED
    assert masked["refresh_token"] == MASKED
    assert masked["user"] == "alice"


def test_nested_credential_container_keeps_shape_only() -> None:
    """凭据类键的容器值 → 只留类型与规模（不回落原值）."""
    masked = mask_sensitive({"credentials": {"a": 1, "b": 2}})
    assert masked["credentials"] == {"_redacted": "domain", "type": "object", "size": 2}


# ---- 个人隐私 ----

def test_phone_keeps_prefix_and_suffix() -> None:
    """手机号 → 保留前 3 后 4. """
    assert mask_sensitive({"contact": "13812345678"})["contact"] == "138****5678"


def test_id_card_keeps_head_and_tail() -> None:
    """18 位证件号 → 保留前 4 后 4. """
    assert mask_sensitive({"id_card": "11010519900101123X"})["id_card"] == "1101**********123X"


def test_email_local_part_is_masked() -> None:
    """邮箱 → 本地部分仅留首字符. """
    assert mask_sensitive({"email": "alice@example.com"})["email"] == f"a{MASKED}@example.com"


def test_privacy_masked_inside_free_text() -> None:
    """自由文本内的隐私同样掩码（错误信息/备注常见）."""
    masked = mask_sensitive({"remark": "call 13812345678 or mail bob@corp.io"})
    assert "13812345678" not in masked["remark"]
    assert "bob@corp.io" not in masked["remark"]


# ---- 隐私业务域 ----

def test_redacted_domain_keeps_shape_not_content() -> None:
    """画像域整体遮蔽：只留类型与规模，键名与内容均不外泄. """
    masked = mask_sensitive(
        {"portraits": {"name": "张三", "tags": ["a", "b"]}, "portrait": "base64-data"}
    )
    assert masked["portraits"] == {"_redacted": "domain", "type": "object", "size": 2}
    assert masked["portrait"] == {"_redacted": "domain", "type": "string", "size": 11}
    assert "portrait" in DEFAULT_REDACTED_DOMAINS


def test_redacted_domain_is_exact_match() -> None:
    """域匹配为精确匹配：``portrait_count`` 这类统计字段不被误伤. """
    masked = mask_sensitive({"portrait_count": 3})
    assert masked["portrait_count"] == 3


# ---- 深度与超限 ----

def test_depth_over_limit_is_collapsed() -> None:
    """层级 > 5 → ``<max-depth>``（避免深嵌套绕过脱敏/放大日志）."""
    node: dict = {"leaf": "13812345678"}
    for _ in range(7):
        node = {"child": node}
    masked = mask_sensitive(node)
    assert "<max-depth>" in str(masked)


def test_oversized_payload_keeps_digest_and_keys_only() -> None:
    """单条 > 2KB → summary 为空、仅留 digest + 顶层键名（不存原文）."""
    payload = (
        '{"code":"BIZ_X","message":"boom","items":["' + "x" * (MAX_SUMMARY_BYTES + 10) + '"]}'
    ).encode("utf-8")
    observed = observe_payload(payload)
    assert observed["truncated"] is True
    assert observed["summary"] is None
    assert observed["keys"] == ["code", "message", "items"]
    assert observed["digest"] == digest_of(payload)
    assert "x" * 50 not in str(observed)


def test_summary_is_produced_under_limit() -> None:
    """未超限 → 产出脱敏后的 summary（本用例同时锁定 summary 已经过脱敏）."""
    observed = observe_payload(b'{"code":"BIZ_X","user":{"token":"t-1","phone":"13812345678"}}')
    assert observed["truncated"] is False
    assert observed["summary"]["code"] == "BIZ_X"
    assert observed["summary"]["user"]["token"] == MASKED
    assert observed["summary"]["user"]["phone"] == "138****5678"


# ---- 允许清单 ----

def test_allowlist_keeps_raw_value_for_attribution() -> None:
    """允许清单命中的字段路径保留原值（错误归因需要），其余仍脱敏. """
    observed = observe_payload(
        b'{"error":{"code":"UPSTREAM_500","message":"upstream failed"},"user":"13812345678"}',
        allowlist=("error.code", "error.message"),
    )
    assert observed["summary"]["error"]["code"] == "UPSTREAM_500"
    assert observed["summary"]["error"]["message"] == "upstream failed"
    assert observed["summary"]["user"] == "138****5678"


def test_default_allowlist_is_empty_means_mask_all() -> None:
    """默认（空允许清单）→ 全脱敏：``error.code`` 亦按文本规则处理但键值保留结构. """
    observed = observe_payload(b'{"error":{"code":"AUTH_401"}}')
    assert observed["summary"]["error"]["code"] == "AUTH_401"  # 非隐私文本，非敏感键


# ---- digest 与边界 ----

def test_digest_is_stable_and_differs_by_content() -> None:
    """digest 稳定（同内容同摘要）且随内容变化（可比对、不可逆推）."""
    assert digest_of(b"abc") == digest_of(b"abc")
    assert digest_of(b"abc") != digest_of(b"abd")
    assert digest_of(b"abc").startswith("sha256:")
    assert len(digest_of(b"abc")) == len("sha256:") + 16


def test_observe_payload_none_means_not_captured() -> None:
    """未采集（None）→ captured False，且不产出 digest/summary（零采集语义）. """
    observed = observe_payload(None)
    assert observed == {
        "bytes": 0,
        "digest": None,
        "keys": [],
        "summary": None,
        "truncated": False,
        "captured": False,
    }


def test_non_json_body_is_masked_preview() -> None:
    """非 JSON 响应体 → 只留脱敏后的短预览. """
    observed = observe_payload(b"plain text 13812345678")
    assert observed["summary"]["type"] == "non-json"
    assert "13812345678" not in observed["summary"]["preview"]


def test_json_array_payload_is_summarized_with_size() -> None:
    """JSON 数组 → 记录规模与脱敏后的条目. """
    observed = observe_payload(b'[{"phone":"13812345678"}]')
    assert observed["summary"]["type"] == "array"
    assert observed["summary"]["size"] == 1
    assert observed["summary"]["items"][0]["phone"] == "138****5678"


def test_scalar_and_empty_payloads_are_handled() -> None:
    """标量 JSON 与空体：标量包结构与类型；空体只留 digest（不臆造摘要）. """
    scalar = observe_payload(b"12345")
    assert scalar["summary"] == {"type": "scalar", "value": 12345}

    empty = observe_payload(b"")
    assert empty["captured"] is True
    assert empty["bytes"] == 0
    assert empty["summary"] is None
    assert empty["keys"] == []


def test_oversized_and_deep_array_payloads_keep_array_marker() -> None:
    """超限/过深的数组体 → 键名清单只留 ``[]`` 标记（不存原文）."""
    oversized = observe_payload(b"[" + b"1," * (MAX_SUMMARY_BYTES // 2) + b"1]")
    assert oversized["truncated"] is True
    assert oversized["keys"] == ["[]"]

    deep = observe_payload(b'[[[[[[["deep"]]]]]]]')
    assert deep["truncated"] is True
    assert deep["keys"] == ["[]"]


def test_allowlist_supports_subtree_prefix_and_ignores_blank_entries() -> None:
    """允许清单支持子树前缀；空条目忽略；未命中路径仍脱敏. """
    masked = mask_sensitive(
        {"error": {"message": "call 13812345678"}, "other": "call 13812345678"},
        allowlist=("", "error"),
    )
    assert masked["error"]["message"] == "call 13812345678"
    assert masked["other"] == "call 138****5678"


def test_redacted_domain_scalar_and_array_values_keep_shape_only() -> None:
    """隐私域标量/数组值同样只留类型与规模（含 None 与数组分支）. """
    masked = mask_sensitive({"portraits": ["a", "b"], "avatar": 42, "profile": None})
    assert masked["portraits"] == {"_redacted": "domain", "type": "array", "size": 2}
    assert masked["avatar"] == {"_redacted": "domain", "type": "int", "size": 1}
    assert masked["profile"] == {"_redacted": "domain", "type": "NoneType", "size": 0}
