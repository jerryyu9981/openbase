"""OpenBase 配置驱动设置.

提供 Settings 类：模块启停（enable_module/disable_module）、
全局配置（数据库/Redis/鉴权/可观测）与 init_app 装配入口。

数据库配置读取优先级：
1. OPENBASE_DB_URL 环境变量（openbase 自有配置）
2. POSTGRES_URL 环境变量（共享基础设施 .env.shared-infra）
3. 默认值（本地开发）
"""

from __future__ import annotations

import json
import logging
import os

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("openbase.settings")

# 已知弱 JWT 密钥（占位/演示值；生产模式一律拒绝）
WEAK_JWT_SECRETS = frozenset({"", "change-me-in-production", "test-jwt-secret-for-v680"})

# 各下游目标的**保留租户码**集合（R-387 统一码空间收口：按目标登记，单一事实源）。
# 只有声明了「保留码」语义的下游才非空；未声明者为空集（该目标接受任何非空码）。
# - rag：OpenRAG 受信入站对保留码返回 400 `BIZ_RESERVED_TENANT_CODE_COLLISION`
#   （出处：doc/test/evidence/v147/def005-multiprobe-20260920.json 的 detail.reserved_codes）。
# - memory：OpenMemory 按**组织策略** fail-closed，仅接受其**已登记组织码**。
#   实测（2026-10-08 修复前）：仅登记 `default`，`tenant-1`/`tenant-2` → 403
#   「组织不存在或未配置策略」。**已由 C1-a 跨仓修复**（编排器显式登记
#   `OPENMEMORY_RBAC__ORG_POLICIES`），故兜底码已切换为 `tenant-1`（统一空间终态）。
#   依据：doc/test/evidence/manual/r387-memory-org-policy-20261008.json（修复前证据）。
# - llm / dps：未声明保留码语义；DPS 另有登记式映射 `dps_code_map`（目标空间码值）。
OUTBOUND_RESERVED_TENANT_CODES_BY_TARGET: dict[str, frozenset[str]] = {
    "rag": frozenset({"default", "openrag-local"}),
    "memory": frozenset(),
    "llm": frozenset(),
    "dps": frozenset(),
}

# RAG 保留码别名（既有引用点兼容；指向登记表，避免两处漂移）
RAG_RESERVED_TENANT_CODES: frozenset[str] = OUTBOUND_RESERVED_TENANT_CODES_BY_TARGET["rag"]

# 各目标出站租户码的**内置登记基线**（A 批 A1/A2：码空间登记的唯一入口）。
# 语义：键存在 = 该目标有兜底码（须非空且非保留码）；键缺席 = 该目标不进兜底
# （主体无租户声明时省略 X-Tenant-ID，保持既有语义，如 llm/dps）。
# 覆盖方式：`OPENBASE_PROXY_CODE_MAP`（JSON，见 parse_proxy_code_map）。
BUILTIN_DEFAULT_TENANT_CODE_BY_TARGET: dict[str, str] = {
    "rag": "tenant-1",
    "memory": "tenant-1",
}


def parse_proxy_code_map(raw: str | None) -> dict[str, dict[str, object]]:
    """解析 `OPENBASE_PROXY_CODE_MAP` 覆盖表（纯函数，供校验与运行期共用）.

    Schema:
        {"schema_version": 1,
         "source_of_truth": "openbase.tenants.code",
         "targets": {"<target>": {"reserved_codes": [...], "default_tenant_code": "..."}}}

    语义：`targets.<t>` 的字段**按字段覆盖**内置登记基线；`default_tenant_code` 显式出现
    即表示该目标进兜底（须非空且非保留码）。

    Args:
        raw: JSON 字符串；空/非法 → 返回空覆盖表（由调用方按 fail-closed 决定是否报错）。

    Returns:
        {target: {"reserved_codes"?: frozenset[str], "default_tenant_code"?: str}}

    Raises:
        ValueError: JSON 非法、结构不符或字段类型错误（fail-fast，禁静默降级）。
    """
    text = (raw or "").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"OPENBASE_PROXY_CODE_MAP 不是合法 JSON：{exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("OPENBASE_PROXY_CODE_MAP 顶层必须是对象")
    targets = parsed.get("targets", {})
    if not isinstance(targets, dict):
        raise ValueError("OPENBASE_PROXY_CODE_MAP.targets 必须是对象")
    result: dict[str, dict[str, object]] = {}
    for target, entry in targets.items():
        if not isinstance(entry, dict):
            raise ValueError(f"OPENBASE_PROXY_CODE_MAP.targets.{target} 必须是对象")
        normalized: dict[str, object] = {}
        if "reserved_codes" in entry:
            reserved = entry["reserved_codes"]
            if not isinstance(reserved, list) or not all(isinstance(c, str) for c in reserved):
                raise ValueError(
                    f"OPENBASE_PROXY_CODE_MAP.targets.{target}.reserved_codes 必须是字符串数组"
                )
            normalized["reserved_codes"] = frozenset(reserved)
        if "default_tenant_code" in entry:
            code = entry["default_tenant_code"]
            if not isinstance(code, str):
                raise ValueError(
                    f"OPENBASE_PROXY_CODE_MAP.targets.{target}.default_tenant_code 必须是字符串"
                )
            normalized["default_tenant_code"] = code
        result[str(target)] = normalized
    return result


