"""Keycloak openbase realm 配置脚本（Admin REST API，幂等，OB-AUTH-OIDC v1.5.0）.

创建/对齐：
  - realm: openbase
  - realm roles: org_admin / user / viewer（对齐 OpenBase 角色白名单）
  - client: openbase-gw（confidential，授权码流程；redirect 指向 OpenBase 8000）
  - client 级租户 mapper：用户属性 tenant_id → token claim（id/access/userinfo）
  - 演示用户: oidc-admin/oidc-pass-2026 -> org_admin；oidc-user/user-pass-2026 -> user

角色默认仅进 access token（Keycloak 官方默认 mapper 行为），用于真实验证
OpenBase oidc_profile=keycloak 的 access token 角色兜底路径。

用法: python scripts/keycloak/provision_realm.py
"""
from __future__ import annotations

import sys
import time

import requests

BASE = "http://127.0.0.1:8080"
ADMIN_USER = "admin"
ADMIN_PASS = "admin"
REALM = "openbase"
CLIENT_ID = "openbase-gw"
CLIENT_SECRET = "openbase-kc-secret-20260902"
REDIRECT_URI = "http://127.0.0.1:8000/api/v1/auth/oidc/callback"
ROLES = ["org_admin", "user", "viewer"]
USERS = [
    {
        "username": "oidc-admin",
        "password": "oidc-pass-2026",
        "email": "oidc-admin@openbase.local",
        "first_name": "OIDC",
        "last_name": "Admin",
        "roles": ["org_admin"],
        "tenant_id": "default",
    },
    {
        "username": "oidc-user",
        "password": "user-pass-2026",
        "email": "oidc-user@openbase.local",
        "first_name": "OIDC",
        "last_name": "User",
        "roles": ["user"],
        "tenant_id": "default",
    },
]
TIMEOUT = 20


def api(token: str, method: str, path: str, **kwargs):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    resp = requests.request(method, f"{BASE}{path}", headers=headers, timeout=TIMEOUT, **kwargs)
    return resp


def get_admin_token() -> str:
    resp = requests.post(
        f"{BASE}/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": ADMIN_USER,
            "password": ADMIN_PASS,
        },
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def ensure_realm(token: str) -> None:
    resp = api(token, "GET", f"/admin/realms/{REALM}")
    if resp.status_code == 200:
        print(f"[skip] realm {REALM} exists")
        return
    body = {
        "realm": REALM,
        "enabled": True,
        "displayName": "OpenBase 集成联调",
        "sslRequired": "external",
    }
    resp = api(token, "POST", "/admin/realms", json=body)
    resp.raise_for_status()
    print(f"[ok] realm {REALM} created")


def ensure_roles(token: str) -> dict[str, str]:
    """确保 realm roles 存在，返回 {code: id}. """
    resp = api(token, "GET", f"/admin/realms/{REALM}/roles")
    resp.raise_for_status()
    existing = {r["name"]: r["id"] for r in resp.json()}
    for code in ROLES:
        if code in existing:
            print(f"[skip] role {code}")
            continue
        r = api(token, "POST", f"/admin/realms/{REALM}/roles", json={"name": code})
        r.raise_for_status()
        print(f"[ok] role {code} created")
        existing[code] = r.headers.get("Location", "").rsplit("/", 1)[-1]
    return existing


def ensure_client(token: str) -> str:
    """确保 client 存在，返回 client id（内部 uuid）. """
    resp = api(token, "GET", f"/admin/realms/{REALM}/clients?clientId={CLIENT_ID}")
    resp.raise_for_status()
    found = resp.json()
    if found:
        cid = found[0]["id"]
        print(f"[skip] client {CLIENT_ID} ({cid})")
        return cid
    body = {
        "clientId": CLIENT_ID,
        "enabled": True,
        "protocol": "openid-connect",
        "publicClient": False,
        "secret": CLIENT_SECRET,
        "standardFlowEnabled": True,
        "directAccessGrantsEnabled": False,
        "redirectUris": [REDIRECT_URI],
        "webOrigins": [],
        "attributes": {"post.logout.redirect.uris": REDIRECT_URI},
    }
    resp = api(token, "POST", f"/admin/realms/{REALM}/clients", json=body)
    resp.raise_for_status()
    cid = resp.headers["Location"].rsplit("/", 1)[-1]
    print(f"[ok] client {CLIENT_ID} created ({cid})")
    return cid


def ensure_tenant_mapper(token: str, cid: str) -> None:
    """client 级租户 mapper：用户属性 tenant_id → token claim tenant_id. """
    resp = api(token, "GET", f"/admin/realms/{REALM}/clients/{cid}/protocol-mappers/models")
    resp.raise_for_status()
    for m in resp.json():
        if m.get("name") == "openbase-tenant-id":
            print("[skip] tenant mapper openbase-tenant-id")
            return
    body = {
        "name": "openbase-tenant-id",
        "protocol": "openid-connect",
        "protocolMapper": "oidc-usermodel-attribute-mapper",
        "config": {
            "user.attribute": "tenant_id",
            "claim.name": "tenant_id",
            "jsonType.label": "String",
            "id.token.claim": "true",
            "access.token.claim": "true",
            "userinfo.token.claim": "true",
        },
    }
    resp = api(token, "POST", f"/admin/realms/{REALM}/clients/{cid}/protocol-mappers/models", json=body)
    resp.raise_for_status()
    print("[ok] tenant mapper openbase-tenant-id created")


