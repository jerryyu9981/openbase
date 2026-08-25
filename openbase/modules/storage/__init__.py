"""storage 模块：统一文件存储（本地/MinIO/S3 适配）."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile
from pydantic import BaseModel

from openbase.settings import get_settings

router = APIRouter(prefix="/api/v1/files", tags=["storage"])

# 文件元数据（v1.0.0 最小实现：本地存储 + 内存元数据）
_records: dict[int, dict] = {}
_next_id = 1


class FileRecordOut(BaseModel):
    """文件记录响应."""

    id: int
    file_name: str
    storage_path: str
    backend: str
    content_type: str | None = None
    size: int


class LocalStorageBackend:
    """本地文件存储适配器."""

    name = "local"

    def __init__(self, base_path: str) -> None:
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save(self, file_name: str, content: bytes) -> str:
        """保存文件，返回相对路径."""
        storage_name = f"{uuid.uuid4().hex}_{file_name}"
        target = self.base_path / storage_name
        target.write_bytes(content)
        return str(target)

    def load(self, storage_path: str) -> bytes:
        """读取文件内容."""
        return Path(storage_path).read_bytes()

    def delete(self, storage_path: str) -> None:
        """删除文件."""
        Path(storage_path).unlink(missing_ok=True)


_backend = LocalStorageBackend(get_settings().storage_local_path)


def get_backend():
    """获取存储后端（v1.0.0 实现本地，MinIO/S3 适配器接口一致）."""
    return _backend


@router.post("", response_model=FileRecordOut)
async def upload_file(file: UploadFile) -> FileRecordOut:
    """上传文件（multipart）."""
    global _next_id
    content = await file.read()
    backend = get_backend()
    storage_path = backend.save(file.filename or "unnamed", content)

    record = {
        "id": _next_id,
        "file_name": file.filename or "unnamed",
        "storage_path": storage_path,
        "backend": backend.name,
        "content_type": file.content_type,
        "size": len(content),
    }
    _records[_next_id] = record
    _next_id += 1
    return FileRecordOut(**record)


@router.get("/{file_id}", response_model=FileRecordOut)
async def get_file(file_id: int) -> FileRecordOut:
    """获取文件元数据."""
    record = _records.get(file_id)
    if record is None:
        from openbase.core.errors import BaseError, ErrorCode

        raise BaseError(ErrorCode.STORAGE_FILE_NOT_FOUND, "file not found")
    return FileRecordOut(**record)


@router.get("", response_model=list[FileRecordOut])
async def list_files() -> list[FileRecordOut]:
    """文件列表."""
    return [FileRecordOut(**r) for r in _records.values()]


@router.delete("/{file_id}")
async def delete_file(file_id: int) -> dict:
    """删除文件（含存储内容）."""
    record = _records.pop(file_id, None)
    if record:
        get_backend().delete(record["storage_path"])
    return {"deleted": file_id}
