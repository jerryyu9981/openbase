"""真实环境集成测试（v1.4.1 R-373 闭环 + 共享基础设施验证）.

依赖 .env.shared-infra（192.168.0.151 共享测试基础设施）。
执行方式：设置 OPENBASE_TEST_REAL_INFRA=1 后运行（未设置默认 skip）。
"""

import asyncio
import os
import uuid
from pathlib import Path

import pytest

REAL_ENV_FLAG = "OPENBASE_TEST_REAL_INFRA"

pytestmark = pytest.mark.skipif(
    not os.environ.get(REAL_ENV_FLAG),
    reason="真实环境测试需 OPENBASE_TEST_REAL_INFRA=1",
)

_PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_shared_infra_env() -> dict[str, str]:
    """解析项目根 .env.shared-infra 配置到环境变量（只覆盖未设置的键）."""
    env_file = _PROJECT_ROOT / ".env.shared-infra"
    assert env_file.exists(), ".env.shared-infra 不存在"
    loaded: dict[str, str] = {}
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if key and value and not os.environ.get(key):
            os.environ[key] = value
            loaded[key] = value
    return loaded


_shared = _load_shared_infra_env()


def test_real_minio_roundtrip() -> None:
    """真实 MinIO：S3StorageBackend save/load/delete 闭环."""
    from openbase.modules.storage import S3StorageBackend

    backend = S3StorageBackend(
        endpoint=_shared.get("MINIO_ENDPOINT", os.environ.get("MINIO_ENDPOINT", "")),
        access_key=_shared.get("MINIO_ACCESS_KEY", "minioadmin"),
        secret_key=_shared.get("MINIO_SECRET_KEY", "minioadmin"),
        bucket=f"openbase-it-{uuid.uuid4().hex[:8]}",
    )
    assert backend.client is not None

    content = b"real-minio-bytes"
    path = backend.save("real.txt", content)
    assert path.startswith("s3://")

    assert backend.load(path) == content
    backend.delete(path)

    import boto3  # noqa: F401  # 已验证 boto3 依赖可用
    print(f"MINIO_REAL_OK path={path}")


def test_real_postgres_connectivity() -> None:
    """真实 PostgreSQL：连接 + 版本 + schema 查询."""
    import asyncpg

    url = _shared.get("POSTGRES_URL", os.environ.get("POSTGRES_URL", ""))
    assert url, "缺少 POSTGRES_URL"

    async def _check() -> str:
        conn = await asyncpg.connect(url, timeout=8)
        try:
            version = await conn.fetchval("SELECT version()")
            return str(version).split(",")[0]
        finally:
            await conn.close()

    version = asyncio.run(_check())
    assert version.startswith("PostgreSQL"), version
    print(f"PG_REAL_OK version={version}")


def test_real_redis_connectivity() -> None:
    """真实 Redis：ping + set/get/delete."""
    import redis

    client = redis.Redis(
        host=_shared.get("REDIS_HOST", "192.168.0.151"),
        port=int(_shared.get("REDIS_PORT", "6380")),
        password=_shared.get("REDIS_PASSWORD", ""),
        socket_timeout=5,
    )
    assert client.ping()
    key = f"openbase-it-{uuid.uuid4().hex[:6]}"
    client.set(key, "ok", ex=60)
    assert client.get(key) == b"ok"
    client.delete(key)
    print("REDIS_REAL_OK")


def test_real_get_backend_uses_s3() -> None:
    """storage_backend=minio + MINIO_ENDPOINT 配置时 get_backend 返回 S3 且真实可用."""
    import openbase.modules.storage as storage_module
    from openbase.settings import Settings

    original_backend = storage_module._backend
    original_get_settings = storage_module.get_settings
    original_env = os.environ.get("OPENBASE_STORAGE_S3_ENDPOINT")
    try:
        storage_module._backend = None
        storage_module.get_settings = lambda: Settings(storage_backend="minio")
        os.environ["OPENBASE_STORAGE_S3_ENDPOINT"] = _shared.get("MINIO_ENDPOINT", "")
        backend = storage_module.get_backend()
        assert backend.name == "s3"
        path = backend.save("via-get-backend.txt", b"gb")
        assert backend.load(path) == b"gb"
        backend.delete(path)
        print("GET_BACKEND_S3_REAL_OK")
    finally:
        storage_module._backend = original_backend
        storage_module.get_settings = original_get_settings
        if original_env is None:
            os.environ.pop("OPENBASE_STORAGE_S3_ENDPOINT", None)
        else:
            os.environ["OPENBASE_STORAGE_S3_ENDPOINT"] = original_env
