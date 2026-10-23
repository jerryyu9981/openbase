/**
 * 平台管理四域路由（v1.4.6 IA 重构，ADR-146-05/08）
 *
 * 统一前缀 `/platform/**`（作为 `/` AppLayout 的子路由，路径相对 `/`）。
 * 权限口径（§3.2 三处一致）：`meta.permission` 与后端权限码同名。
 *  - `log:read` / `module:manage` / `test:record` 显式声明（菜单可见性 + 守卫同源）；
 *  - 2026-10-14（走查 F3 收口）：为「页内接口受后端权限码管控」的平台页补声明——
 *    `tenant:view`（租户管理）、`users:view`（组织/团队/用户、用户管理）、
 *    `auth:api-keys:view`（API 密钥）、`memory:manage`（记忆管理席位）——
 *    避免「菜单可见但进入后接口 403」割裂；仍无独立权限码的页（角色/工作空间/注册找回/
 *    全局配置/可观测各页/开发者资源等）沿用既有「仅登录可见」口径。
 * `GenericPage` 承载的占位路由按 UI 设计 §9.3 R2/R3：**复用** openllm 单份实现（不复制）。
 */
import type { RouteRecordRaw } from 'vue-router'

const GenericPage = () => import('@/pages/platform/governance/GenericPage.vue')

/** 平台管理 · 身份与权限域 */
export const identityRoutes: RouteRecordRaw[] = [
  { path: 'platform/identity/tenants', name: 'platform-identity-tenants', component: () => import('@/pages/platform/identity/SystemTenants.vue'), meta: { title: '租户管理', icon: 'OfficeBuilding', permission: 'tenant:view' } },
  { path: 'platform/identity/roles', name: 'platform-identity-roles', component: () => import('@/pages/platform/identity/RolesView.vue'), meta: { title: '角色与权限', icon: 'User' } },
  { path: 'platform/identity/org', name: 'platform-identity-org', component: () => import('@/pages/platform/identity/OrgTeamsUsersView.vue'), meta: { title: '组织/团队/用户', icon: 'OfficeBuilding', permission: 'users:view' } },
  { path: 'platform/identity/workspaces', name: 'platform-identity-workspaces', component: () => import('@/pages/platform/identity/WorkspacesView.vue'), meta: { title: '工作空间', icon: 'Grid' } },
  { path: 'platform/identity/auth-ext', name: 'platform-identity-auth-ext', component: () => import('@/pages/platform/identity/AuthExt.vue'), meta: { title: '注册/找回密码', icon: 'Key' } },
  { path: 'platform/identity/users', name: 'platform-identity-users', component: () => import('@/pages/platform/identity/UsersView.vue'), meta: { title: '用户管理', icon: 'User', permission: 'users:view' } },
  { path: 'platform/identity/memory-admin', name: 'platform-identity-memory-admin', component: () => import('@/pages/platform/identity/MemoryAdminView.vue'), meta: { title: '记忆管理席位', icon: 'Setting', permission: 'memory:manage', dependsOn: 'memory' } },
  // v1.4.11：DPS 权限管理从画像模块上收（公共域统一治理）
  { path: 'platform/identity/dps-permissions', name: 'platform-identity-dps-permissions', component: () => import('@/pages/platform/identity/DpsPermissionView.vue'), meta: { title: '画像数据权限', icon: 'User', dependsOn: 'portrait' } },
]

/** 平台管理 · 平台配置与密钥域 */
export const configRoutes: RouteRecordRaw[] = [
  { path: 'platform/config/general', name: 'platform-config-general', component: () => import('@/pages/platform/config/ConfigManageView.vue'), meta: { title: '全局配置', icon: 'Setting' } },
  { path: 'platform/config/modules', name: 'platform-config-modules', component: () => import('@/pages/platform/config/ModuleSwitchView.vue'), meta: { title: '模块开关', icon: 'Grid', permission: 'module:manage' } },
  { path: 'platform/config/api-keys', name: 'platform-config-api-keys', component: () => import('@/pages/platform/config/ApiKeys.vue'), meta: { title: 'API 密钥', icon: 'Key', permission: 'auth:api-keys:view' } },
  // v1.4.11：DPS 限流管理从画像模块上收（公共域统一治理）
  { path: 'platform/config/rate-limits', name: 'platform-config-rate-limits', component: () => import('@/pages/platform/config/DpsRateLimitView.vue'), meta: { title: '画像接口限流', icon: 'Operation', dependsOn: 'portrait' } },
]

