/**
 * 平台管理四域路由（v1.4.6 IA 重构，ADR-146-05/08）
 *
 * 统一前缀 `/platform/**`（作为 `/` AppLayout 的子路由，路径相对 `/`）。
 * 权限口径（§3.2 三处一致）：`meta.permission` 与后端权限码同名。
 *  - `log:read` / `module:manage` / `test:record` 显式声明（菜单可见性 + 守卫同源）；
 *  - 其余平台页沿用既有（无独立权限码 → 仅登录可见，与迁移前一致）。
 * `GenericPage` 承载的占位路由按 UI 设计 §9.3 R2/R3：**复用** openllm 单份实现（不复制）。
 */
import type { RouteRecordRaw } from 'vue-router'

const GenericPage = () => import('@/modules/openllm/pages/GenericPage.vue')

/** 平台管理 · 身份与权限域 */
export const identityRoutes: RouteRecordRaw[] = [
  { path: 'platform/identity/tenants', name: 'platform-identity-tenants', component: () => import('@/pages/platform/identity/SystemTenants.vue'), meta: { title: '租户管理', icon: 'OfficeBuilding' } },
  { path: 'platform/identity/roles', name: 'platform-identity-roles', component: () => import('@/pages/platform/identity/RolesView.vue'), meta: { title: '角色与权限', icon: 'User' } },
  { path: 'platform/identity/org', name: 'platform-identity-org', component: () => import('@/pages/platform/identity/OrgTeamsUsersView.vue'), meta: { title: '组织/团队/用户', icon: 'OfficeBuilding' } },
  { path: 'platform/identity/workspaces', name: 'platform-identity-workspaces', component: () => import('@/pages/platform/identity/WorkspacesView.vue'), meta: { title: '工作空间', icon: 'Grid' } },
  { path: 'platform/identity/auth-ext', name: 'platform-identity-auth-ext', component: () => import('@/pages/platform/identity/AuthExt.vue'), meta: { title: '注册/找回密码', icon: 'Key' } },
  { path: 'platform/identity/users', name: 'platform-identity-users', component: () => import('@/pages/platform/identity/UsersView.vue'), meta: { title: '用户管理', icon: 'User' } },
  { path: 'platform/identity/memory-admin', name: 'platform-identity-memory-admin', component: () => import('@/pages/platform/identity/MemoryAdminView.vue'), meta: { title: '记忆管理席位', icon: 'Setting' } },
]

/** 平台管理 · 平台配置与密钥域 */
export const configRoutes: RouteRecordRaw[] = [
  { path: 'platform/config/general', name: 'platform-config-general', component: () => import('@/pages/platform/config/ConfigManageView.vue'), meta: { title: '全局配置', icon: 'Setting' } },
  { path: 'platform/config/modules', name: 'platform-config-modules', component: () => import('@/pages/platform/config/ModuleSwitchView.vue'), meta: { title: '模块开关', icon: 'Grid', permission: 'module:manage' } },
  { path: 'platform/config/api-keys', name: 'platform-config-api-keys', component: () => import('@/pages/platform/config/ApiKeys.vue'), meta: { title: 'API 密钥', icon: 'Key' } },
]

/** 平台管理 · 可观测与审计域 */
export const observabilityRoutes: RouteRecordRaw[] = [
  { path: 'platform/observability/logs', name: 'platform-observability-logs', component: () => import('@/pages/platform/observability/LogsView.vue'), meta: { title: '日志中心', icon: 'Document', permission: 'log:read' } },
  { path: 'platform/observability/test-records', name: 'platform-observability-test-records', component: () => import('@/pages/platform/observability/SystemTestRecords.vue'), meta: { title: '测试记录', icon: 'Memo', permission: 'test:record' } },
  { path: 'platform/observability/monitoring', name: 'platform-observability-monitoring', component: () => import('@/pages/platform/observability/Monitoring.vue'), meta: { title: '统一监控', icon: 'Monitor' } },
  { path: 'platform/observability/monitoring/costs', name: 'platform-observability-monitoring-costs', component: () => import('@/pages/platform/observability/Costs.vue'), meta: { title: '成本分析', icon: 'TrendCharts' } },
  { path: 'platform/observability/monitoring/alerts', name: 'platform-observability-monitoring-alerts', component: () => import('@/pages/platform/observability/Alerts.vue'), meta: { title: '告警中心', icon: 'Bell' } },
  { path: 'platform/observability/monitoring/traces', name: 'platform-observability-monitoring-traces', component: GenericPage, meta: { title: '链路追踪', icon: 'Share' } },
  { path: 'platform/observability/monitoring/budgets', name: 'platform-observability-monitoring-budgets', component: GenericPage, meta: { title: '预算管理', icon: 'Wallet' } },
  { path: 'platform/observability/gpu', name: 'platform-observability-gpu', component: () => import('@/pages/platform/observability/GpuMonitorView.vue'), meta: { title: 'GPU 资源', icon: 'CPU' } },
  { path: 'platform/observability/usage', name: 'platform-observability-usage', component: () => import('@/pages/platform/observability/Usage.vue'), meta: { title: '用量统计', icon: 'DataLine' } },
  { path: 'platform/observability/billing', name: 'platform-observability-billing', component: () => import('@/pages/platform/observability/BillingView.vue'), meta: { title: '计费', icon: 'Money' } },
  { path: 'platform/observability/service-discovery', name: 'platform-observability-service-discovery', component: () => import('@/pages/platform/observability/GatewayServicesView.vue'), meta: { title: '服务发现与编排', icon: 'Connection' } },
  { path: 'platform/observability/gateway-test', name: 'platform-observability-gateway-test', component: () => import('@/pages/platform/observability/GatewayAggregateView.vue'), meta: { title: '聚合网关测试', icon: 'Operation' } },
  { path: 'platform/observability/app-calls', name: 'platform-observability-app-calls', component: GenericPage, meta: { title: '应用调用记录', icon: 'ChatDotRound' } },
]

/** 平台管理 · 开发者资源域 */
export const developerRoutes: RouteRecordRaw[] = [
  { path: 'platform/developers/docs', name: 'platform-developers-docs', component: () => import('@/pages/platform/developers/DocCenterView.vue'), meta: { title: '文档中心', icon: 'Reading' } },
  { path: 'platform/developers/edgerouter', name: 'platform-developers-edgerouter', component: () => import('@/pages/platform/developers/EdgeRouterView.vue'), meta: { title: 'EdgeRouter 与适配器', icon: 'Connection' } },
  { path: 'platform/developers/plugins', name: 'platform-developers-plugins', component: () => import('@/pages/platform/developers/PluginsView.vue'), meta: { title: '插件管理', icon: 'Box' } },
]

/** 平台管理全部路由（AppLayout 子路由，路径相对 `/`；AC-146-10-2：不受单一模块启停影响） */
export const platformRoutes: RouteRecordRaw[] = [
  ...identityRoutes,
  ...configRoutes,
  ...observabilityRoutes,
  ...developerRoutes,
]