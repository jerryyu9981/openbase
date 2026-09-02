"""OpenBase 本地 OIDC IdP（标准授权码流程，开发/联调用）.

标准端点：discovery / jwks / authorize（真实登录页）/ token / userinfo
协议：OIDC Authorization Code Flow + PKCE 可选；ID Token RS256（JWKS 公钥验证）

演示用户（明文密码仅限本地开发）：
    oidc-admin / oidc-pass-2026   roles=[org_admin]  tenant_id=default
    oidc-user  / user-pass-2026   roles=[user]       tenant_id=default

内置 client：
    client_id=openbase-gw
    client_secret=openbase-oidc-secret-20260902
    redirect_uri=http://127.0.0.1:8000/api/v1/auth/oidc/callback

用法：python idp_server.py   （监听 0.0.0.0:8090）
"""

from __future__ import annotations

import html
import json
import logging
import os
import secrets
import time
import urllib.parse
from typing import Any

from authlib.jose import JsonWebKey, JsonWebSignature
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("openbase.oidc-idp")

# ---- 配置 ----
HOST = os.environ.get("OIDC_IDP_HOST", "127.0.0.1")
PORT = int(os.environ.get("OIDC_IDP_PORT", "8090"))
ISSUER = os.environ.get("OIDC_IDP_ISSUER", f"http://{HOST}:{PORT}")

CLIENT_ID = os.environ.get("OIDC_IDP_CLIENT_ID", "openbase-gw")
CLIENT_SECRET = os.environ.get("OIDC_IDP_CLIENT_SECRET", "openbase-oidc-secret-20260902")
REDIRECT_URIS = [
    u.strip()
    for u in os.environ.get(
        "OIDC_IDP_REDIRECT_URIS",
        "http://127.0.0.1:8000/api/v1/auth/oidc/callback",
    ).split(",")
    if u.strip()
]

# 演示用户池（本地开发用途）
USERS: dict[str, dict[str, Any]] = {
    "oidc-admin": {
        "password": "oidc-pass-2026",
        "sub": "oidc-sub-admin-001",
        "preferred_username": "oidc-admin",
        "email": "oidc-admin@openbase.local",
        "roles": ["org_admin"],
        "tenant_id": "default",
    },
    "oidc-user": {
        "password": "user-pass-2026",
        "sub": "oidc-sub-user-001",
        "preferred_username": "oidc-user",
        "email": "oidc-user@openbase.local",
        "roles": ["user"],
        "tenant_id": "default",
    },
}

_KEY_FILE = os.environ.get(
    "OIDC_IDP_KEY_FILE",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "keys", "idp-rsa.json"),
)


def _load_or_create_keys() -> tuple[str, Any]:
    """加载或生成 RSA 密钥对（JWK 私有格式，含 kid）。"""
    if os.path.isfile(_KEY_FILE):
        with open(_KEY_FILE, encoding="utf-8") as f:
            priv = json.load(f)
        return priv["kid"], priv
    kid = "openbase-idp-rsa-1"
    key = JsonWebKey.generate_key("RSA", 2048, is_private=True)
    priv = key.as_dict(is_private=True)
    priv["kid"] = kid
    priv["alg"] = "RS256"
    priv["use"] = "sig"
    os.makedirs(os.path.dirname(_KEY_FILE), exist_ok=True)
    with open(_KEY_FILE, "w", encoding="utf-8") as f:
        json.dump({"kid": kid, **priv}, f)
    logger.info("generated new RSA key kid=%s file=%s", kid, _KEY_FILE)
    return kid, priv


KID, _PRIV_JWK = _load_or_create_keys()
_PUB_JWK = {k: v for k, v in _PRIV_JWK.items() if k != "d" and not k.startswith("oth")}


def _sign_jws(payload: dict[str, Any]) -> str:
    """RS256 签名 compact JWS（ID Token）。"""
    jws = JsonWebSignature()
    body = json.dumps(payload, separators=(",", ":")).encode()
    return jws.serialize_compact(
        {"alg": "RS256", "kid": KID, "typ": "JWT"}, body, _PRIV_JWK
    ).decode()