/** 平台管理 · 可观测与审计域 */
export const observabilityRoutes: RouteRecordRaw[] = [
  { path: 'platform/observability/logs', name: 'platform-observability-logs', component: () => import('@/pages/platform/observability/LogsView.vue'), meta: { title: '日志中心', icon: 'Document', permission: 'log:read' } },
  { path: 'platform/observability/test-records', name: 'platform-observability-test-records', component: () => import('@/pages/platform/observability/SystemTestRecords.vue'), meta: { title: '测试记录', icon: 'Memo', permission: 'test:record' } },
  { path: 'platform/observability/monitoring', name: 'platform-observability-monitoring', component: () => import('@/pages/platform/observability/Monitoring.vue'), meta: { title: '统一监控', icon: 'Monitor' } },
  { path: 'platform/observability/monitoring/costs', name: 'platform-observability-monitoring-costs', component: () => import('@/pages/platform/observability/Costs.vue'), meta: { title: '成本分析', icon: 'TrendCharts' } },
  { path: 'platform/observability/monitoring/alerts', name: 'platform-observability-monitoring-alerts', component: () => import('@/pages/platform/observability/Alerts.vue'), meta: { title: '告警中心', icon: 'Bell' } },
  { path: 'platform/observability/monitoring/traces', name: 'platform-observability-monitoring-traces', component: () => import('@/pages/platform/observability/Traces.vue'), meta: { title: '链路追踪', icon: 'Share' } },
  { path: 'platform/observability/monitoring/budgets', name: 'platform-observability-monitoring-budgets', component: () => import('@/pages/platform/observability/Budgets.vue'), meta: { title: '预算管理', icon: 'Wallet' } },
  { path: 'platform/observability/gpu', name: 'platform-observability-gpu', component: () => import('@/pages/platform/observability/GpuMonitorView.vue'), meta: { title: 'GPU 资源', icon: 'CPU' } },
  { path: 'platform/observability/usage', name: 'platform-observability-usage', component: () => import('@/pages/platform/observability/Usage.vue'), meta: { title: '用量统计', icon: 'DataLine' } },
  { path: 'platform/observability/billing', name: 'platform-observability-billing', component: () => import('@/pages/platform/observability/BillingView.vue'), meta: { title: '计费', icon: 'Money' } },
  { path: 'platform/observability/service-discovery', name: 'platform-observability-service-discovery', component: () => import('@/pages/platform/observability/GatewayServicesView.vue'), meta: { title: '服务发现与编排', icon: 'Connection' } },
  { path: 'platform/observability/gateway-test', name: 'platform-observability-gateway-test', component: () => import('@/pages/platform/observability/GatewayAggregateView.vue'), meta: { title: '聚合网关测试', icon: 'Operation' } },
  { path: 'platform/observability/app-calls', name: 'platform-observability-app-calls', component: GenericPage, meta: { title: '应用调用记录', icon: 'ChatDotRound' } },
  // v1.4.11：DPS 系统监控从画像模块上收（公共域可观测）
  { path: 'platform/observability/dps-monitor', name: 'platform-observability-dps-monitor', component: () => import('@/pages/platform/observability/DpsMonitorView.vue'), meta: { title: '画像系统监控', icon: 'Monitor', dependsOn: 'portrait' } },
]

/** 平台管理 · 开发者资源域 */
export const developerRoutes: RouteRecordRaw[] = [
  { path: 'platform/developers/docs', name: 'platform-developers-docs', component: () => import('@/pages/platform/developers/DocCenterView.vue'), meta: { title: '文档中心', icon: 'Reading' } },
  { path: 'platform/developers/edgerouter', name: 'platform-developers-edgerouter', component: () => import('@/pages/platform/developers/EdgeRouterView.vue'), meta: { title: 'EdgeRouter 与适配器', icon: 'Connection' } },
  { path: 'platform/developers/plugins', name: 'platform-developers-plugins', component: () => import('@/pages/platform/developers/PluginsView.vue'), meta: { title: '插件管理', icon: 'Box' } },
  // v1.4.11：DPS API 管理 + 知识库管理后台/控制台从业务模块上收（公共域开发者资源）
  { path: 'platform/developers/dps-api', name: 'platform-developers-dps-api', component: () => import('@/pages/platform/developers/DpsApiManageView.vue'), meta: { title: '画像 API 管理', icon: 'Connection', dependsOn: 'portrait' } },
  { path: 'platform/developers/knowledge-admin', name: 'platform-developers-knowledge-admin', component: () => import('@/pages/platform/developers/KnowledgeAdminView.vue'), meta: { title: '知识库管理后台', icon: 'Collection', dependsOn: 'knowledge' } },
  { path: 'platform/developers/knowledge-console', name: 'platform-developers-knowledge-console', component: () => import('@/pages/platform/developers/KnowledgeConsoleView.vue'), meta: { title: '知识库 API 控制台', icon: 'Reading', dependsOn: 'knowledge' } },
]