def ensure_audience_mapper(token: str, cid: str) -> None:
    """client 级 audience mapper：access token aud 包含本 client（默认 aud 仅 account）. """
    resp = api(token, "GET", f"/admin/realms/{REALM}/clients/{cid}/protocol-mappers/models")
    resp.raise_for_status()
    for m in resp.json():
        if m.get("name") == "openbase-audience":
            print("[skip] audience mapper openbase-audience")
            return
    body = {
        "name": "openbase-audience",
        "protocol": "openid-connect",
        "protocolMapper": "oidc-audience-mapper",
        "config": {
            "included.client.audience": CLIENT_ID,
            "id.token.claim": "false",
            "access.token.claim": "true",
        },
    }
    resp = api(token, "POST", f"/admin/realms/{REALM}/clients/{cid}/protocol-mappers/models", json=body)
    resp.raise_for_status()
    print("[ok] audience mapper openbase-audience created")


def ensure_users(token: str, role_ids: dict[str, str]) -> None:
    for spec in USERS:
        username = spec["username"]
        resp = api(token, "GET", f"/admin/realms/{REALM}/users?username={username}&exact=true")
        resp.raise_for_status()
        found = resp.json()
        if found:
            uid = found[0]["id"]
            print(f"[skip] user {username} ({uid})")
        else:
            body = {
                "username": username,
                "enabled": True,
                "email": spec["email"],
                "emailVerified": True,
                "firstName": spec["first_name"],
                "lastName": spec["last_name"],
                "requiredActions": [],  # 避免首次登录 VERIFY_PROFILE 打断授权码流程
                "attributes": {"tenant_id": [spec["tenant_id"]]},
                "credentials": [
                    {
                        "type": "password",
                        "value": spec["password"],
                        "temporary": False,
                    }
                ],
            }
            resp = api(token, "POST", f"/admin/realms/{REALM}/users", json=body)
            resp.raise_for_status()
            uid = resp.headers["Location"].rsplit("/", 1)[-1]
            print(f"[ok] user {username} created ({uid})")
            # 容忍创建后即时一致性（首次角色绑定偶发 404）
            time.sleep(0.8)
        # 补齐用户资料（幂等）：Keycloak PUT 为全量替换，须带全字段（email/enabled 等）
        cur = api(token, "GET", f"/admin/realms/{REALM}/users/{uid}")
        cur.raise_for_status()
        u = cur.json()
        attrs = dict(u.get("attributes") or {})
        attrs["tenant_id"] = [spec["tenant_id"]]
        patch = {
            "username": u.get("username", username),
            "email": u.get("email") or spec["email"],
            "emailVerified": True,
            "enabled": True,
            "firstName": u.get("firstName") or spec["first_name"],
            "lastName": u.get("lastName") or spec["last_name"],
            "requiredActions": [],
            "attributes": attrs,
        }
        upd = api(token, "PUT", f"/admin/realms/{REALM}/users/{uid}", json=patch)
        upd.raise_for_status()
        print(f"[ok] user {username} profile ensured (full fields + attrs + no required actions)")
        # realm role 绑定（幂等：查询现有）
        rm = api(token, "GET", f"/admin/realms/{REALM}/users/{uid}/role-mappings/realm")
        rm.raise_for_status()
        have = {r["name"] for r in rm.json()}
        need = [r for r in spec["roles"] if r not in have]
        if need:
            payload = [
                {"id": role_ids[r], "name": r} for r in need if r in role_ids
            ]
            if payload:
                r = api(
                    token,
                    "POST",
                    f"/admin/realms/{REALM}/users/{uid}/role-mappings/realm",
                    json=payload,
                )
                r.raise_for_status()
            print(f"[ok] user {username} roles += {need}")
        else:
            print(f"[skip] user {username} roles already set")


def main() -> None:
    token = get_admin_token()
    print("admin token ok")
    ensure_realm(token)
    role_ids = ensure_roles(token)
    cid = ensure_client(token)
    ensure_tenant_mapper(token, cid)
    ensure_audience_mapper(token, cid)
    ensure_users(token, role_ids)
    print("\n=== 配置完成 ===")
    print(f"issuer:     {BASE}/realms/{REALM}")
    print(f"discovery:  {BASE}/realms/{REALM}/.well-known/openid-configuration")
    print(f"client:     {CLIENT_ID} (secret: {CLIENT_SECRET})")
    print(f"redirect:   {REDIRECT_URI}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"PROVISION FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