# ---- 运行时状态（单进程内存；多实例需共享存储） ----
_auth_codes: dict[str, dict[str, Any]] = {}  # code -> {client_id,redirect_uri,sub,scope,exp}
_sessions: dict[str, str] = {}  # sid -> username
_access_tokens: dict[str, dict[str, Any]] = {}  # token -> {sub, exp}

app = FastAPI(title="openbase-oidc-idp", docs_url=None, redoc_url=None)

AUTH_CODE_TTL = 300  # 5 分钟
ACCESS_TTL = 3600
SCOPE_MAP = {
    "openid": {"preferred_username", "sub"},
    "profile": {"preferred_username", "email", "roles", "tenant_id"},
    "email": {"email"},
}


def _user_claims(username: str, scope: str) -> dict[str, Any]:
    user = USERS[username]
    allowed: set[str] = set()
    for s in scope.split():
        allowed |= SCOPE_MAP.get(s, set())
    claims: dict[str, Any] = {}
    for claim in allowed:
        if claim == "preferred_username":
            claims[claim] = user["preferred_username"]
        elif claim in user:
            claims[claim] = user[claim]
    if "sub" in allowed or "openid" in scope:
        claims["sub"] = user["sub"]
    return claims


def _client_ok(client_id: str, secret: str = "") -> bool:
    return client_id == CLIENT_ID and (not CLIENT_SECRET or secret == CLIENT_SECRET)


# ---- 端点 ----

