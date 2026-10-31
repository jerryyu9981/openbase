"""E3-4 统一 IdP Provider 抽象层（多 IdP 登记 + 声明映射 + 启动门禁）.

现状：OIDC 单 IdP 由 ``oidc_*`` 配置驱动，claims 适配由 ``oidc_profile``
（``generic`` / ``keycloak``）承载。本模块在其上补一层**多 Provider 登记**：

- ``OPENBASE_IDP_PROVIDERS``（JSON 数组）登记多个 IdP（政务统一身份平台等）；
- 每个 Provider 声明 discovery / client / 回调 / scopes / profile / 角色 claim / 默认租户；
- 启动门禁校验（JSON 合法、名称唯一、必填项齐全、profile 受支持），fail-fast；
- 只读端点列出 Provider（**绝不下发 client_secret**）。

默认留空 = 不登记任何 Provider，行为与既有单 IdP 配置完全一致。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Depends

from openbase.core.deps.auth import get_current_user
from openbase.settings import (
    OIDC_ID_TOKEN_ALGORITHMS,
    OIDC_TOKEN_AUTH_METHODS,
    get_settings,
)

IDP_PROFILE_GENERIC = "generic"
IDP_PROFILE_KEYCLOAK = "keycloak"
SUPPORTED_IDP_PROFILES: frozenset[str] = frozenset(
    {IDP_PROFILE_GENERIC, IDP_PROFILE_KEYCLOAK}
)

router = APIRouter(prefix="/api/v1/auth/idp", tags=["auth"])

__all__ = [
    "IDP_PROFILE_GENERIC",
    "IDP_PROFILE_KEYCLOAK",
    "SUPPORTED_IDP_PROFILES",
    "IdpProviderConfig",
    "parse_idp_providers",
    "public_provider_views",
    "router",
]


@dataclass(frozen=True)
class IdpProviderConfig:
    """单个 IdP Provider 配置（敏感字段不参与对外视图）."""

    name: str
    discovery_url: str
    client_id: str
    client_secret: str = ""
    redirect_uri: str = ""
    scopes: str = "openid profile email"
    profile: str = IDP_PROFILE_GENERIC
    claim_role: str = "roles"
    default_tenant: str = "tenant-1"
    # C-05：Provider 级覆盖（None/空串 = 回落全局配置）
    pkce_enabled: bool | None = None
    signing_algorithms: str = ""
    token_auth_method: str = ""


def _normalized_signing_algorithms(name: str, raw: Any) -> str:
    """归一 Provider 声明的 ID Token 算法白名单（逗号分隔、大写、去重保序）.

    空值表示未声明（回落全局）；含未接线算法即报错（fail-fast）。

    Raises:
        ValueError: 声明含未接线算法。
    """
    text = str(raw or "").strip()
    if not text:
        return ""
    algorithms: list[str] = []
    for item in text.split(","):
        algorithm = item.strip().upper()
        if algorithm and algorithm not in algorithms:
            algorithms.append(algorithm)
    unsupported = sorted(set(algorithms) - set(OIDC_ID_TOKEN_ALGORITHMS))
    if unsupported:
        raise ValueError(
            f"IdP Provider {name} 的 signing_algorithms 含未接线算法："
            f"{','.join(unsupported)}；可用值：{','.join(OIDC_ID_TOKEN_ALGORITHMS)}"
        )
    return ",".join(algorithms)


def _provider_from_object(raw: Any, index: int) -> IdpProviderConfig:
    """JSON 对象 → :class:`IdpProviderConfig`（缺必填项抛 ValueError）."""
    if not isinstance(raw, dict):
        raise ValueError(f"IdP Provider 第 {index} 项必须为对象")
    name = str(raw.get("name") or "").strip()
    if not name:
        raise ValueError(f"IdP Provider 第 {index} 项缺少 name")
    discovery_url = str(raw.get("discovery_url") or "").strip()
    if not discovery_url.startswith(("http://", "https://")):
        raise ValueError(f"IdP Provider {name} 的 discovery_url 必须为 http(s) 地址")
    client_id = str(raw.get("client_id") or "").strip()
    if not client_id:
        raise ValueError(f"IdP Provider {name} 缺少 client_id")
    profile = str(raw.get("profile") or IDP_PROFILE_GENERIC).strip().lower()
    if profile not in SUPPORTED_IDP_PROFILES:
        raise ValueError(
            f"IdP Provider {name} 的 profile 不受支持：{profile}"
            "（可选 generic / keycloak）"
        )
    pkce_raw = raw.get("pkce_enabled")
    if pkce_raw is None:
        pkce_enabled: bool | None = None
    elif isinstance(pkce_raw, bool):
        pkce_enabled = pkce_raw
    else:
        raise ValueError(f"IdP Provider {name} 的 pkce_enabled 必须为布尔值")
    signing_algorithms = _normalized_signing_algorithms(
        name, raw.get("signing_algorithms")
    )
    token_auth_method = str(raw.get("token_auth_method") or "").strip().lower()
    if token_auth_method and token_auth_method not in OIDC_TOKEN_AUTH_METHODS:
        raise ValueError(
            f"IdP Provider {name} 的 token_auth_method 取值非法：{token_auth_method}；"
            f"可用值：{','.join(OIDC_TOKEN_AUTH_METHODS)}"
        )
    return IdpProviderConfig(
        name=name,
        discovery_url=discovery_url,
        client_id=client_id,
        client_secret=str(raw.get("client_secret") or ""),
        redirect_uri=str(raw.get("redirect_uri") or ""),
        scopes=str(raw.get("scopes") or "openid profile email"),
        profile=profile,
        claim_role=str(raw.get("claim_role") or "roles"),
        default_tenant=str(raw.get("default_tenant") or "tenant-1"),
        pkce_enabled=pkce_enabled,
        signing_algorithms=signing_algorithms,
        token_auth_method=token_auth_method,
    )


def parse_idp_providers(raw: str) -> tuple[IdpProviderConfig, ...]:
    """解析 ``OPENBASE_IDP_PROVIDERS``（供启动门禁与运行期共用）.

    Args:
        raw: 原始 JSON 文本；空串表示未登记 Provider。

    Returns:
        Provider 元组（保持声明顺序）。

    Raises:
        ValueError: JSON 非法 / 顶层非数组 / 名称重复 / 必填项缺失。
    """
    text = (raw or "").strip()
    if not text:
        return ()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"OPENBASE_IDP_PROVIDERS 不是合法 JSON：{exc}") from exc
    if not isinstance(parsed, list):
        raise ValueError("OPENBASE_IDP_PROVIDERS 顶层必须为 JSON 数组")
    providers = tuple(
        _provider_from_object(item, index)
        for index, item in enumerate(parsed, start=1)
    )
    names = [provider.name for provider in providers]
    if len(set(names)) != len(names):
        raise ValueError("OPENBASE_IDP_PROVIDERS 的 Provider name 必须唯一")
    return providers


def public_provider_views(providers: tuple[IdpProviderConfig, ...]) -> list[dict]:
    """对外视图：只暴露非敏感字段（不含 client_secret）."""
    return [
        {
            "name": provider.name,
            "discovery_url": provider.discovery_url,
            "profile": provider.profile,
            "claim_role": provider.claim_role,
            "scopes": provider.scopes,
            "default_tenant": provider.default_tenant,
            "has_client_secret": bool(provider.client_secret),
            "pkce_enabled": provider.pkce_enabled,
            "signing_algorithms": provider.signing_algorithms,
            "token_auth_method": provider.token_auth_method,
        }
        for provider in providers
    ]


@router.get("/providers")
async def list_idp_providers(user: dict = Depends(get_current_user)) -> dict:
    """列出已登记的 IdP Provider（登录用户可读；不含密钥）."""
    providers = parse_idp_providers(get_settings().idp_providers)
    return {
        "code": "OK",
        "message": "ok",
        "data": {
            "providers": public_provider_views(providers),
            "count": len(providers),
        },
    }
