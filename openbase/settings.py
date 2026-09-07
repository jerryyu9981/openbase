"""OpenBase 配置驱动设置.

提供 Settings 类：模块启停（enable_module/disable_module）、
全局配置（数据库/Redis/鉴权/可观测）与 init_app 装配入口。

数据库配置读取优先级：
1. OPENBASE_DB_URL 环境变量（openbase 自有配置）
2. POSTGRES_URL 环境变量（共享基础设施 .env.shared-infra）
3. 默认值（本地开发）
"""

from __future__ import annotations

import logging
import os

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("openbase.settings")

# 已知弱 JWT 密钥（占位/演示值；生产模式一律拒绝）
WEAK_JWT_SECRETS = frozenset({"", "change-me-in-production", "test-jwt-secret-for-v680"})

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
    # U1 统一身份收口（RA-01/OB-1）：Principal 主体面 + agent 密钥面（identity 路由）
    "identity",
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
    # 运行环境：development | production（production 强制强 JWT 密钥，弱值启动即拒绝）
    env: str = "development"

    # ---- 数据库 ----
    db_url: str = _resolve_db_url()
    db_echo: bool = False
    # openbase schema 名（共享库内隔离）
    db_schema: str = "openbase"

    # ---- Redis ----
    redis_url: str = _resolve_redis_url()

    # ---- 鉴权 ----
    # 无内置弱默认（v1.7.0）：本地由 .env 提供随机密钥；production 强制强密钥否则启动失败。
    # 轮换宽限：jwt_secret_previous 仅参与验签（旧 token 过渡期有效），签发始终用 jwt_secret。
    jwt_secret: str = ""
    jwt_secret_previous: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_seconds: int = 7200
    refresh_expire_seconds: int = 604800
    # U1 T3（K04，方案 a token 版本号）：token 版本强校验开关（两段式发布第二段，
    # 设计草案 §5.1/§12.1 风险 1/§6.2）。默认 False：版本强校验关闭，存量 v0 / 落后
    # tvn 过渡窗口不误杀；每请求主体状态校验不依赖本开关（默认即生效）。第二段置 True。
    enforce_token_version: bool = False
    # bcrypt 成本因子（默认 12 ≈ 400-600ms；并发敏感场景可调低至 10 ≈ 200ms）
    bcrypt_rounds: int = 12
    # MCP 服务级 API Key（逗号分隔；生产环境必须覆盖默认值）
    mcp_api_keys: str = "dev-mcp-key"

    # ---- OIDC 统一认证（OB-AUTH-OIDC，默认关闭，不影响现有本地认证） ----
    oidc_enabled: bool = False
    oidc_discovery_url: str = ""  # IdP discovery 端点（.well-known/openid-configuration）
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_redirect_uri: str = ""  # 如 http://<host>:8000/api/v1/auth/oidc/callback
    oidc_scopes: str = "openid profile email"  # 空格分隔
    oidc_claim_role: str = "roles"  # IdP ID Token 中角色 claim 名
    oidc_default_tenant: str = "default"  # 未映射租户时的默认值
    oidc_profile: str = "generic"  # claims 适配 profile：generic（平铺 roles）| keycloak（realm_access/resource_access 嵌套聚合）
    oidc_keycloak_client_roles: bool = True  # keycloak：聚合 resource_access.<client_id>.roles（False 仅 realm 角色）
    oidc_frontend_redirect: str = "/auth/oidc/callback"  # 浏览器授权成功后 302 前端回调路由（同源，fragment 携带令牌）

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

    # ---- OpenRAG 对接（v1.4.4 R-380，JWT 门禁 + 上游认证转发） ----
    rag_upstream_base: str = "http://127.0.0.1:8010"
    rag_upstream_timeout: float = 20.0
    rag_stream_timeout: float = 120.0
    # 任务书 M1：OpenRAG 服务级 API Key（X-API-Key，与 OPENRAG_API_SERVICE_API_KEY 同密钥），
    # rag-proxy 转发时注入；空则不注入（向后兼容）
    rag_api_key: str = "openbase-rag-gw-key-20260901"

    # ---- DPS 对接（v1.4.5 R-381，JWT 门禁 + 身份头注入转发） ----
    # P0-3 端口对齐（评审 Q5）：默认对齐 DPS 源码 api_port=8000（DPS src/config.py
    # API_PORT 默认 8000，main.py REST 入口；rest_api.app/MCP 部署入口为 8013）。
    # 真实部署（如本地编排将 DPS 置于 8030 / 容器 8013）须经
    # OPENBASE_DPS_UPSTREAM_BASE 环境变量显式覆盖，避免端口错配。
    dps_upstream_base: str = "http://127.0.0.1:8000"
    dps_upstream_timeout: float = 20.0
    # 上游健康探活（P0-3）：首次 dps-proxy 请求前及此后每 dps_health_interval 秒
    # 对 {dps_upstream_base}/health 探活一次；失败仅 WARN 降级提示不阻断转发。
    # 关闭（False）仅用于测试隔离或上游无 /health 的场景。
    dps_health_check_enabled: bool = True
    dps_health_interval: float = 30.0
    # P6（DPS 对接任务书）：连续转发失败达到该次数后返回 503 显式降级提示
    # （fail-open 保持：阈值内仍按既有 SYS_502 语义转发尝试；探活恢复自动归零）。
    dps_degrade_threshold: int = 3
    dps_default_org_id: str = ""
    dps_default_tenant_id: str = ""
    # 组织/租户映射表（JSON：OpenBase 值 → DPS 值），命中则转换
    dps_org_map: str = ""
    dps_tenant_map: str = ""

    # ---- P2-1 协议头与信任链（K02/K03；设计草案 §3.3/§5.4/§11.1）----
    # 受信来源白名单（逗号分隔，如 "openbase-dps-proxy,openbase-llm-proxy,..."）；
    # 默认空 = 不信任任何外部携带的身份头（OpenBase 自身出口不在其列）。
    trusted_proxy_sources: str = ""
    # 入站头收口分段开关（§5.4 两段式）：过渡期仅审计标注不采信（默认）；
    # 剥离期物理剥除非受信来源身份头；强校验期非受信带头 → 403。
    strip_inbound_identity_headers: bool = False
    enforce_inbound_identity_headers: bool = False
    # 出站严格模式（出站头与规范不符 → 502/审计；默认 false，常规补头始终开启）
    enforce_proxy_identity_headers: bool = False
    # X-Org-ID 别名强模式（org ≠ tenant → 403；批次 2/T7 接线）
    enforce_org_alias: bool = False
    # K03 过渡豁免白名单清单（JSON 数组：{id, system, method, path_pattern, reason,
    # owner, audit, expires_at}）；白名单外匿名业务写一律拒绝（D-V6）。
    k03_bypass_whitelist: str = ""
    # OB-12 角色互译表 JSON（schema_version/anchors/systems；批次 2/T6 消费）
    role_intertranslate: str = ""
    # 通用 proxy ob_k_ 服务 Key「服务账号主体映射」JSON 数组（P2-1 §3.7 例 3/§5.2 D-V6）：
    # 每条 {name 或 name_prefix, subject_id, tenant_code, role}；ob_k_ 凭据命中映射 →
    # 出站以服务账号主体上下文补头（X-User-ID=subject_id 等）；未绑定 → 维持仅来源标注
    # （不构造伪主体身份头）。业务写仍受 k03_bypass_whitelist fail-closed 约束（D-V6）。
    service_account_subject_map: str = ""
    # dps org/tenant code→UUID 登记式基线 JSON（批次 2/T7 消费）
    dps_code_map: str = ""

    # ---- 模块启停（内部状态） ----
    _enabled_modules: set[str] = set()

    @model_validator(mode="after")
    def _validate_jwt_secret(self) -> Settings:
        """JWT 密钥安全校验（v1.7.0）.

        production：必须为强随机密钥（≥32 字符且非已知弱值），否则启动失败（fail-fast）；
        development：弱值仅 WARN（便于本地演示，.env 仍建议随机密钥）。
        """
        secret = self.jwt_secret or ""
        is_weak = len(secret) < 32 or secret in WEAK_JWT_SECRETS
        if self.env == "production":
            if is_weak:
                raise ValueError(
                    "OPENBASE_JWT_SECRET 必须为强随机密钥（≥32 字符，禁止占位/演示值）；"
                    "可用 python scripts/gen_jwt_secret.py 生成"
                )
        elif is_weak and secret:
            logger.warning(
                "development 模式使用弱/演示 JWT 密钥，仅限本地联调（生产将拒绝启动）"
            )
        elif not secret:
            logger.warning(
                "OPENBASE_JWT_SECRET 未配置：签发将失败（fail-closed）；请配置随机密钥"
            )
        return self

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

    # ---- P2-1 协议头/信任链辅助解析（§3.3/§5.2）----

    @property
    def trusted_proxy_sources_list(self) -> list[str]:
        """受信来源白名单解析（逗号分隔 → 去空列表）."""
        return [item.strip() for item in (self.trusted_proxy_sources or "").split(",") if item.strip()]

    def parse_k03_bypass_whitelist(self) -> list[dict]:
        """K03 过渡豁免白名单解析（JSON 数组；非法/空 → 空表）.

        Returns:
            白名单条目 dict 列表。非法 JSON 记 WARN 并按空表处理（fail-closed：
            白名单外匿名业务写一律拒绝，宁可 403 也不放宽）。
        """
        raw = self.k03_bypass_whitelist or ""
        if not raw:
            return []
        try:
            import json

            data = json.loads(raw)
        except (TypeError, ValueError):
            logger.warning(
                "k03_bypass_whitelist invalid JSON; treated as empty (fail-closed)"
            )
            return []
        if not isinstance(data, list):
            logger.warning(
                "k03_bypass_whitelist must be a JSON array; treated as empty (fail-closed)"
            )
            return []
        return [item for item in data if isinstance(item, dict)]

    def parse_service_account_subject_map(self) -> list[dict]:
        """ob_k_ 服务账号主体映射解析（JSON 数组；非法/空 → 空表）.

        条目：{name 或 name_prefix, subject_id, tenant_code, role}。
        非法 JSON/结构记 WARN 并按空表处理——出站回落「仅来源标注」语义，不构造伪主体。
        """
        raw = self.service_account_subject_map or ""
        if not raw:
            return []
        try:
            import json

            data = json.loads(raw)
        except (TypeError, ValueError):
            logger.warning(
                "service_account_subject_map invalid JSON; treated as empty"
            )
            return []
        if not isinstance(data, list):
            logger.warning(
                "service_account_subject_map must be a JSON array; treated as empty"
            )
            return []
        return [item for item in data if isinstance(item, dict)]


_settings: Settings | None = None


def get_settings() -> Settings:
    """获取全局 Settings 单例."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
