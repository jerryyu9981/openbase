"""RSA 密钥材料加载与 JWKS 文档构建（E1-5A）.

本模块**不依赖** ``openbase.settings``（供 settings 启动门禁与 jwt 运行期共用，
避免循环导入）。私钥只读挂载 PEM 文件；公钥由私钥派生，或经
``jwt_jwks_public_keys`` 显式登记（历史/过渡 kid，双验签期使用）。

安全约束：对外 JWKS 只输出公钥分量（kty/n/e），绝不输出私钥分量（d/p/q/dp/dq/qi）。
"""

from __future__ import annotations

import functools
import json
import os
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwk as jose_jwk

RSA_ALGORITHM = "RS256"


class JwtKeyConfigError(ValueError):
    """JWT 密钥配置错误（启动门禁按 ValueError 处理，fail-fast）."""


def _read_text(path: str) -> str:
    """读取文本文件（失败统一转 JwtKeyConfigError，避免裸 OSError 泄漏路径细节）."""
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except OSError as exc:
        raise JwtKeyConfigError(f"无法读取 JWT RSA 密钥文件 {path}：{exc}") from exc


def parse_private_pem(pem: str, *, source: str) -> rsa.RSAPrivateKey:
    """解析 PEM 私钥并要求为 RSA（当前仅支持 RS256）."""
    try:
        key = serialization.load_pem_private_key(pem.encode("utf-8"), password=None)
    except Exception as exc:  # noqa: BLE001 - 解析失败原因多样，统一转配置错误
        raise JwtKeyConfigError(f"{source} 不是合法的 PEM 私钥：{exc}") from exc
    if not isinstance(key, rsa.RSAPrivateKey):
        raise JwtKeyConfigError(f"{source} 不是 RSA 私钥（当前仅支持 RS256）")
    return key


