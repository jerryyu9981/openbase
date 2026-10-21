/**
 * 旧路径 → 新 IA 路径 重定向集中定义（v1.4.6，ADR-146-08 §3.1 全量映射）
 *
 * 约定：
 *  - 单文件维护（§3.3），便于审计与 E2E 遍历抽样断言（旧路径可达且落到预期新路径，AC-146-14-1）；
 *  - vue-router `redirect` 天然**保留 query 与 hash**（函数式 redirect 显式拼回 query，双保险）；
 *  - 旧路径来源路由已从模块/静态路由表移除（禁 404），此处以**顶层路由**承接使其保持可达；
 *  - gatekeeper：`LEGACY_REDIRECTS` 为纯数据，供 E2E 遍历与文档复用，禁止直接改此处破坏契约。
 */
import type { RouteRecordRaw } from 'vue-router'

/** 纯数据映射（from → to）。from 为绝对旧路径，to 为绝对新路径。 */
export const LEGACY_REDIRECTS: ReadonlyArray<readonly [string, string]> = [
  // 系统管理 → 平台四域
  ['/system/logs', '/platform/observability/logs'],
  ['/system/audit', '/platform/observability/logs'],
  ['/system/tenants', '/platform/identity/tenants'],
  ['/system/roles', '/platform/identity/roles'],
  ['/system/org', '/platform/identity/org'],
  ['/system/workspaces', '/platform/identity/workspaces'],
  ['/system/config', '/platform/config/general'],
  ['/system/billing', '/platform/observability/billing'],
  ['/system/test-records', '/platform/observability/test-records'],
  ['/system/docs', '/platform/developers/docs'],
  ['/system/edgerouter', '/platform/developers/edgerouter'],
  // openllm 系统性能力上收
  ['/openllm/settings', '/personal/settings'],
  ['/openllm/api-keys', '/platform/config/api-keys'],
  ['/openllm/usage', '/platform/observability/usage'],
  ['/openllm/monitoring', '/platform/observability/monitoring'],
  ['/openllm/monitoring/costs', '/platform/observability/monitoring/costs'],
  ['/openllm/monitoring/budgets', '/platform/observability/monitoring/budgets'],
  ['/openllm/monitoring/alerts', '/platform/observability/monitoring/alerts'],
  ['/openllm/monitoring/traces', '/platform/observability/monitoring/traces'],
  ['/openllm/gpu', '/platform/observability/gpu'],
  ['/openllm/plugins', '/platform/developers/plugins'],
  ['/openllm/auth-ext', '/platform/identity/auth-ext'],
  ['/openllm/adapters', '/platform/developers/edgerouter'],
  ['/openllm/apps/calls', '/platform/observability/app-calls'],
  // memory / portrait / knowledge 上收
  ['/memory/admin', '/platform/identity/memory-admin'],
  ['/memory/api-gateway', '/platform/observability/service-discovery'],
  ['/memory/monitor', '/platform/observability/monitoring'],
  ['/portrait/dps-monitor', '/platform/observability/monitoring'],
  ['/knowledge/settings', '/platform/config/general'],
  ['/knowledge/users', '/platform/identity/users'],
  // gateway 迁入可观测域
  ['/gateway/services', '/platform/observability/service-discovery'],
  ['/gateway/aggregate', '/platform/observability/gateway-test'],
  // v1.4.11：治理类页面上收至公共功能域（业务模块只保留场景功能）
  ['/openllm/providers', '/platform/governance/providers'],
  // 提供商注册为提供商管理页内嵌表单（不单独成页），旧直达链接收敛到列表页
  ['/openllm/providers/register', '/platform/governance/providers'],
  ['/openllm/models/categories', '/platform/governance/model-categories'],
  ['/openllm/routing/strategies', '/platform/governance/routing'],
  ['/openllm/routing/circuit-breakers', '/platform/governance/circuit-breakers'],
  ['/openllm/deploy', '/platform/governance/deploy'],
  ['/openllm/downloads', '/platform/governance/downloads'],
  ['/openllm/tool-calls', '/platform/governance/tool-calls'],
  ['/openllm/ab-tests', '/platform/governance/ab-tests'],
  ['/openllm/prompt-templates', '/platform/governance/prompt-templates'],
  ['/openllm/prompt-experiments', '/platform/governance/prompt-experiments'],
  ['/portrait/permissions', '/platform/identity/dps-permissions'],
  ['/portrait/rate-limit', '/platform/config/rate-limits'],
  ['/portrait/monitor', '/platform/observability/dps-monitor'],
  ['/portrait/api-manage', '/platform/developers/dps-api'],
  // v1.4.11：画像「分析报表 / 批量任务」原为复用列表视图的假页面，下线后回落到画像列表
  ['/portrait/reports', '/portrait/list'],
  ['/portrait/batch', '/portrait/list'],
  ['/knowledge/admin', '/platform/developers/knowledge-admin'],
  ['/knowledge/console', '/platform/developers/knowledge-console'],
  // v1.4.11 收口：DPS 模板化页面从顶部 `/dps/**` 归位到画像模块 `/portrait/dps/**`
  ['/dps/templates', '/portrait/dps/templates'],
  ['/dps/templates/new', '/portrait/dps/templates/new'],
  ['/dps/template-packages', '/portrait/dps/template-packages'],
  ['/dps/lineage', '/portrait/dps/lineage'],
  ['/dps/measures', '/portrait/dps/measures'],
  ['/dps/scoring-types', '/portrait/dps/scoring-types'],
  ['/dps/annotation-adapters', '/portrait/dps/annotation-adapters'],
  ['/dps/annotation-templates', '/portrait/dps/annotation-templates'],
  ['/dps/tags', '/portrait/dps/tags'],
]

/** 顶层重定向路由（承接旧路径，保留 query/hash）。 */
export const legacyRedirectRoutes: RouteRecordRaw[] = LEGACY_REDIRECTS.map(([from, to]) => ({
  path: from,
  redirect: (toLocation) => ({
    path: to,
    query: toLocation.query,
    hash: toLocation.hash,
  }),
}))

/**
 * DPS 动态子路径前缀迁移（`/dps/templates/:code/edit|versions|preflight`、
 * `/dps/annotation-templates/:code/fields` 无法逐条枚举）。
 *
 * 单独导出、不并入 `LEGACY_REDIRECTS`：该数组是「旧路径 ↔ 新路径」契约数据，
 * 仅承载可枚举的精确映射，E2E 与用例按其条目逐条断言。
 */
export const legacyPrefixRedirectRoutes: RouteRecordRaw[] = [
  {
    path: '/dps/:pathMatch(.*)*',
    redirect: (toLocation) => ({
      path: `/portrait${toLocation.path}`,
      query: toLocation.query,
      hash: toLocation.hash,
    }),
  },
]