"""OpenBase 配置驱动设置.

提供 Settings 类：模块启停（enable_module/disable_module）、
全局配置（数据库/Redis/鉴权/可观测）与 init_app 装配入口。

数据库配置读取优先级：
1. OPENBASE_DB_URL 环境变量（openbase 自有配置）
2. POSTGRES_URL 环境变量（共享基础设施 .env.shared-infra）
3. 默认值（本地开发）
"""

from __future__ import annotations

import os

from pydantic_settings import BaseSettings, SettingsConfigDict

# 已注册的可用模块（模块包目录中存在即注册）
AVAILABLE_MODULES: tuple[str, ...] = (
    "auth",
    "tenant",
    "audit",
    "observability",
    "config",
    "mcp",
    "org",
    "dict",
    "scheduler",
    "storage",
    "notify",
    # v1.2.0 统一前端增量
    "ai_apps",
    "proxy",
    "frontend",
    # v1.4.0 统一网关增强（服务发现 + 聚合编排）
    "gateway",
    # v1.4.2 四维身份管理（R-375 用户管理 CRUD）
    "users",
    # v1.4.3 OpenLLM 对接（R-379：认证注入 + llm-proxy 转发）
    "llm_proxy",
    # v1.4.4 OpenRAG 对接（R-380：JWT 门禁 + rag-proxy 转发，无上游认证注入）
    "rag_proxy",
    # v1.4.5 DPS 对接（R-381：JWT 门禁 + dps-proxy 转发 + 身份头注入）
    "dps_proxy",
)


def _resolve_db_url() -> str:
    """解析数据库连接串：OPENBASE_DB_URL > POSTGRES_URL > 默认.

    基于 .env.shared-infra 共享基础设施约定（POSTGRES_URL），
    兼容 asyncpg 驱动（自动将 postgresql:// 规范为 postgresql+asyncpg://）。
    """
    url = os.environ.get("OPENBASE_DB_URL") or os.environ.get("POSTGRES_URL", "")
    if not url:
        return "postgresql+asyncpg://postgres:postgres@localhost:5432/openbase"
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def _resolve_redis_url() -> str:
    """解析 Redis 连接串：OPENBASE_REDIS_URL > REDIS_URL > 默认."""
    url = os.environ.get("OPENBASE_REDIS_URL") or os.environ.get("REDIS_URL", "")
    if url:
        return url
    return "redis://localhost:6379/0"


class Settings(BaseSettings):
    """OpenBase 全局配置.

    配置来源优先级：环境变量 > .env 文件 > 默认值。
    """

    model_config = SettingsConfigDict(
        env_prefix="OPENBASE_", env_file=".env", extra="ignore"
    )

    # ---- 基础 ----
    app_name: str = "OpenBase"
    debug: bool = False

    # ---- 数据库 ----
    db_url: str = _resolve_db_url()
    db_echo: bool = False
    # openbase schema 名（共享库内隔离）
    db_schema: str = "openbase"

    # ---- Redis ----
    redis_url: str = _resolve_redis_url()

    # ---- 鉴权 ----
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_seconds: int = 7200
    refresh_expire_seconds: int = 604800
    # bcrypt 成本因子（默认 12 ≈ 400-600ms；并发敏感场景可调低至 10 ≈ 200ms）
    bcrypt_rounds: int = 12
    # MCP 服务级 API Key（逗号分隔；生产环境必须覆盖默认值）
    mcp_api_keys: str = "dev-mcp-key"

    # ---- 多租户 ----
    tenant_mode: str = "schema"  # schema | row

    # ---- 可观测 ----
    otel_enabled: bool = False
    otlp_endpoint: str = "http://localhost:4318"
    langfuse_enabled: bool = False
    sample_rate: float = 0.1

    # ---- 文件存储 ----
    storage_backend: str = "local"  # local | minio | s3
    storage_local_path: str = "./storage"

    # ---- OpenMemory 对接（v1.4.2 R-378，双层认证转发） ----
    memory_api_key: str = "openbase-gw-key-20260830"
    memory_upstream_base: str = "http://127.0.0.1:8020"
    memory_upstream_timeout: float = 20.0

    # ---- OpenLLM 对接（v1.4.3 R-379，API Key Bearer 注入转发） ----
    llm_api_key: str = "sk-openllm-openbase-gateway-key"
    llm_upstream_base: str = "http://127.0.0.1:8001"
    llm_upstream_timeout: float = 20.0
    llm_stream_timeout: float = 120.0

    # ---- OpenRAG 对接（v1.4.4 R-380，JWT 门禁 + 无上游认证转发） ----
    rag_upstream_base: str = "http://127.0.0.1:8010"
    rag_upstream_timeout: float = 20.0
    rag_stream_timeout: float = 120.0

    # ---- DPS 对接（v1.4.5 R-381，JWT 门禁 + 身份头注入转发） ----
    dps_upstream_base: str = "http://127.0.0.1:8030"
    dps_upstream_timeout: float = 20.0
    dps_default_org_id: str = ""
    dps_default_tenant_id: str = ""
    # 组织/租户映射表（JSON：OpenBase 值 → DPS 值），命中则转换
    dps_org_map: str = ""
    dps_tenant_map: str = ""

    # ---- 模块启停（内部状态） ----
    _enabled_modules: set[str] = set()

    def enable_module(self, name: str) -> None:
        """启用模块.

        Args:
            name: 模块名（如 "auth"、"tenant"）。

        Raises:
            ValueError: 模块名未注册。
        """
        if name not in AVAILABLE_MODULES:
            raise ValueError(
                f"未知模块: {name}，可用模块: {', '.join(AVAILABLE_MODULES)}"
            )
        self._enabled_modules.add(name)

    def disable_module(self, name: str) -> None:
        """禁用模块.

        Args:
            name: 模块名。
        """
        self._enabled_modules.discard(name)

    def is_enabled(self, name: str) -> bool:
        """检查模块是否已启用."""
        return name in self._enabled_modules

    @property
    def enabled_modules(self) -> list[str]:
        """已启用模块列表（保持注册顺序）. """
        return [m for m in AVAILABLE_MODULES if m in self._enabled_modules]


_settings: Settings | None = None


def get_settings() -> Settings:
    """获取全局 Settings 单例."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
