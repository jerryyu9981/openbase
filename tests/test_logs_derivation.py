"""日志分类派生规则单元测试（v1.4.6，锁定 API 设计文档 §4 契约表）."""

from __future__ import annotations

import pytest

from openbase.modules.logs.derivation import (
    REPO_LOG_SVC_TO_MODULE,
    derive_module_from_path,
    derive_operation,
    derive_result_from_status,
    derive_result_from_test,
    module_to_svc_dir,
    svc_dir_to_module,
)


class TestModuleDerivation:
    """API §4.1 path 前缀 → module（最长匹配优先，其余 other）。"""

    @pytest.mark.parametrize(
        ("path", "expected"),
        [
            ("/api/v1/auth/login", "identity"),
            ("/api/v1/identity/purge", "identity"),
            ("/api/v1/users/1", "identity"),
            ("/api/v1/tenants", "identity"),
            ("/oidc/authorize", "identity"),
            ("/api/v1/dps-proxy/forward", "dps"),
            ("/api/v1/rag-proxy/chat", "rag"),
            ("/api/v1/memory-proxy/search", "memory"),
            ("/api/v1/llm-proxy/completion", "llm"),
            ("/api/v1/gateway/aggregate", "gateway"),
            ("/api/v1/system/config", "gateway"),
            ("/api/v1/modules", "gateway"),
            ("/api/v1/logs/search", "gateway"),
            ("/api/v1/test-runs/run-1/summary", "testing"),
            ("/api/v1/test-records", "testing"),
        ],
    )
    def test_derive_module_from_path(self, path: str, expected: str) -> None:
        assert derive_module_from_path(path) == expected

    @pytest.mark.parametrize("path", [None, "", "/api/v1/unknown", "/something/else"])
    def test_unknown_path_to_other(self, path: str | None) -> None:
        assert derive_module_from_path(path) == "other"

    def test_longest_prefix_wins(self) -> None:
        # /logs 命中 gateway 前缀，而非最前匹配
        assert derive_module_from_path("/api/v1/logs/export") == "gateway"


class TestOperationDerivation:
    """API §4.2 operation 派生（顺序优先）。"""

    @pytest.mark.parametrize(
        ("method", "path", "expected"),
        [
            ("POST", "/api/v1/auth/login", "auth_login"),
            ("GET", "/oidc/authorize", "auth_login"),
            ("DELETE", "/api/v1/tenants/1", "delete"),
            ("GET", "/api/v1/system/config", "config"),
            ("GET", "/api/v1/modules/openllm/switch", "config"),  # path 含 switch 派生 config
            ("PATCH", "/api/v1/modules/openllm", "write"),  # 无 config/settings/switch token → method 派生
            ("GET", "/api/v1/rag-proxy/chat", "proxy"),
            ("GET", "/api/v1/users", "read"),
            ("POST", "/api/v1/users", "write"),
            ("PUT", "/api/v1/users/1", "write"),
        ],
    )
    def test_derive_operation_priority(
        self, method: str | None, path: str | None, expected: str
    ) -> None:
        assert derive_operation(method, path) == expected

    def test_config_token_includes_switch(self) -> None:
        assert derive_operation("PATCH", "/api/v1/modules/openllm/switch") == "config"

    def test_action_fallback(self) -> None:
        # 无 method/action 兜底
        assert derive_operation(None, None, "identity.purge") == "config"
        assert derive_operation(None, None, "proxy.outbound") == "proxy"
        assert derive_operation(None, None, None) == "read"

    def test_path_switch_wins_over_method(self) -> None:
        # switch token 优先于 method 判读
        assert derive_operation("GET", "/api/v1/modules/openllm/switch") == "config"


class TestResultDerivation:
    """API §4.3 状态码区间 → result。"""

    @pytest.mark.parametrize(
        ("status", "expected"),
        [
            (200, "success"),
            (201, "success"),
            (299, "success"),
            (400, "client_error"),
            (401, "client_error"),
            (499, "client_error"),
            (500, "server_error"),
            (503, "server_error"),
            (None, "unknown"),
            (100, "unknown"),
            (600, "unknown"),
        ],
    )
    def test_derive_result_from_status(self, status: int | None, expected: str) -> None:
        assert derive_result_from_status(status) == expected

    @pytest.mark.parametrize(
        ("test_result", "expected"),
        [
            ("PASS", "success"),
            ("pass", "success"),
            ("FAIL", "client_error"),
            ("BLOCKED", "client_error"),
            ("SKIPPED", "client_error"),
            (None, "unknown"),
            ("UNKNOWN", "unknown"),
        ],
    )
    def test_derive_result_from_test(self, test_result: str | None, expected: str) -> None:
        assert derive_result_from_test(test_result) == expected


class TestRepoLogSvcModuleMap:
    """API §4.4 svc 目录名 ↔ module 显式映射（含非同名 mapping）。"""

    def test_svc_to_module_mapping(self) -> None:
        assert REPO_LOG_SVC_TO_MODULE == {
            "dps": "dps",
            "openrag": "rag",
            "openmemory": "memory",
            "openllm": "llm",
        }

    def test_svc_dir_to_module(self) -> None:
        assert svc_dir_to_module("dps") == "dps"
        assert svc_dir_to_module("openrag") == "rag"
        assert svc_dir_to_module("openmemory") == "memory"
        assert svc_dir_to_module("openllm") == "llm"

    def test_unknown_svc_returns_none(self) -> None:
        assert svc_dir_to_module("unknown") is None

    def test_module_to_svc_dir_roundtrip(self) -> None:
        assert module_to_svc_dir("dps") == "dps"
        assert module_to_svc_dir("rag") == "openrag"
        assert module_to_svc_dir("memory") == "openmemory"
        assert module_to_svc_dir("llm") == "openllm"
        assert module_to_svc_dir("identity") is None

    def test_non_homonymous_mapping_flag(self) -> None:
        # openrag→rag 非同名，契约要求显式登记
        assert module_to_svc_dir("rag") != "rag"
        assert module_to_svc_dir("memory") != "memory"
        assert module_to_svc_dir("llm") != "llm"
