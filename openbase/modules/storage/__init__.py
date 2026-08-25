"""storage 模块：统一文件存储（本地/MinIO/S3 适配，数据库优先 + 内存回退）."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openbase.core.db.services import BaseDBService
from openbase.core.db.session import get_db
from openbase.core.models import FileRecord
from openbase.settings import get_settings

logger = logging.getLogger("openbase.storage")

router = APIRouter(prefix="/api/v1/files", tags=["storage"])

# 文件元数据（数据库不可用时内存回退）
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


def _to_out(r: dict) -> FileRecordOut:
    return FileRecordOut(
        id=r["id"], file_name=r["file_name"], storage_path=r["storage_path"],
        backend=r["backend"], content_type=r.get("content_type"), size=r["size"],
    )


class FileService(BaseDBService):
    """文件元数据服务：数据库优先 + 内存回退."""

    @classmethod
    async def create(
        cls, session: AsyncSession, file_name: str, storage_path: str,
        backend: str, content_type: str | None, size: int,
    ) -> dict:
        rec = FileRecord(
            file_name=file_name, file_path=storage_path, backend=backend,
            mime_type=content_type, size=size,
        )
        session.add(rec)
        await session.commit()
        return {"id": rec.id, "file_name": file_name, "storage_path": storage_path,
                "backend": backend, "content_type": content_type, "size": size}

    @classmethod
    async def get(cls, session: AsyncSession, file_id: int) -> dict | None:
        r = (await session.execute(select(FileRecord).where(FileRecord.id == file_id))).scalar_one_or_none()
        if r is None:
            return None
        return {"id": r.id, "file_name": r.file_name, "storage_path": r.file_path,
                "backend": r.backend, "content_type": r.mime_type, "size": r.size}

    @classmethod
    async def list_all(cls, session: AsyncSession) -> list[dict]:
        rows = (await session.execute(select(FileRecord).order_by(FileRecord.id))).scalars().all()
        return [{"id": r.id, "file_name": r.file_name, "storage_path": r.file_path,
                 "backend": r.backend, "content_type": r.mime_type, "size": r.size} for r in rows]

    @classmethod
    async def delete(cls, session: AsyncSession, file_id: int) -> dict | None:
        r = (await session.execute(select(FileRecord).where(FileRecord.id == file_id))).scalar_one_or_none()
        if r is None:
            return None
        await session.delete(r)
        await session.commit()
        return {"deleted": file_id, "storage_path": r.file_path}

    # ---- 内存回退 ----
    @classmethod
    async def create_mem(cls, file_name: str, storage_path: str, backend: str,
                         content_type: str | None, size: int) -> dict:
        global _next_id
        rec = {"id": _next_id, "file_name": file_name, "storage_path": storage_path,
               "backend": backend, "content_type": content_type, "size": size}
        _records[_next_id] = rec
        _next_id += 1
        return rec

    @classmethod
    async def get_mem(cls, file_id: int) -> dict | None:
        return _records.get(file_id)

    @classmethod
    async def list_all_mem(cls) -> list[dict]:
        return list(_records.values())

    @classmethod
    async def delete_mem(cls, file_id: int) -> dict | None:
        return _records.pop(file_id, None)


@router.post("", response_model=FileRecordOut)
async def upload_file(file: UploadFile, session: AsyncSession = Depends(get_db)) -> FileRecordOut:
    """上传文件（multipart；元数据落库）."""
    content = await file.read()
    backend = get_backend()
    storage_path = backend.save(file.filename or "unnamed", content)
    try:
        record = await FileService.create(
            session, file.filename or "unnamed", storage_path, backend.name,
            file.content_type, len(content),
        )
    except Exception as exc:  # noqa: BLE001
        FileService._fallback("storage.create", exc)
        record = await FileService.create_mem(
            file.filename or "unnamed", storage_path, backend.name,
            file.content_type, len(content),
        )
    return _to_out(record)


@router.get("/{file_id}", response_model=FileRecordOut)
async def get_file(file_id: int, session: AsyncSession = Depends(get_db)) -> FileRecordOut:
    """获取文件元数据."""
    try:
        record = await FileService.get(session, file_id)
    except Exception as exc:  # noqa: BLE001
        FileService._fallback("storage.get", exc)
        record = await FileService.get_mem(file_id)
    if record is None:
        from openbase.core.errors import BaseError, ErrorCode

        raise BaseError(ErrorCode.STORAGE_FILE_NOT_FOUND, "file not found")
    return _to_out(record)


@router.get("", response_model=list[FileRecordOut])
async def list_files(session: AsyncSession = Depends(get_db)) -> list[FileRecordOut]:
    """文件列表."""
    try:
        records = await FileService.list_all(session)
    except Exception as exc:  # noqa: BLE001
        FileService._fallback("storage.list", exc)
        records = await FileService.list_all_mem()
    return [_to_out(r) for r in records]


@router.delete("/{file_id}")
async def delete_file(file_id: int, session: AsyncSession = Depends(get_db)) -> dict:
    """删除文件（含存储内容）."""
    try:
        result = await FileService.delete(session, file_id)
    except Exception as exc:  # noqa: BLE001
        FileService._fallback("storage.delete", exc)
        result = await FileService.delete_mem(file_id)
    if result is not None and "storage_path" in result:
        get_backend().delete(result["storage_path"])
    elif result is not None:
        get_backend().delete(result.get("storage_path", ""))
    return {"deleted": file_id}
