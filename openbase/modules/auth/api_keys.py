"""服务级 API Key 存储（v1.4.1 R-367/368，对齐完整方案 2.5 服务 Key ②）.

ApiKeyStore：内存存储 + 哈希保存（sha256），支持签发/校验/吊销/列表。
scope 模型：{"system": ["openllm"], "tenants": ["*"]}（* 表示全量）。
验证时同时校验 system 与 tenant scope。
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import threading
import time
import uuid
from typing import Any

logger = logging.getLogger("openbase.auth.api_keys")

KEY_PREFIX = "ob_k_"


_INTERNAL_FIELDS = frozenset({"key_hash"})


def _public_record(record: dict[str, Any]) -> dict[str, Any]:
    """对外凭据副本：剔除存储内部字段（`key_hash`），避免凭据面外泄哈希.

    Returns:
        浅拷贝后的记录（调用方可安全改写，不影响存储内记录）。
    """
    return {key: value for key, value in record.items() if key not in _INTERNAL_FIELDS}


class ApiKeyStore:
    """服务 Key 存储与校验（线程安全）.

    Attributes:
        _keys: instance_id → 记录（key_hash/name/scope/created/revoked）。
    """

    def __init__(self) -> None:
        self._keys: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()

    # ---- 签发 ----

    def create(
        self,
        name: str,
        scope: dict[str, Any] | None = None,
        description: str | None = None,
    ) -> str:
        """签发服务 Key，返回明文（仅此一次可见）.

        Args:
            name: Key 名称（如 gateway-agent）。
            scope: 访问范围 {"system": [...], "tenants": [...]}，缺省全量。
            description: 备注。

        Returns:
            明文 Key（前缀 ob_k_）。
        """
        raw_key = f"{KEY_PREFIX}{secrets.token_urlsafe(24)}"
        key_hash = self._hash(raw_key)
        with self._lock:
            self._keys[key_hash] = {
                # v1.9.2：稳定标识（列表可回显，支持按 id 吊销，避免依赖明文 Key）
                "id": uuid.uuid4().hex,
                "name": name,
                "key_hash": key_hash,
                "scope": scope or {"system": ["*"], "tenants": ["*"]},
                "description": description or "",
                "created": time.time(),
                "revoked": False,
            }
        logger.info("api key created", extra={"key_name": name})
        return raw_key

    def revoke(self, raw_key: str) -> None:
        """吊销 Key（按哈希匹配，吊销后校验失败）."""
        key_hash = self._hash(raw_key)
        with self._lock:
            record = self._keys.get(key_hash)
            if record is not None:
                record["revoked"] = True
                logger.info("api key revoked", extra={"key_name": record["name"]})

    def revoke_by_id(self, key_id: str) -> bool:
        """按稳定标识吊销（列表可回显 id，前端无需持有明文）.

        Args:
            key_id: 记录 id（创建时生成）。

        Returns:
            命中并吊销返回 True；未找到返回 False。
        """
        with self._lock:
            for record in self._keys.values():
                if record.get("id") == key_id:
                    record["revoked"] = True
                    logger.info("api key revoked by id", extra={"key_name": record["name"]})
                    return True
        return False

    # ---- 校验 ----

    def verify(
        self,
        raw_key: str,
        system: str | None = None,
        tenant_id: str | None = None,
    ) -> dict[str, Any] | None:
        """校验 Key 有效性 + scope.

        Args:
            raw_key: 明文 Key。
            system: 目标系统（scope 校验）。
            tenant_id: 目标租户（scope 校验）。

        Returns:
            通过返回记录**副本**（不含 `key_hash`）；无效/吊销/越 scope 返回 None。
        """
        key_hash = self._hash(raw_key)
        with self._lock:
            record = self._keys.get(key_hash)
            if record is None or record["revoked"]:
                return None

        scope = record["scope"]
        systems = scope.get("system") or ["*"]
        tenants = scope.get("tenants") or ["*"]
        if system is not None and system not in systems and "*" not in systems:
            return None
        if tenant_id is not None and tenant_id not in tenants and "*" not in tenants:
            return None
        return _public_record(record)

    def list_keys(self) -> list[dict[str, Any]]:
        """列表签发记录（不回显明文 Key / 哈希）."""
        with self._lock:
            return [_public_record(record) for record in self._keys.values()]

    @staticmethod
    def _hash(raw_key: str) -> str:
        """哈希明文 Key（sha256，盐可后续接入）."""
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