def resolve_target_code_space(raw: str | None) -> dict[str, dict[str, object]]:
    """按内置基线 + 覆盖表解析各目标码空间（纯函数）.

    Returns:
        {target: {"reserved_codes": frozenset[str], "default_tenant_code": str | None}}
    """
    overrides = parse_proxy_code_map(raw)
    resolved: dict[str, dict[str, object]] = {}
    for target, reserved in OUTBOUND_RESERVED_TENANT_CODES_BY_TARGET.items():
        resolved[target] = {
            "reserved_codes": reserved,
            "default_tenant_code": BUILTIN_DEFAULT_TENANT_CODE_BY_TARGET.get(target),
        }
    for target, override in overrides.items():
        entry = resolved.setdefault(
            target, {"reserved_codes": frozenset(), "default_tenant_code": None}
        )
        entry.update(override)
    return resolved


def validate_target_code_space(resolved: dict[str, dict[str, object]]) -> None:
    """校验解析后的码空间登记（fail-fast）；供 Settings 校验与运行期二次防线共用.

    Raises:
        ValueError: 兜底码出现但为空，或命中该目标保留码。
    """
    for target, entry in resolved.items():
        code = entry.get("default_tenant_code")
        if code is None:
            continue  # 该目标不设兜底（既有语义）
        text = str(code).strip()
        if not text:
            raise ValueError(
                f"目标 {target} 的 default_tenant_code 不得为空（出现即表示进兜底）"
            )
        reserved = entry.get("reserved_codes") or frozenset()
        if text in reserved:
            raise ValueError(
                f"目标 {target} 的 default_tenant_code {text!r} 命中其保留码 "
                f"{sorted(reserved)}；请改用该目标可接受的码值"
            )

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
    # 批 2 C-10：人工测试结论记录（受权 API test:record）
    "testing",
    # v1.4.6：日志中心（四源统一检索，受权 log:read）
    "logs",
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
    #
    # B4 安全收紧（2026-10-08，人工裁定选项 A：fail-closed + 显式白名单）：
    # **production 环境必须为 True**，否则拒绝启动（照弱 JWT 密钥启动拒绝风格，
    # 见 `_validate_production_token_version_enforcement`）；非生产可配置，默认维持 False。
    enforce_token_version: bool = False
    # B4 主体验证 DB 降级**显式白名单**（默认空 = 不放行任何主体）。
    # 语义：DB 不可达（无法证明主体状态）时默认**拒绝**（503 SYS_SOURCE_UNAVAILABLE）；
    # 仅本名单内**显式列名**的本地主体（users.id 的十进制字符串，逗号分隔）可在此情形
    # 放行（窄口径应急通道）；命中必留痕（结构化日志 + 审计标注）。
    # 取值约束（fail-closed）：仅接受十进制主体 id；含通配/前缀/非数字项一律**不作为命中**
    # （视同未列名 → 拒绝），并在解析时 WARN 提示。
    principal_db_degraded_allowlist: str = ""
    # B4 环境门控（2026-10-09 修复）：主体验证「DB 不可达」降级策略**显式覆盖**。
    # 取值：""（默认 = 按环境推导）| "reject"（fail-closed 拒绝 503）| "allow"（兼容放行）。
    # 推导规则（本字段为空时）：env == "production" → reject（安全口径不变）；
    # 其余（development/test 等）→ allow（兼容沙箱，**必 WARN + 留痕**，不得静默）。
    # 约束（fail-fast）：production 下**不得**为 "allow"（避免误配回退 fail-open），
    # 否则拒绝启动（见 `_validate_principal_db_degraded_policy`）。
    principal_db_degraded_policy: str = ""
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
    # C1-a 终态（2026-10-08）：未映射租户的默认码统一为 **非保留码** `tenant-1`
    # （与 `BUILTIN_DEFAULT_TENANT_CODE_BY_TARGET` 及各目标可接受码空间一致）。
    # 原为保留码 `default`：对 OpenRAG 是禁用保留码（受信入站 400），且与 memory 目标的
    # 已登记组织码不一致，导致身份空间与目标空间口径分裂。切换前提（OpenMemory 已登记
    # `tenant-1`）已由 C1-a 跨仓修复满足。
    oidc_default_tenant: str = "tenant-1"  # 未映射租户时的默认值
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

    # ---- 响应级观测三开关（批 4 C-19；方案 §11.2 红线 / §11.3）----
    # 默认全关：未设置或为 0 时**零采集、零落盘**（响应摘要字段不出现）；
    # 仅联调/人工测试窗口显式开启，且开启后摘要必经 core/mask.mask_sensitive 脱敏；
    # **生产永久关闭**（env=production 时开关不生效，见 capture_response_enabled）。
    capture_response: bool = False
    capture_upstream: bool = False
    # 允许清单（逗号分隔字段路径，如 "error.code,error.message"）：命中路径保留原值；
    # 默认空 = 全脱敏（默认只留结构化键名与 digest，隐私域整体遮蔽）。
    capture_field_allowlist: str = ""

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
    # 本轮迭代（智能体对话全链路）修正：非流式上游预算 20.0s → 120.0s。
    # 依据：OpenLLM 在 mode=auto 下按真实契约**同步**完成「画像拉取 + 记忆检索 +
    # 知识库检索 + 上下文装配 + LLM 推理 + 三路回执」，实测端到端 19~27s
    # （单「LLM 推理」步骤即约 25.7s；时间线证据见 doc/test/evidence/agent-e2e/）。
    # 20.0s 预算下 OpenBase 先于上游返回 → 抛 SYS_502「upstream unreachable」，
    # 即把**上游正常但较慢**的响应误判为不可达（实测 23740ms 触发）。
    # 非流式与流式共用同一「一次会话总预算」（120.0s）；代理自身开销目标
    # （P95 ≤ 500ms，不含上游处理）不变，本项仅放宽容忍窗口。
    llm_upstream_timeout: float = 120.0
    llm_stream_timeout: float = 120.0

    # ---- OpenRAG 对接（v1.4.4 R-380，JWT 门禁 + 上游认证转发） ----
    rag_upstream_base: str = "http://127.0.0.1:8010"
    rag_upstream_timeout: float = 20.0
    rag_stream_timeout: float = 120.0
    # 任务书 M1：OpenRAG 服务级 API Key（X-API-Key，与 OPENRAG_API_SERVICE_API_KEY 同密钥），
    # rag-proxy 转发时注入；空则不注入（向后兼容）
    rag_api_key: str = "openbase-rag-gw-key-20260901"
    # DEF-BE-147-005（v1.4.7）引入的 rag-proxy 身份头注入策略开关。
    #   True （默认）＝维持 P2-1 四维身份透传（注入四头 + 来源 + 请求 id）；
    #   False       ＝**不注入身份头**，仅 `X-API-Key` + `X-Proxy-Source` + `X-Request-Id`。
    # R-387 收口（2026-10-08）后本开关**仅为应急回滚杠杆**，默认 True 不再被联调环境关闭：
    # 出站头矩阵实测证明根因是**租户码落在 OpenRAG 保留码上或缺省**（而非「注入」本身）——
    # 受信入站 + 非保留码时读、写同时 200（见下方 `proxy_code_map` 登记入口）。
    rag_inject_identity_headers: bool = True

    # ---- A 批 A1/A2：出站租户码空间**统一登记入口**（替代原散落的 rag_/memory_ 兜底码字段） ----
    # 内置登记基线见模块常量 `OUTBOUND_RESERVED_TENANT_CODES_BY_TARGET` 与
    # `BUILTIN_DEFAULT_TENANT_CODE_BY_TARGET`（rag=tenant-1、memory=default）；
    # 本字段用于**覆盖**：
    #   {"schema_version": 1, "source_of_truth": "openbase.tenants.code",
    #    "targets": {"<target>": {"reserved_codes": [...], "default_tenant_code": "..."}}}
    # 约束（启动即校验，fail-fast）：非合法 JSON/结构不符 → 拒绝启动；`default_tenant_code`
    # 出现即须非空且**不得命中该目标保留码**。
    # 背景见《OpenBase-R387-跨域租户码对齐设计与收口实施记录》§11 与
    # 《OpenBase-自研系统多租户与授权集成总体完善方案》§4.2 L3 码空间登记层。
    proxy_code_map: str = ""

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

    @model_validator(mode="after")
    def _validate_production_token_version_enforcement(self) -> Settings:
        """生产门禁（B4 安全收紧）：production 下强制启用 token 吊销强校验.

        语义（人工裁定选项 A）：生产环境 `enforce_token_version` 必须为 True，
        否则**拒绝启动**（照 `_validate_jwt_secret` 弱密钥启动拒绝风格，fail-fast）。
        理由：token 版本（`users.token_version` 递增）是撤销存量令牌的即时手段；
        生产若处于默认关，吊销将静默不生效 —— 属必须前置于启动的门禁缺陷。

        Raises:
            ValueError: env == "production" 且未启用 enforce_token_version。
        """
        if self.env == "production" and not self.enforce_token_version:
            raise ValueError(
                "生产环境必须启用 OPENBASE_ENFORCE_TOKEN_VERSION=true（token 吊销强校验），"
                "否则拒绝启动（fail-closed）；非生产环境可维持默认关闭"
            )
        return self

    @model_validator(mode="after")
    def _validate_principal_db_degraded_policy(self) -> Settings:
        """主体验证 DB 降级策略校验（B4 环境门控，2026-10-09 修复）.

        语义：`principal_db_degraded_policy` 取值仅支持 ""（按环境推导）/ "reject" / "allow"；
        非法取值 → 拒绝启动（fail-fast，禁静默降级）。生产环境**不得**设为 "allow"——该配置会
        使 DB 不可达时回退 fail-open，属必须前置于启动的安全门禁缺陷（照
        `_validate_production_token_version_enforcement` 风格）。

        Raises:
            ValueError: 取值非法，或 env == "production" 且 policy == "allow"。
        """
        policy = (self.principal_db_degraded_policy or "").strip().lower()
        if policy not in ("", "reject", "allow"):
            raise ValueError(
                "OPENBASE_PRINCIPAL_DB_DEGRADED_POLICY 取值非法（仅支持 reject/allow/留空）："
                f"{self.principal_db_degraded_policy!r}"
            )
        if self.env == "production" and policy == "allow":
            raise ValueError(
                "生产环境不得将 OPENBASE_PRINCIPAL_DB_DEGRADED_POLICY 设为 allow"
                "（会使 DB 不可达时回退 fail-open）；生产须为 reject 或留空（按环境推导为 reject）"
            )
        return self

    @model_validator(mode="after")
    def _validate_outbound_tenant_alignment(self) -> Settings:
        """出站租户码空间登记校验（fail-fast，A 批 A1/A2）.

        校验 `proxy_code_map` 覆盖表（结构 + 兜底码合法性），并把内置登记基线一并纳入
        校验；任一目标的兜底码为空或命中**该目标**保留码 → 拒绝启动，避免退化为
        「调用期才 400/403」的隐性故障。

        Raises:
            ValueError: 覆盖表非法，或某目标兜底码为空/命中该目标保留码。
        """
        resolved = resolve_target_code_space(self.proxy_code_map)
        validate_target_code_space(resolved)
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

    # ---- 响应级观测三开关（批 4 C-19）辅助 ----

    @property
    def capture_field_allowlist_list(self) -> list[str]:
        """允许清单解析（逗号分隔 → 去空列表；默认空 = 全脱敏）."""
        return [
            item.strip()
            for item in (self.capture_field_allowlist or "").split(",")
            if item.strip()
        ]

    @property
    def capture_response_enabled(self) -> bool:
        """网关响应体采集是否**实际**生效（红线 4：生产永久关闭）."""
        return self.capture_response and self.env != "production"

    @property
    def capture_upstream_enabled(self) -> bool:
        """上游响应体采集是否**实际**生效（红线 4：生产永久关闭）."""
        return self.capture_upstream and self.env != "production"

    # ---- P2-1 协议头/信任链辅助解析（§3.3/§5.2）----

    @property
    def trusted_proxy_sources_list(self) -> list[str]:
        """受信来源白名单解析（逗号分隔 → 去空列表）."""
        return [item.strip() for item in (self.trusted_proxy_sources or "").split(",") if item.strip()]

    @property
    def principal_db_degraded_allowlist_set(self) -> frozenset[str]:
        """主体验证 DB 降级放行白名单解析（逗号分隔 → 仅十进制主体 id 集合）.

        取值约束（fail-closed，B4 安全收紧）：仅接受十进制主体 id（`users.id` 的字符串
        形态）；**禁止通配/前缀模糊匹配** —— 非数字/超范围项一律**丢弃**（不入集合），
        从而在该情形**不作为命中**（等价于拒绝）。非法项存在时记 WARN（便于运维定位）。
        """
        allowed: set[str] = set()
        rejected: list[str] = []
        for item in (self.principal_db_degraded_allowlist or "").split(","):
            token = item.strip()
            if not token:
                continue
            if token.isdigit():
                allowed.add(token)
            else:
                rejected.append(token)
        if rejected:
            logger.warning(
                "principal_db_degraded_allowlist 含非法项（非十进制主体 id，已忽略=fail-closed）",
                extra={"rejected": rejected},
            )
        return frozenset(allowed)

    @property
    def principal_db_degraded_policy_source(self) -> str:
        """DB 降级策略来源（显式 policy 优先；为空按环境推导）.

        Returns:
            "explicit_reject" | "explicit_allow" | "env_production" | "env_nonproduction"。
        """
        policy = (self.principal_db_degraded_policy or "").strip().lower()
        if policy == "reject":
            return "explicit_reject"
        if policy == "allow":
            return "explicit_allow"
        return "env_production" if self.env == "production" else "env_nonproduction"

    @property
    def principal_db_degraded_reject(self) -> bool:
        """主体验证「DB 不可达」的有效裁定：True = fail-closed 拒绝，False = 兼容放行.

        显式 ``principal_db_degraded_policy`` 优先；为空时按环境推导（production → 拒绝，
        其余 → 放行）。放行路径仍须 WARN + 留痕（由 verification 模块保证，不得静默）。
        """
        return self.principal_db_degraded_policy_source in (
            "explicit_reject",
            "env_production",
        )

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
        entries = [item for item in data if isinstance(item, dict)]
        # C3 影子期（R1 过渡段，2026-10-09）：登记缺统一契约必填字段的条目，**不改变放行行为**。
        # 契约见 `config/identity_exemptions.json`（必填 target/ticket/approver/expires_at）；
        # 退出条件：影子期无「缺失 ticket/approver 但实际依赖豁免」的调用方 → 开启强制段（fail-closed）。
        for entry in entries:
            missing = [
                field
                for field in ("ticket", "approver", "expires_at")
                if not str(entry.get(field) or "").strip()
            ]
            if missing:
                logger.warning(
                    "k03 bypass exemption missing unified-contract fields "
                    "(shadow phase, still effective)",
                    extra={"exemption_id": entry.get("id"), "missing_fields": missing},
                )
        return entries

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
        entries = [item for item in data if isinstance(item, dict)]
        # C3 影子期（R1 过渡段，2026-10-09）：登记缺统一契约必填字段的条目，**不改变放行行为**。
        # 契约见 `config/identity_exemptions.json`（必填 target/ticket/approver/expires_at）；
        # 退出条件：影子期无「缺失 ticket/approver 但实际依赖豁免」的调用方 → 开启强制段（fail-closed）。
        for entry in entries:
            missing = [
                field
                for field in ("ticket", "approver", "expires_at")
                if not str(entry.get(field) or "").strip()
            ]
            if missing:
                logger.warning(
                    "k03 bypass exemption missing unified-contract fields "
                    "(shadow phase, still effective)",
                    extra={"exemption_id": entry.get("id"), "missing_fields": missing},
                )
        return entries

    # ---- OB-8 dps code→UUID 登记式基线（§7.2，批次 3/T7）----

    def dps_code_map_entries(self) -> list[dict]:
        """登记式基线 entries（settings.dps_code_map JSON 解析，非法 → 空表）."""
        from openbase.modules.protocol_headers.dps_code_map import parse_dps_code_map

        data = parse_dps_code_map(self.dps_code_map)
        return [entry for entry in data.get("entries", []) if isinstance(entry, dict)]

    def deprecated_dps_defaults(self) -> dict[str, str]:
        """已配置的 deprecated dps_default_*（§7.2：verify-env WARN 数据源）."""
        deprecated: dict[str, str] = {}
        if self.dps_default_org_id:
            deprecated["dps_default_org_id"] = self.dps_default_org_id
        if self.dps_default_tenant_id:
            deprecated["dps_default_tenant_id"] = self.dps_default_tenant_id
        return deprecated

    def dps_defaults_deprecation_warnings(self) -> list[str]:
        """dps_default_* deprecated 提示文本（登记式基线替换，T7-6）."""
        return [
            f"dps_default_* deprecated (OB-8): {name}={value} configured; "
            "register tenant code in dps_code_map instead"
            for name, value in self.deprecated_dps_defaults().items()
        ]


_settings: Settings | None = None


def get_settings() -> Settings:
    """获取全局 Settings 单例."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
