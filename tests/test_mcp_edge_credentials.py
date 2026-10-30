"""E1-6 MCP 边缘凭证与工具级 ``scope.tools`` 过滤测试."""

import hashlib
import logging
import os
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openbase.core.errors import BaseError, ErrorCode, install_exception_handlers


def _build_client() -> TestClient:
    """构建挂载 MCP 路由的最小应用（保留统一错误契约）."""
    from openbase.modules.mcp import router

    app = FastAPI()
    install_exception_handlers(app)
    app.include_router(router)
    return TestClient(app)


def _register(tool_name: str) -> None:
    """注册只读回显工具（幂等，避免跨用例重复注册报错）."""
    from openbase.modules.mcp import get_mcp_server

    get_mcp_server().register_tool(
        {"name": tool_name, "description": "测试工具", "func": lambda **_: "ok"}
    )


def test_service_key_scope_tools_filters_list_and_call(monkeypatch):
    """服务 Key 的 scope.tools 同时约束 tools/list 与 tools/call."""
    from openbase.modules.mcp import credentials

    _register("tool_a")
    _register("tool_b")
    _register("tool_c")

    async def _fake_lookup(raw_key: str):
        assert raw_key == "ob_k_test"
        return {
            "id": "key-1",
            "name": "edge-key",
            "scope": {"system": ["mcp"], "tools": ["tool_a"]},
            "tenant_code": "tenant-1",
            "last_used_at": 0.0,
        }

    monkeypatch.setattr(credentials, "_lookup_service_key", _fake_lookup)
    client = _build_client()
    headers = {"X-API-Key": "ob_k_test"}

    listing = client.get("/mcp/tools/list", headers=headers)
    assert listing.status_code == 200
    names = [tool["name"] for tool in listing.json()["tools"]]
    assert "tool_a" in names
    assert "tool_b" not in names

    allowed = client.post("/mcp/tools/call", json={"name": "tool_a", "arguments": {}} , headers=headers)
    assert allowed.status_code == 200

    denied = client.post("/mcp/tools/call", json={"name": "tool_b", "arguments": {}}, headers=headers)
    assert denied.status_code == 403
    assert denied.json()["code"] == ErrorCode.PERM_API_KEY_SCOPE.value


def test_service_key_requires_mcp_system_scope(monkeypatch):
    """服务 Key 的 scope.system 不含 mcp → 403（不得打通全部系统）."""
    from openbase.modules.mcp import credentials

    async def _fake_lookup(raw_key: str):
        return {"id": "key-2", "name": "llm-key", "scope": {"system": ["llm"]}}

    monkeypatch.setattr(credentials, "_lookup_service_key", _fake_lookup)
    client = _build_client()
    resp = client.get("/mcp/tools/list", headers={"X-API-Key": "ob_k_other"})
    assert resp.status_code == 403
    assert resp.json()["code"] == ErrorCode.PERM_API_KEY_SCOPE.value


def test_jwt_bearer_scope_tools_applies():
    """短期 JWT（Bearer）按 claims scope.tools 过滤，且缺省不限定."""
    from openbase.modules.auth.jwt import create_access_token

    _register("tool_jwt_allowed")
    _register("tool_jwt_denied")
    token = create_access_token(
        "42", username="edge", extra={"scope": {"tools": ["tool_jwt_allowed"]}}
    )

    async def _fake_lookup(raw_key: str):  # 不应被调用（密码分支不应走服务 Key）
        raise AssertionError("service key lookup must not run for JWT")

    import openbase.modules.mcp.credentials as module

    original = module._lookup_service_key
    module._lookup_service_key = _fake_lookup  # type: ignore[assignment]
    try:
        client = _build_client()
        headers = {"Authorization": f"Bearer {token}"}
        names = [t["name"] for t in client.get("/mcp/tools/list", headers=headers).json()["tools"]]
        assert "tool_jwt_allowed" in names
        assert "tool_jwt_denied" not in names
        denied = client.post(
            "/mcp/tools/call", json={"name": "tool_jwt_denied", "arguments": {}}, headers=headers
        )
        assert denied.status_code == 403
    finally:
        module._lookup_service_key = original


def test_stdio_credential_requires_injected_token(monkeypatch, tmp_path):
    """stdio 无宿主令牌 → 拒绝；文件注入合法 access token → 通过."""
    from openbase.modules.auth.jwt import create_access_token, create_refresh_token
    from openbase.modules.mcp.credentials import resolve_stdio_credential

    monkeypatch.delenv("OPENBASE_MCP_TOKEN", raising=False)
    monkeypatch.delenv("OPENBASE_MCP_TOKEN_FILE", raising=False)
    with pytest.raises(BaseError) as exc_info:
        resolve_stdio_credential()
    assert exc_info.value.code == ErrorCode.AUTH_UNAUTHORIZED

    token_file = tmp_path / "mcp.token"
    token_file.write_text(create_access_token("7", extra={"scope": {"tools": ["x"]}}), encoding="utf-8")
    monkeypatch.setenv("OPENBASE_MCP_TOKEN_FILE", str(token_file))
    credential = resolve_stdio_credential()
    assert credential.credential_type == "stdio-token"
    assert credential.tools == ("x",)

    token_file.write_text(create_refresh_token("7"), encoding="utf-8")
    with pytest.raises(BaseError):
        resolve_stdio_credential()


