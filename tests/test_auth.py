"""JWT 与错误处理测试."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from openbase.core.errors import BaseError, ErrorCode, install_exception_handlers
from openbase.modules.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)


def test_create_and_decode_access_token():
    token = create_access_token("42", username="alice", tenant_id="t1")
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["username"] == "alice"
    assert payload["tenant_id"] == "t1"
    assert payload["type"] == "access"


def test_create_and_decode_refresh_token():
    token = create_refresh_token("42")
    payload = decode_refresh_token(token)
    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["type"] == "refresh"


def test_access_token_rejected_as_refresh():
    token = create_access_token("42")
    assert decode_refresh_token(token) is None


def test_invalid_token_returns_none():
    assert decode_access_token("not-a-jwt") is None
    assert decode_refresh_token("not-a-jwt") is None


def test_base_error_status_mapping():
    err = BaseError(ErrorCode.AUTH_UNAUTHORIZED, "unauthorized")
    assert err.status_code == 401
    err2 = BaseError(ErrorCode.PARAM_VALIDATION_ERROR, "bad param")
    assert err2.status_code == 400  # v1.4.6 Step 4 裁定：参数校验统一 400 PARAM_400
    err3 = BaseError(ErrorCode.SYS_INTERNAL_ERROR, "boom")
    assert err3.status_code == 500


def test_exception_handler_returns_unified_format():
    app = FastAPI()
    install_exception_handlers(app)

    @app.get("/err")
    async def err():
        raise BaseError(ErrorCode.AUTH_FORBIDDEN, "no permission")

    client = TestClient(app)
    resp = client.get("/err")
    assert resp.status_code == 403
    body = resp.json()
    assert body["code"] == "AUTH_403"
    assert body["message"] == "no permission"
    assert "request_id" in body
