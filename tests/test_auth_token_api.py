"""E1-5A 令牌服务面 API 测试（JWKS 公开 / 内省 / 吊销增量）."""

import asyncio
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from openbase import init_app
from openbase.core.db.session import get_engine, init_db
from openbase.core.models import Base
from openbase.modules.auth import UserService
from openbase.settings import Settings

_DB_PATH = Path(tempfile.gettempdir()) / "openbase_test_auth_token_api.db"
_KEY_DIR = Path(tempfile.mkdtemp(prefix="openbase-token-api-key-"))
_PRIVATE_PATH = _KEY_DIR / "private.pem"
_KID = "ob-test-kid"


def _write_private_key() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    _PRIVATE_PATH.write_bytes(
        private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )


def build_test_app() -> TestClient:
    """构造启用 auth 模块 + RS256 的测试应用（SQLite，不依赖外部 PG）."""
    _write_private_key()
    settings = Settings(
        jwt_rsa_private_key_path=str(_PRIVATE_PATH),
        jwt_signing_kid=_KID,
    )
    settings.enable_module("auth")
    UserService.seed_memory_user("admin", "admin123")

    Base.metadata.schema = None
    for table in Base.metadata.tables.values():
        table.schema = None
    if _DB_PATH.exists():
        _DB_PATH.unlink()
    init_db(f"sqlite+aiosqlite:///{_DB_PATH}", schema=None)

    async def _create_schema() -> None:
        async with get_engine().begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(_create_schema())
    # jwt 运行期经 get_settings() 取配置，须同步注入同一实例
    sys.modules["openbase.settings"]._settings = settings
    return TestClient(init_app(settings))


client: TestClient | None = None


@pytest.fixture(scope="module", autouse=True)
def _token_api_app() -> TestClient:
    global client
    previous = sys.modules["openbase.settings"]._settings
    client = build_test_app()
    yield client
    sys.modules["openbase.settings"]._settings = previous
    client = None


def _login_token() -> str:
    response = client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "admin123"}
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _service_key() -> str:
    """经 HTTP 签发服务 Key（默认 scope 含 system=*），返回明文."""
    response = client.post(
        "/api/v1/auth/api-keys",
        json={"name": f"introspect-{uuid4().hex[:6]}"},
        headers={"Authorization": f"Bearer {_login_token()}"},
    )
    assert response.status_code == 200, response.text
    return response.json()["key"]


async def _seed_active_user() -> int:
    """落库一个 active 主体（内存种子用户无 DB 行，无法覆盖「已核验」分支）."""
    from openbase.core.db.session import get_session_factory
    from openbase.core.models import User

    factory = get_session_factory()
    async with factory() as session:
        user = User(
            username=f"rs256-probe-{uuid4().hex[:6]}",
            password_hash="not-a-real-hash",
            display_name="RS256 Probe",
            status_state="active",
            token_version=2,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user.id


def test_jwks_is_public_and_exposes_rs256_key() -> None:
    """JWKS 无需认证；返回当前签发 kid 的公钥."""
    response = client.get("/.well-known/jwks.json")
    assert response.status_code == 200, response.text
    document = response.json()
    assert [entry["kid"] for entry in document["keys"]] == [_KID]
    entry = document["keys"][0]
    assert entry["alg"] == "RS256" and entry["use"] == "sig"
    assert "d" not in entry


def test_introspect_requires_service_key() -> None:
    response = client.post("/api/v1/auth/introspect", json={"token": "x"})
    assert response.status_code == 401


def test_introspect_reports_active_token() -> None:
    response = client.post(
        "/api/v1/auth/introspect",
        json={"token": _login_token(), "token_type_hint": "access_token"},
        headers={"X-API-Key": _service_key()},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["active"] is True
    assert body["sub"]
    assert body["type"] == "access"


def test_introspect_verifies_principal_state_and_token_version() -> None:
    """落库主体：内省回显 active 状态与 token 版本（下游缓存依据）."""
    from openbase.modules.auth.jwt import create_access_token

    subject = asyncio.run(_seed_active_user())
    response = client.post(
        "/api/v1/auth/introspect",
        json={"token": create_access_token(str(subject), token_version=2)},
        headers={"X-API-Key": _service_key()},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["active"] is True
    assert body["principal_verified"] is True
    assert body["subject_status"] == "active"
    assert body["token_version"] == 2


def test_introspect_invalid_token_is_inactive() -> None:
    response = client.post(
        "/api/v1/auth/introspect",
        json={"token": "not-a-jwt"},
        headers={"X-API-Key": _service_key()},
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"active": False, "reason": "invalid_or_expired_token"}


def test_introspect_token_type_mismatch() -> None:
    response = client.post(
        "/api/v1/auth/introspect",
        json={"token": _login_token(), "token_type_hint": "refresh_token"},
        headers={"X-API-Key": _service_key()},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["active"] is False
    assert body["reason"] == "token_type_mismatch"


def test_revocations_requires_service_key() -> None:
    assert client.get("/api/v1/auth/revocations").status_code == 401


def test_revocations_snapshot_shape_and_incremental_cursor() -> None:
    headers = {"X-API-Key": _service_key()}
    response = client.get("/api/v1/auth/revocations", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) >= {
        "since",
        "next_since",
        "generated_at",
        "limit",
        "subjects",
        "service_keys",
        "agent_keys",
    }
    assert isinstance(body["subjects"], list)
    assert body["next_since"] >= body["since"]

    incremental = client.get(
        f"/api/v1/auth/revocations?since={body['next_since']}", headers=headers
    )
    assert incremental.status_code == 200, incremental.text
    assert incremental.json()["since"] == body["next_since"]

    limited = client.get("/api/v1/auth/revocations?limit=1", headers=headers)
    assert limited.status_code == 200, limited.text
    assert limited.json()["limit"] == 1