def parse_public_pem(pem: str, *, source: str) -> rsa.RSAPublicKey:
    """解析 PEM 公钥并要求为 RSA."""
    try:
        key = serialization.load_pem_public_key(pem.encode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - 解析失败原因多样，统一转配置错误
        raise JwtKeyConfigError(f"{source} 不是合法的 PEM 公钥：{exc}") from exc
    if not isinstance(key, rsa.RSAPublicKey):
        raise JwtKeyConfigError(f"{source} 不是 RSA 公钥（当前仅支持 RS256）")
    return key


def _public_pem_text(public_key: rsa.RSAPublicKey) -> str:
    return public_key.public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")


def public_jwk(public_pem_text: str) -> dict[str, Any]:
    """PEM 公钥 → JWK 公钥分量（kty/n/e/alg，无任何私钥分量）."""
    try:
        document = jose_jwk.construct(public_pem_text, RSA_ALGORITHM).to_dict()
    except Exception as exc:  # noqa: BLE001 - jose 抛 JWKError 等
        raise JwtKeyConfigError(f"PEM 公钥无法转换为 JWK：{exc}") from exc
    return {
        "kty": document["kty"],
        "n": document["n"],
        "e": document["e"],
        "alg": RSA_ALGORITHM,
    }


@functools.lru_cache(maxsize=8)
def _load_key_material_cached(
    path: str, mtime_ns: int, size: int
) -> tuple[str, str, dict[str, Any]]:
    """按 (路径, mtime, 大小) 缓存私钥 PEM 与派生公钥（换钥后自动失效）."""
    private_pem = _read_text(path)
    private_key = parse_private_pem(private_pem, source=f"JWT RSA 私钥文件 {path}")
    public_pem = _public_pem_text(private_key.public_key())
    return private_pem, public_pem, public_jwk(public_pem)


def load_key_material(path: str) -> dict[str, Any]:
    """读取私钥 PEM 与派生公钥/JWK（带 mtime 缓存，支持平滑换钥）.

    Returns:
        {"private_pem": str, "public_pem": str, "public_jwk": dict}

    Raises:
        JwtKeyConfigError: 文件不存在/不可读/非 RSA 私钥。
    """
    try:
        stat = os.stat(path)
    except OSError as exc:
        raise JwtKeyConfigError(
            f"JWT RSA 私钥文件不存在或不可读：{path}"
        ) from exc
    private_pem, public_pem, public_jwk_document = _load_key_material_cached(
        path, stat.st_mtime_ns, stat.st_size
    )
    return {
        "private_pem": private_pem,
        "public_pem": public_pem,
        "public_jwk": dict(public_jwk_document),
    }


@functools.lru_cache(maxsize=8)
def _parse_public_keys_map_cached(raw: str) -> dict[str, str]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise JwtKeyConfigError(
            f"OPENBASE_JWT_JWKS_PUBLIC_KEYS 不是合法 JSON：{exc}"
        ) from exc
    if not isinstance(parsed, dict):
        raise JwtKeyConfigError("OPENBASE_JWT_JWKS_PUBLIC_KEYS 顶层必须是对象")
    result: dict[str, str] = {}
    for kid, value in parsed.items():
        if not isinstance(kid, str) or not kid.strip():
            raise JwtKeyConfigError(
                "OPENBASE_JWT_JWKS_PUBLIC_KEYS 的 kid 必须是非空字符串"
            )
        if not isinstance(value, str) or not value.strip():
            raise JwtKeyConfigError(
                f"OPENBASE_JWT_JWKS_PUBLIC_KEYS.{kid} 必须是非空字符串"
            )
        text = value.strip()
        public_pem = _read_text(text[1:].strip()) if text.startswith("@") else value
        parse_public_pem(public_pem, source=f"OPENBASE_JWT_JWKS_PUBLIC_KEYS.{kid}")
        result[kid.strip()] = public_pem
    return result


def parse_public_keys_map(raw: str | None) -> dict[str, str]:
    """解析 ``jwt_jwks_public_keys``：JSON ``{kid: PEM 文本或 @路径}``；空 → {}.

    Raises:
        JwtKeyConfigError: JSON 非法 / 结构不符 / 公钥不可解析。
    """
    text = (raw or "").strip()
    if not text:
        return {}
    return dict(_parse_public_keys_map_cached(text))


def build_jwks(
    *,
    private_key_path: str = "",
    signing_kid: str = "",
    extra_public_keys_raw: str = "",
) -> dict[str, Any]:
    """构建 JWKS 文档（签发公钥优先，随后追加显式登记的历史/过渡公钥）."""
    keys: list[dict[str, Any]] = []
    seen_kids: set[str] = set()

    path = (private_key_path or "").strip()
    if path:
        kid = (signing_kid or "").strip()
        entry = dict(load_key_material(path)["public_jwk"])
        entry.update({"kid": kid, "use": "sig", "alg": RSA_ALGORITHM})
        keys.append(entry)
        seen_kids.add(kid)

    for kid, public_pem in parse_public_keys_map(extra_public_keys_raw).items():
        if kid in seen_kids:
            continue
        entry = public_jwk(public_pem)
        entry.update({"kid": kid, "use": "sig", "alg": RSA_ALGORITHM})
        keys.append(entry)
        seen_kids.add(kid)

    return {"keys": keys}


def public_pem_for_kid(
    kid: str | None,
    *,
    private_key_path: str = "",
    signing_kid: str = "",
    extra_public_keys_raw: str = "",
) -> str | None:
    """按 kid 取验签公钥 PEM；未知 kid → None（fail-closed）.

    无 kid 时仅当「唯一公钥」可确定才回退（单密钥部署兼容），否则 None。
    """
    path = (private_key_path or "").strip()
    signing = (signing_kid or "").strip()
    extras = parse_public_keys_map(extra_public_keys_raw)

    if kid:
        if path and kid == signing:
            return load_key_material(path)["public_pem"]
        return extras.get(kid)

    candidates: list[str] = []
    if path:
        candidates.append(load_key_material(path)["public_pem"])
    candidates.extend(extras.values())
    if len(candidates) == 1:
        return candidates[0]
    return None


def clear_key_cache() -> None:
    """清空密钥缓存（测试/换钥排障用）."""
    _load_key_material_cached.cache_clear()
    _parse_public_keys_map_cached.cache_clear()
