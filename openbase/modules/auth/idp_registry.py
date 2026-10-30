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
from openbase.settings import get_settings

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
