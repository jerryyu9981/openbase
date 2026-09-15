"""日志分类派生规则（单点实现，ADR-146-02 / ADR-146-06）.

三源共用同一套 module / operation / result 派生规则，避免各适配器口径分裂。
四仓日志（repo_log）的 module 不由 path 派生，而由采集目录名（svc）显式映射得出
（API 设计文档 §4.4）：映射表为显式常量并置于本文件单点，禁止在适配器内硬编码散落。
"""

from __future__ import annotations

from openbase.modules.logs.schemas import (
    LogModule,
    LogOperation,
    LogResult,
)

# ---- repo_log 源：svc 目录名 → module 名 显式映射（API §4.4，契约三处一致）----
# 注意三个 svc 名与 module 名**非同名**（openrag→rag、openmemory→memory、openllm→llm）。
REPO_LOG_SVC_TO_MODULE: dict[str, LogModule] = {
    "dps": "dps",
    "openrag": "rag",
    "openmemory": "memory",
    "openllm": "llm",
}
REPO_LOG_MODULE_TO_SVC: dict[LogModule, str] = {
    module: svc for svc, module in REPO_LOG_SVC_TO_MODULE.items()
}
REPO_LOG_SOURCES: tuple[str, ...] = tuple(REPO_LOG_SVC_TO_MODULE.keys())

# ---- module 派生：按 path 前缀（最长匹配优先，API §4.1）----
_MODULE_PREFIX_RULES: tuple[tuple[tuple[str, ...], LogModule], ...] = (
    (("/api/v1/auth", "/api/v1/identity", "/api/v1/users", "/api/v1/tenants", "/oidc"), "identity"),
    (("/api/v1/dps-proxy",), "dps"),
    (("/api/v1/rag-proxy",), "rag"),
    (("/api/v1/memory-proxy",), "memory"),
    (("/api/v1/llm-proxy",), "llm"),
    (("/api/v1/gateway", "/api/v1/system", "/api/v1/modules", "/api/v1/logs"), "gateway"),
    (("/api/v1/test-runs", "/api/v1/test-records"), "testing"),
)


def derive_module_from_path(path: str | None) -> LogModule:
    """按 path 前缀派生 module（最长匹配优先，其余落 other）。"""
    if not path:
        return "other"
    for prefixes, module in _MODULE_PREFIX_RULES:
        for prefix in prefixes:
            if path.startswith(prefix):
                return module
    return "other"


# ---- operation 派生（API §4.2，顺序优先）----
_AUTH_LOGIN_PATH_TOKENS: tuple[str, ...] = ("/auth/login", "/oidc/")
_CONFIG_TOKENS: tuple[str, ...] = ("config", "settings", "switch")


def derive_operation(method: str | None, path: str | None, action: str | None = None) -> LogOperation:
    """从 method + path 派生 operation（条件满足即按顺序优先）。"""
    if path and ("/auth/login" in path or path.startswith("/oidc/")):
        return "auth_login"
    if method == "DELETE":
        return "delete"
    if path and any(token in path for token in _CONFIG_TOKENS):
        return "config"
    if path and "-proxy" in path:
        return "proxy"
    if method == "GET":
        return "read"
    if method in ("POST", "PUT", "PATCH"):
        return "write"
    if action:
        return _derive_operation_from_action(action)
    return "read"


def _derive_operation_from_action(action: str) -> LogOperation:
    """action 存在但无 method 时的动作语义兜底映射。"""
    if action in ("identity.purge", "module.switch"):
        return "config"
    if "delete" in action or action.endswith(".delete"):
        return "delete"
    if action in ("proxy.outbound",):
        return "proxy"
    return "read"


# ---- result 派生（API §4.3，状态码区间）----
# 测试记录源 result 字段（PASS/FAIL/BLOCKED/SKIPPED）语义映射：PASS→success，其余→client_error
TEST_RESULT_TO_RESULT: dict[str, LogResult] = {
    "PASS": "success",
    "FAIL": "client_error",
    "BLOCKED": "client_error",
    "SKIPPED": "client_error",
    "NONE": "unknown",
    "UNKNOWN": "unknown",
}


def derive_result_from_status(status_code: int | None) -> LogResult:
    """按状态码区间派生 result。"""
    if status_code is None:
        return "unknown"
    if 200 <= status_code < 300:
        return "success"
    if 400 <= status_code < 500:
        return "client_error"
    if 500 <= status_code < 600:
        return "server_error"
    return "unknown"


def derive_result_from_test(test_result: str | None) -> LogResult:
    """测试记录源直接取 result 字段（按记录语义映射）。"""
    if not test_result:
        return "unknown"
    return TEST_RESULT_TO_RESULT.get(test_result.upper(), "unknown")


def svc_dir_to_module(svc: str) -> LogModule | None:
    """四仓 svc 目录名 → module；未知 svc 返回 None（不纳入检索）。"""
    return REPO_LOG_SVC_TO_MODULE.get(svc)


def module_to_svc_dir(module: LogModule) -> str | None:
    """module → 四仓 svc 目录名；非四仓 module 返回 None。"""
    return REPO_LOG_MODULE_TO_SVC.get(module)


__all__ = [
    "REPO_LOG_SVC_TO_MODULE",
    "REPO_LOG_MODULE_TO_SVC",
    "REPO_LOG_SOURCES",
    "derive_module_from_path",
    "derive_operation",
    "derive_result_from_status",
    "derive_result_from_test",
    "svc_dir_to_module",
    "module_to_svc_dir",
]
