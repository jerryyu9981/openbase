"""可插拔签名算法注册表（E3-3，国密 SM2 预留位）.

目的：把「JWT 签名算法」从硬编码分支收敛为**注册表 + 可用性探测**，政务交付
需要启用国密时只接线 Provider，不改动签发/验签主流程。

当前可用性口径（不伪造能力）：

- ``HS256`` / ``RS256``：已接线，可用（RS256 见 ``jwt_keys.py`` 与 ``jwt.py``）。
- ``SM2``：**预留**。JWS 标准未定义 SM2，且需要 ``gmssl`` 或密码机提供签名
  原语；本仓尚未接线，故标记为**不可用**——配置为 SM2 时启动门禁直接拒绝
  （fail-fast），绝不静默降级到其它算法。
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "HS256_ALGORITHM",
    "RSA_ALGORITHM",
    "SM2_ALGORITHM",
    "SignatureAlgorithm",
    "assert_signature_algorithm_usable",
    "available_signature_algorithms",
    "get_signature_algorithm",
    "register_signature_algorithm",
]

HS256_ALGORITHM = "HS256"
RSA_ALGORITHM = "RS256"
SM2_ALGORITHM = "SM2"


@dataclass(frozen=True)
class SignatureAlgorithm:
    """签名算法登记项.

    Attributes:
        name: 算法名（JWS ``alg`` 值大小写敏感，统一大写登记）。
        available: 当前进程是否真正可签发/验签。
        note: 不可用原因或启用条件说明。
    """

    name: str
    available: bool
    note: str = ""


_REGISTRY: dict[str, SignatureAlgorithm] = {
    HS256_ALGORITHM: SignatureAlgorithm(HS256_ALGORITHM, True, "HMAC-SHA256（存量/开发）"),
    RSA_ALGORITHM: SignatureAlgorithm(RSA_ALGORITHM, True, "RSA-SHA256（JWKS 发布）"),
    SM2_ALGORITHM: SignatureAlgorithm(
        SM2_ALGORITHM,
        False,
        "国密 SM2 预留：需 gmssl/密码机提供签名原语并在政务交付时接线",
    ),
}


def register_signature_algorithm(
    algorithm: SignatureAlgorithm, *, replace: bool = False
) -> None:
    """登记签名算法（供后续国密 Provider 接线使用）.

    Args:
        algorithm: 算法登记项（名称统一大写）。
        replace: 是否覆盖同名已有登记。

    Raises:
        ValueError: 名称为空，或同名已登记且未声明覆盖。
    """
    name = (algorithm.name or "").strip().upper()
    if not name:
        raise ValueError("签名算法名称不能为空")
    if name in _REGISTRY and not replace:
        raise ValueError(f"签名算法已登记：{name}")
    _REGISTRY[name] = SignatureAlgorithm(name, algorithm.available, algorithm.note)


def get_signature_algorithm(name: str) -> SignatureAlgorithm:
    """按名称取登记项（未知算法抛 ValueError）."""
    normalized = (name or "").strip().upper()
    try:
        return _REGISTRY[normalized]
    except KeyError as exc:
        raise ValueError(f"未知签名算法：{name or '(空)'}") from exc


def assert_signature_algorithm_usable(name: str) -> SignatureAlgorithm:
    """断言算法可用（启动门禁调用；不可用即 fail-fast）."""
    algorithm = get_signature_algorithm(name)
    if not algorithm.available:
        raise ValueError(f"签名算法 {algorithm.name} 当前不可用：{algorithm.note}")
    return algorithm


def available_signature_algorithms() -> tuple[str, ...]:
    """当前可用的算法名（声明顺序）."""
    return tuple(
        algorithm.name for algorithm in _REGISTRY.values() if algorithm.available
    )
