"""测试 v1.4.1 R-373 storage S3/MinIO 适配（TD-141-07 补充：单元级，mock boto3）. """

from openbase.modules.storage import S3StorageBackend, _resolve_s3_config, get_backend
from openbase.settings import Settings


class _FakeBody:
    def __init__(self, content: bytes) -> None:
        self._content = content

    def read(self) -> bytes:
        return self._content


class _FakeS3Client:
    """记录调用的 boto3 客户端桩."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.created_buckets: set[str] = set()
        self.head_bucket_errors = 0

    def head_bucket(self, Bucket: str) -> dict:
        if Bucket not in self.created_buckets:
            from botocore.exceptions import ClientError

            raise ClientError(
                {"Error": {"Code": "404", "Message": "Not Found"}},
                "HeadBucket",
            )
        return {}

    def create_bucket(self, Bucket: str) -> dict:
        self.created_buckets.add(Bucket)
        return {}

    def put_object(self, Bucket: str, Key: str, Body: bytes, **_: object) -> dict:
        self.objects[f"{Bucket}/{Key}"] = Body
        return {}

    def get_object(self, Bucket: str, Key: str) -> dict:
        return {"Body": _FakeBody(self.objects[f"{Bucket}/{Key}"])}

    def delete_object(self, Bucket: str, Key: str) -> dict:
        self.objects.pop(f"{Bucket}/{Key}", None)
        return {}


def _make_backend(fake_client: _FakeS3Client, **kwargs: object) -> S3StorageBackend:
    backend = S3StorageBackend(endpoint="http://minio.local:9000", bucket="test-bucket", **kwargs)
    backend._client = fake_client  # 注入桩，绕过懒加载
    return backend


def test_s3_backend_save_returns_s3_reference() -> None:
    """save 返回 s3://{bucket}/{key} 引用并上传对象."""
    fake = _FakeS3Client()
    backend = _make_backend(fake)

    path = backend.save("report.pdf", b"pdf-bytes")
    assert path.startswith("s3://test-bucket/")
    assert "report.pdf" in path

    key = path.split("test-bucket/", 1)[1]
    assert fake.objects[f"test-bucket/{key}"] == b"pdf-bytes"
    assert "test-bucket" in fake.created_buckets  # bucket 幂等创建


def test_s3_backend_load_roundtrip() -> None:
    """load 读取对象内容（roundtrip 一致）."""
    fake = _FakeS3Client()
    backend = _make_backend(fake)

    path = backend.save("data.bin", b"\x00\x01\x02")
    assert backend.load(path) == b"\x00\x01\x02"


def test_s3_backend_delete_removes_object() -> None:
    """delete 删除对象（不存在时静默）."""
    fake = _FakeS3Client()
    backend = _make_backend(fake)

    path = backend.save("tmp.txt", b"x")
    backend.delete(path)
    assert fake.objects == {}

    backend.delete("s3://test-bucket/missing.txt")  # 不抛异常
    assert fake.objects == {}


def test_s3_backend_parse_path_rejects_invalid() -> None:
    """非法 storage_path 抛出 ValueError."""
    fake = _FakeS3Client()
    backend = _make_backend(fake)
    try:
        backend.load("/local/path.txt")
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_s3_config_resolution_priority() -> None:
    """配置解析优先级：OPENBASE_STORAGE_S3_* > MINIO_*."""
    import os

    os.environ["OPENBASE_STORAGE_S3_ENDPOINT"] = "http://openbase-s3:9000"
    os.environ["MINIO_ENDPOINT"] = "http://minio:9000"
    os.environ["OPENBASE_STORAGE_S3_BUCKET"] = "openbase-custom"
    try:
        config = _resolve_s3_config()
        assert config["endpoint"] == "http://openbase-s3:9000"
        assert config["bucket"] == "openbase-custom"
    finally:
        os.environ.pop("OPENBASE_STORAGE_S3_ENDPOINT", None)
        os.environ.pop("OPENBASE_STORAGE_S3_BUCKET", None)
        os.environ.pop("MINIO_ENDPOINT", None)


def test_s3_config_fallback_to_minio_env() -> None:
    """无 OPENBASE_* 配置时回退 MINIO_* 共享约定."""
    import os

    os.environ["MINIO_ENDPOINT"] = "http://192.168.0.151:9000"
    os.environ["MINIO_ACCESS_KEY"] = "minioadmin"
    os.environ["MINIO_SECRET_KEY"] = "minioadmin"
    try:
        config = _resolve_s3_config()
        assert config["endpoint"] == "http://192.168.0.151:9000"
        assert config["access_key"] == "minioadmin"
    finally:
        os.environ.pop("MINIO_ENDPOINT", None)
        os.environ.pop("MINIO_ACCESS_KEY", None)
        os.environ.pop("MINIO_SECRET_KEY", None)


def test_get_backend_default_local(monkeypatch) -> None:
    """默认 storage_backend=local 返回 LocalStorageBackend."""
    import openbase.modules.storage as storage_module

    monkeypatch.setattr(storage_module, "_backend", None)
    monkeypatch.setattr(storage_module, "get_settings", lambda: Settings())
    backend = get_backend()
    assert backend.name == "local"


def test_get_backend_s3_when_configured(monkeypatch) -> None:
    """storage_backend=minio + endpoint 配置 → S3StorageBackend."""
    import openbase.modules.storage as storage_module

    monkeypatch.setattr(storage_module, "_backend", None)
    monkeypatch.setattr(storage_module, "get_settings", lambda: Settings(storage_backend="minio"))
    monkeypatch.setattr(
        storage_module, "_resolve_s3_config",
        lambda: {"endpoint": "http://minio:9000", "access_key": "a", "secret_key": "s", "bucket": "b"},
    )
    backend = get_backend()
    assert backend.name == "s3"


def test_get_backend_fallback_local_when_no_endpoint(monkeypatch) -> None:
    """storage_backend=s3 但无 endpoint → 回退 LocalStorageBackend."""
    import openbase.modules.storage as storage_module

    monkeypatch.setattr(storage_module, "_backend", None)
    monkeypatch.setattr(storage_module, "get_settings", lambda: Settings(storage_backend="s3"))
    monkeypatch.setattr(
        storage_module, "_resolve_s3_config",
        lambda: {"endpoint": "", "access_key": "a", "secret_key": "s", "bucket": "b"},
    )
    backend = get_backend()
    assert backend.name == "local"