def test_production_rejects_default_mcp_key():
    """生产环境沿用内置 dev-mcp-key → 拒绝启动（fail-closed）."""
    from openbase.settings import Settings

    settings = Settings(env="development")
    settings.env = "production"
    settings.mcp_api_keys = "dev-mcp-key"
    with pytest.raises(ValueError, match="dev-mcp-key"):
        settings._validate_mcp_edge_configuration()


def test_anomaly_settings_validation_rejects_negative():
    """异常检测阈值非法 → 拒绝启动."""
    from openbase.settings import Settings

    settings = Settings(env="development")
    settings.key_anomaly_window_seconds = 0
    with pytest.raises(ValueError, match="WINDOW_SECONDS"):
        settings._validate_mcp_edge_configuration()


def test_static_key_sha256_hash_allows_and_rejects_unknown(monkeypatch):
    """R16/R20：摘要命中 → 200；错误 Key → 401（摘要比较分支生效）."""
    from openbase.settings import get_settings

    secret = "edge-static-secret"
    settings = get_settings()
    monkeypatch.setattr(settings, "mcp_api_keys", "")
    monkeypatch.setattr(settings, "mcp_api_keys_file", "")
    monkeypatch.setattr(
        settings, "mcp_api_key_hashes", hashlib.sha256(secret.encode()).hexdigest()
    )
    client = _build_client()

    allowed = client.get("/mcp/tools/list", headers={"X-API-Key": secret})
    assert allowed.status_code == 200

    denied = client.get("/mcp/tools/list", headers={"X-API-Key": "edge-static-wrong"})
    assert denied.status_code == 401
    assert denied.json()["code"] == ErrorCode.AUTH_UNAUTHORIZED.value


def test_static_key_file_injection_allows_and_reloads(monkeypatch, tmp_path):
    """R16/R20：宿主注入 Key 文件命中通过；mtime 变化后重载新 Key."""
    from openbase.settings import get_settings

    key_file = tmp_path / "mcp.keys"
    key_file.write_text("# rotation-before\n\nfile-secret\n", encoding="utf-8")
    settings = get_settings()
    monkeypatch.setattr(settings, "mcp_api_keys", "")
    monkeypatch.setattr(settings, "mcp_api_key_hashes", "")
    monkeypatch.setattr(settings, "mcp_api_keys_file", str(key_file))
    client = _build_client()

    assert client.get("/mcp/tools/list", headers={"X-API-Key": "file-secret"}).status_code == 200
    # 注释行不得被当成 Key
    assert client.get("/mcp/tools/list", headers={"X-API-Key": "# rotation-before"}).status_code == 401

    key_file.write_text("rotated-secret\n", encoding="utf-8")
    future = time.time() + 5
    os.utime(key_file, (future, future))
    assert client.get(
        "/mcp/tools/list", headers={"X-API-Key": "rotated-secret"}
    ).status_code == 200
    assert client.get("/mcp/tools/list", headers={"X-API-Key": "file-secret"}).status_code == 401


def test_static_key_file_unreadable_warns_and_denies(monkeypatch, tmp_path, caplog):
    """R16/R20：Key 文件不可读 → WARNING + 视为空集合（401，不抛 500）."""
    from openbase.settings import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "mcp_api_keys", "")
    monkeypatch.setattr(settings, "mcp_api_key_hashes", "")
    monkeypatch.setattr(settings, "mcp_api_keys_file", str(tmp_path / "missing.keys"))
    client = _build_client()

    with caplog.at_level(logging.WARNING, logger="openbase.modules.mcp.credentials"):
        resp = client.get("/mcp/tools/list", headers={"X-API-Key": "any-key"})
    assert resp.status_code == 401
    assert any("keys file" in record.message for record in caplog.records)


def test_production_rejects_plaintext_static_key():
    """R16/R20：生产即使非默认值也禁止任何明文静态 Key."""
    from openbase.settings import Settings

    settings = Settings(env="development")
    settings.env = "production"
    settings.mcp_api_keys = "prod-static-key"
    settings.mcp_api_key_hashes = hashlib.sha256(b"prod-static-key").hexdigest()
    with pytest.raises(ValueError, match="明文"):
        settings._validate_mcp_edge_configuration()


def test_production_requires_hash_or_key_file():
    """R16/R20：生产缺摘要与密钥文件 → 拒绝启动；配置其一即通过."""
    from openbase.settings import Settings

    settings = Settings(env="development")
    settings.env = "production"
    settings.mcp_api_keys = ""
    settings.mcp_api_key_hashes = ""
    settings.mcp_api_keys_file = ""
    with pytest.raises(ValueError, match="OPENBASE_MCP_API_KEY_HASHES"):
        settings._validate_mcp_edge_configuration()

    settings.mcp_api_key_hashes = hashlib.sha256(b"prod-key").hexdigest()
    assert settings._validate_mcp_edge_configuration() is settings

    settings.mcp_api_key_hashes = ""
    settings.mcp_api_keys_file = "/run/secrets/mcp.keys"
    assert settings._validate_mcp_edge_configuration() is settings


def test_production_rejects_malformed_hash():
    """R16/R20：摘要非 64 位小写十六进制 → 拒绝启动."""
    from openbase.settings import Settings

    settings = Settings(env="development")
    settings.env = "production"
    settings.mcp_api_keys = ""
    settings.mcp_api_key_hashes = "deadbeef"
    settings.mcp_api_keys_file = "/run/secrets/mcp.keys"
    with pytest.raises(ValueError, match="64 位小写十六进制"):
        settings._validate_mcp_edge_configuration()