@app.get("/.well-known/openid-configuration")
async def discovery() -> dict:
    return {
        "issuer": ISSUER,
        "authorization_endpoint": f"{ISSUER}/authorize",
        "token_endpoint": f"{ISSUER}/token",
        "userinfo_endpoint": f"{ISSUER}/userinfo",
        "jwks_uri": f"{ISSUER}/jwks",
        "response_types_supported": ["code"],
        "response_modes_supported": ["query"],
        "grant_types_supported": ["authorization_code"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["RS256"],
        "token_endpoint_auth_methods_supported": ["client_secret_post"],
        "scopes_supported": ["openid", "profile", "email"],
        "claims_supported": ["sub", "preferred_username", "email", "roles", "tenant_id"],
    }


@app.get("/jwks")
async def jwks() -> dict:
    return {"keys": [_PUB_JWK]}


@app.get("/authorize")
async def authorize(
    client_id: str,
    redirect_uri: str,
    response_type: str,
    scope: str = "openid",
    state: str = "",
    request: Request = None,
) -> Response:
    """授权端点：无登录态返回登录页；已登录签发 code 302 回 redirect_uri。"""
    if client_id != CLIENT_ID:
        return HTMLResponse("<h3>400 unknown client_id</h3>", status_code=400)
    if redirect_uri not in REDIRECT_URIS:
        return HTMLResponse("<h3>400 invalid redirect_uri</h3>", status_code=400)
    if response_type != "code":
        return HTMLResponse("<h3>400 unsupported response_type</h3>", status_code=400)

    sid = request.cookies.get("idp_sid") if request else None
    username = _sessions.get(sid) if sid else None
    if username is None:
        # 登录页（GET 表单，保留原参数）
        params = urllib.parse.urlencode({
            "client_id": client_id, "redirect_uri": redirect_uri,
            "response_type": response_type, "scope": scope, "state": state,
        })
        page = f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>OpenBase 本地 IdP 登录</title></head><body style="font-family:sans-serif">
<h2>OpenBase 本地 OIDC IdP 登录</h2>
<form method="post" action="/login?{html.escape(params)}">
  <p><label>用户名 <input name="username" value="oidc-admin"></label></p>
  <p><label>密码 <input name="password" type="password" value="oidc-pass-2026"></label></p>
  <p><button type="submit">登录并授权</button></p>
  <p style="color:#888">演示账号：oidc-admin / oidc-pass-2026 · oidc-user / user-pass-2026</p>
</form></body></html>"""
        return HTMLResponse(page)

    user = USERS[username]
    code = secrets.token_urlsafe(24)
    _auth_codes[code] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "sub": user["sub"],
        "scope": scope,
        "exp": time.time() + AUTH_CODE_TTL,
    }
    location = f"{redirect_uri}?{urllib.parse.urlencode({'code': code, 'state': state})}"
    logger.info("authorize ok user=%s code_len=%d", username, len(code))
    return RedirectResponse(location, status_code=302)


@app.post("/login")
async def login(request: Request) -> Response:
    """登录表单提交：校验用户 → 建会话 → 302 回 authorize 原参数。"""
    form = await request.form()
    username = (form.get("username") or "").strip()
    password = form.get("password") or ""
    user = USERS.get(username)
    if user is None or user["password"] != password:
        return HTMLResponse("<h3>401 invalid credentials</h3>", status_code=401)
    sid = secrets.token_hex(16)
    _sessions[sid] = username
    target = request.url.path  # /login 本身；原 authorize 参数在 query
    query = request.url.query or ""
    resp = RedirectResponse(f"/authorize?{query}" if query else "/authorize", status_code=302)
    resp.set_cookie("idp_sid", sid, max_age=1800, httponly=True)
    logger.info("login ok user=%s", username)
    return resp


class TokenForm(BaseModel):
    grant_type: str
    code: str | None = None
    redirect_uri: str | None = None
    client_id: str | None = None
    client_secret: str | None = None


@app.post("/token")
async def token(request: Request) -> Response:
    """token 端点：授权码换 access_token + id_token（RS256）。"""
    form = await request.form()
    grant_type = form.get("grant_type")
    client_id = form.get("client_id")
    client_secret = form.get("client_secret")
    if grant_type != "authorization_code":
        return Response('{"error":"unsupported_grant_type"}', media_type="application/json", status_code=400)
    if not _client_ok(client_id or "", client_secret or ""):
        return Response('{"error":"invalid_client"}', media_type="application/json", status_code=401)

    code = form.get("code")
    rec = _auth_codes.pop(code, None) if code else None
    if rec is None or rec["exp"] < time.time():
        return Response('{"error":"invalid_grant"}', media_type="application/json", status_code=400)
    if rec["client_id"] != client_id:
        return Response('{"error":"invalid_grant"}', media_type="application/json", status_code=400)
    if form.get("redirect_uri") != rec["redirect_uri"]:
        return Response('{"error":"invalid_grant"}', media_type="application/json", status_code=400)

    username = next((u for u, d in USERS.items() if d["sub"] == rec["sub"]), None)
    if username is None:
        return Response('{"error":"invalid_grant"}', media_type="application/json", status_code=400)

    claims = _user_claims(username, rec["scope"])
    now = int(time.time())
    id_token_payload = {
        "iss": ISSUER,
        "sub": rec["sub"],
        "aud": CLIENT_ID,
        "exp": now + ACCESS_TTL,
        "iat": now,
        "auth_time": now,
        "nonce": None,
        **claims,
    }
    id_token = _sign_jws(id_token_payload)
    access = secrets.token_urlsafe(32)
    _access_tokens[access] = {"sub": rec["sub"], "exp": time.time() + ACCESS_TTL}
    body = {
        "access_token": access,
        "token_type": "Bearer",
        "expires_in": ACCESS_TTL,
        "id_token": id_token,
    }
    logger.info("token ok sub=%s", rec["sub"])
    return Response(json.dumps(body), media_type="application/json")


@app.get("/userinfo")
async def userinfo(request: Request) -> Response:
    auth = request.headers.get("Authorization", "")
    token = auth.removeprefix("Bearer ").strip()
    rec = _access_tokens.get(token)
    if rec is None or rec["exp"] < time.time():
        return Response('{"error":"invalid_token"}', media_type="application/json", status_code=401)
    username = next((u for u, d in USERS.items() if d["sub"] == rec["sub"]), None)
    user = USERS.get(username or "")
    if user is None:
        return Response('{"error":"invalid_token"}', media_type="application/json", status_code=401)
    return Response(json.dumps({
        "sub": user["sub"],
        "preferred_username": user["preferred_username"],
        "email": user["email"],
        "roles": user["roles"],
        "tenant_id": user["tenant_id"],
    }), media_type="application/json")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "issuer": ISSUER}


if __name__ == "__main__":
    import uvicorn

    logger.info("OpenBase local OIDC IdP starting issuer=%s port=%d", ISSUER, PORT)
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
