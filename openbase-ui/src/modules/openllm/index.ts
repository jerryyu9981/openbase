import type { RouteRecordRaw } from 'vue-router'

/**
 * OpenLLM 特色模块路由表（板块重设计 v1.2.0 落地）
 * 板块：模型中心 / AI 应用 / 对话监控 / 平台联动
 */
export const routes: RouteRecordRaw[] = [
  { path: '', redirect: '/openllm/models' },
  // 模型中心
  { path: 'models', name: 'openllm-models', component: () => import('./pages/Models.vue'), meta: { title: '模型管理' } },
  { path: 'models/local', name: 'openllm-local-models', component: () => import('./pages/LocalModels.vue'), meta: { title: '本地模型' } },
  { path: 'models/categories', name: 'openllm-categories', component: () => import('./pages/Categories.vue'), meta: { title: '模型分类' } },
  { path: 'models/comparison', name: 'openllm-comparison', component: () => import('./pages/Comparison.vue'), meta: { title: '模型对比' } },
  { path: 'models/market', name: 'openllm-market', component: () => import('./pages/GenericPage.vue'), meta: { title: '开源模型市场' } },
  { path: 'providers', name: 'openllm-providers', component: () => import('./pages/Providers.vue'), meta: { title: '提供商管理' } },
  { path: 'providers/register', name: 'openllm-provider-register', component: () => import('./pages/GenericPage.vue'), meta: { title: '提供商注册' } },
  { path: 'favorites', name: 'openllm-favorites', component: () => import('./pages/Favorites.vue'), meta: { title: '我的收藏' } },
  { path: 'usage', name: 'openllm-usage', component: () => import('./pages/Usage.vue'), meta: { title: '用量统计' } },
  { path: 'settings', name: 'openllm-settings', component: () => import('./pages/Settings.vue'), meta: { title: '个人设置' } },
  { path: 'auth-ext', name: 'openllm-auth-ext', component: () => import('./pages/AuthExt.vue'), meta: { title: '注册/找回密码' } },
  { path: 'api-keys', name: 'openllm-api-keys', component: () => import('./pages/ApiKeys.vue'), meta: { title: 'API 密钥' } },
  { path: 'deploy', name: 'openllm-deploy', component: () => import('./pages/GenericPage.vue'), meta: { title: '模型部署' } },
  { path: 'gpu', name: 'openllm-gpu', component: () => import('./pages/GenericPage.vue'), meta: { title: 'GPU 资源' } },
  { path: 'adapters', name: 'openllm-adapters', component: () => import('./pages/GenericPage.vue'), meta: { title: 'EdgeRouter 适配器' } },
  // AI 应用（全新补建）
  { path: 'apps', name: 'openllm-apps', component: () => import('./pages/Apps.vue'), meta: { title: 'AI 应用' } },
  { path: 'apps/new', name: 'openllm-app-new', component: () => import('./pages/AppForm.vue'), meta: { title: '创建应用' } },
  { path: 'apps/:id', name: 'openllm-app-detail', component: () => import('./pages/AppForm.vue'), meta: { title: '应用详情' } },
  { path: 'apps/calls', name: 'openllm-app-calls', component: () => import('./pages/GenericPage.vue'), meta: { title: '调用记录' } },
  { path: 'playground', name: 'openllm-playground', component: () => import('./pages/Playground.vue'), meta: { title: 'Playground' } },
  { path: 'prompt-templates', name: 'openllm-prompt-templates', component: () => import('./pages/GenericPage.vue'), meta: { title: 'Prompt 模板' } },
  { path: 'prompt-experiments', name: 'openllm-prompt-experiments', component: () => import('./pages/GenericPage.vue'), meta: { title: 'Prompt 实验' } },
  // 对话监控
  { path: 'conversations', name: 'openllm-conversations', component: () => import('./pages/Conversations.vue'), meta: { title: '对话管理' } },
  { path: 'monitoring', name: 'openllm-monitoring', component: () => import('./pages/Monitoring.vue'), meta: { title: '监控仪表盘' } },
  { path: 'monitoring/traces', name: 'openllm-traces', component: () => import('./pages/GenericPage.vue'), meta: { title: '链路追踪' } },
  { path: 'monitoring/costs', name: 'openllm-costs', component: () => import('./pages/Costs.vue'), meta: { title: '成本分析' } },
  { path: 'monitoring/budgets', name: 'openllm-budgets', component: () => import('./pages/GenericPage.vue'), meta: { title: '预算管理' } },
  { path: 'monitoring/alerts', name: 'openllm-alerts', component: () => import('./pages/Alerts.vue'), meta: { title: '告警中心' } },
  // 平台联动
  { path: 'routing/strategies', name: 'openllm-routing-strategies', component: () => import('./pages/Routing.vue'), meta: { title: '路由策略' } },
  { path: 'routing/circuit-breakers', name: 'openllm-circuit-breakers', component: () => import('./pages/Routing.vue'), meta: { title: '熔断器' } },
]

/** 板块导航（ModuleLayout 菜单数据，对齐系统架构设计文档 §8.2） */
export const navItems = [
  {
    label: '模型中心',
    items: [
      { path: '/openllm/models', title: '模型管理' },
      { path: '/openllm/models/local', title: '本地模型' },
      { path: '/openllm/models/categories', title: '模型分类' },
      { path: '/openllm/models/comparison', title: '模型对比' },
      { path: '/openllm/models/market', title: '开源市场' },
      { path: '/openllm/providers', title: '提供商管理' },
      { path: '/openllm/favorites', title: '我的收藏' },
      { path: '/openllm/usage', title: '用量统计' },
      { path: '/openllm/settings', title: '个人设置' },
      { path: '/openllm/providers/register', title: '提供商注册' },
      { path: '/openllm/api-keys', title: 'API 密钥' },
      { path: '/openllm/deploy', title: '模型部署' },
      { path: '/openllm/gpu', title: 'GPU 资源' },
      { path: '/openllm/adapters', title: 'EdgeRouter 适配器' },
    ],
  },
  {
    label: 'AI 应用',
    items: [
      { path: '/openllm/apps', title: '应用管理' },
      { path: '/openllm/playground', title: 'Playground' },
      { path: '/openllm/prompt-templates', title: 'Prompt 模板' },
      { path: '/openllm/prompt-experiments', title: 'Prompt 实验' },
      { path: '/openllm/apps/calls', title: '调用记录' },
    ],
  },
  {
    label: '对话监控',
    items: [
      { path: '/openllm/conversations', title: '对话管理' },
      { path: '/openllm/monitoring', title: '监控仪表盘' },
      { path: '/openllm/monitoring/traces', title: '链路追踪' },
      { path: '/openllm/monitoring/costs', title: '成本分析' },
      { path: '/openllm/monitoring/budgets', title: '预算管理' },
      { path: '/openllm/monitoring/alerts', title: '告警中心' },
    ],
  },
  {
    label: '平台联动',
    items: [
      { path: '/openllm/routing/strategies', title: '路由策略' },
      { path: '/openllm/routing/circuit-breakers', title: '熔断器' },
    ],
  },
]