/**
 * 公共功能 · AI 能力治理域（v1.4.11）
 *
 * 从 OpenLLM 业务模块上收的「统一 AI 能力治理」页面：提供商、路由/熔断、部署、
 * 下载、工具调用、A/B 与 Prompt 资产。`dependsOn: 'openllm'` 表示随 OpenLLM
 * 模块启停——模块停用时菜单隐藏、直链进 403/仪表盘，避免出现「页面在但后端能力已下线」。
 */
export const governanceRoutes: RouteRecordRaw[] = [
  { path: 'platform/governance/providers', name: 'platform-governance-providers', component: () => import('@/pages/platform/governance/Providers.vue'), meta: { title: '提供商管理', icon: 'Connection', dependsOn: 'openllm' } },
  { path: 'platform/governance/model-categories', name: 'platform-governance-model-categories', component: () => import('@/pages/platform/governance/Categories.vue'), meta: { title: '模型分类', icon: 'Grid', dependsOn: 'openllm' } },
  { path: 'platform/governance/routing', name: 'platform-governance-routing', component: () => import('@/pages/platform/governance/Routing.vue'), meta: { title: '路由策略', icon: 'Connection', dependsOn: 'openllm' } },
  { path: 'platform/governance/circuit-breakers', name: 'platform-governance-circuit-breakers', component: () => import('@/pages/platform/governance/Routing.vue'), meta: { title: '熔断器', icon: 'Operation', dependsOn: 'openllm' } },
  { path: 'platform/governance/deploy', name: 'platform-governance-deploy', component: () => import('@/pages/platform/governance/DeployView.vue'), meta: { title: '模型部署', icon: 'Cpu', dependsOn: 'openllm' } },
  { path: 'platform/governance/downloads', name: 'platform-governance-downloads', component: () => import('@/pages/platform/governance/DownloadManagerView.vue'), meta: { title: '下载管理', icon: 'Download', dependsOn: 'openllm' } },
  { path: 'platform/governance/tool-calls', name: 'platform-governance-tool-calls', component: () => import('@/pages/platform/governance/ToolCallMonitorView.vue'), meta: { title: '工具调用监控', icon: 'DataLine', dependsOn: 'openllm' } },
  { path: 'platform/governance/ab-tests', name: 'platform-governance-ab-tests', component: () => import('@/pages/platform/governance/AbTestView.vue'), meta: { title: 'A/B 测试', icon: 'TrendCharts', dependsOn: 'openllm' } },
  { path: 'platform/governance/prompt-templates', name: 'platform-governance-prompt-templates', component: () => import('@/pages/platform/governance/PromptTemplatesView.vue'), meta: { title: 'Prompt 模板', icon: 'Document', dependsOn: 'openllm' } },
  { path: 'platform/governance/prompt-experiments', name: 'platform-governance-prompt-experiments', component: () => import('@/pages/platform/governance/PromptExperimentsView.vue'), meta: { title: 'Prompt 实验', icon: 'Operation', dependsOn: 'openllm' } },
]

/** 平台管理全部路由（AppLayout 子路由，路径相对 `/`；AC-146-10-2：不受单一模块启停影响）
 *
 * v1.4.11 例外：`dependsOn` 声明的治理页随对应模块启停（菜单隐藏 + 守卫拦截），
 * 其余公共域页面仍为静态常驻。 */
export const platformRoutes: RouteRecordRaw[] = [
  ...identityRoutes,
  ...configRoutes,
  ...observabilityRoutes,
  ...developerRoutes,
  ...governanceRoutes,
]