import type { RouteRecordRaw } from 'vue-router'

/**
 * OpenLLM 特色业务模块路由表（板块重设计 v1.2.0 落地；v1.4.6 IA 重构收口）
 * 板块：模型中心 / AI 应用 / 对话与路由
 *
 * v1.4.6（ADR-146-05/08）：系统性能力已上收至平台四域（settings、api-keys、usage、monitoring、
 * plugins、auth-ext、gpu、adapters、apps-calls 迁出），openllm 只保留本模块特色页——特色页零删减。
 * 旧路径经 legacyRedirects 统一重定向至新平台路径与个人设置（禁 404）。
 */
export const routes: RouteRecordRaw[] = [
  { path: '', redirect: '/openllm/models' },
  // 模型中心
  { path: 'models', name: 'openllm-models', component: () => import('./pages/Models.vue'), meta: { title: '模型管理' } },
  { path: 'models/local', name: 'openllm-local-models', component: () => import('./pages/LocalModels.vue'), meta: { title: '本地模型' } },
  { path: 'models/categories', name: 'openllm-categories', component: () => import('./pages/Categories.vue'), meta: { title: '模型分类' } },
  { path: 'models/comparison', name: 'openllm-comparison', component: () => import('./pages/Comparison.vue'), meta: { title: '模型对比' } },
  { path: 'models/market', name: 'openllm-market', component: () => import('./pages/ModelMarketView.vue'), meta: { title: '开源模型市场' } },
  { path: 'downloads', name: 'openllm-downloads', component: () => import('./pages/DownloadManagerView.vue'), meta: { title: '下载管理' } },
  { path: 'providers', name: 'openllm-providers', component: () => import('./pages/Providers.vue'), meta: { title: '提供商管理' } },
  { path: 'providers/register', name: 'openllm-provider-register', component: () => import('./pages/GenericPage.vue'), meta: { title: '提供商注册' } },
  { path: 'favorites', name: 'openllm-favorites', component: () => import('./pages/Favorites.vue'), meta: { title: '我的收藏' } },
  { path: 'deploy', name: 'openllm-deploy', component: () => import('./pages/GenericPage.vue'), meta: { title: '模型部署' } },
  // AI 应用
  { path: 'apps', name: 'openllm-apps', component: () => import('./pages/Apps.vue'), meta: { title: 'AI 应用' } },
  { path: 'apps/new', name: 'openllm-app-new', component: () => import('./pages/AppForm.vue'), meta: { title: '创建应用' } },
  { path: 'apps/:id', name: 'openllm-app-detail', component: () => import('./pages/AppForm.vue'), meta: { title: '应用详情' } },
  { path: 'playground', name: 'openllm-playground', component: () => import('./pages/Playground.vue'), meta: { title: 'Playground' } },
  { path: 'prompt-templates', name: 'openllm-prompt-templates', component: () => import('./pages/PromptTemplatesView.vue'), meta: { title: 'Prompt 模板' } },
  { path: 'prompt-experiments', name: 'openllm-prompt-experiments', component: () => import('./pages/PromptExperimentsView.vue'), meta: { title: 'Prompt 实验' } },
  { path: 'tool-calls', name: 'openllm-tool-calls', component: () => import('./pages/ToolCallMonitorView.vue'), meta: { title: '工具调用监控' } },
  { path: 'ab-tests', name: 'openllm-ab-tests', component: () => import('./pages/AbTestView.vue'), meta: { title: 'A/B 测试' } },
  // 对话与路由
  { path: 'conversations', name: 'openllm-conversations', component: () => import('./pages/Conversations.vue'), meta: { title: '对话管理' } },
  { path: 'routing/strategies', name: 'openllm-routing-strategies', component: () => import('./pages/Routing.vue'), meta: { title: '路由策略' } },
  { path: 'routing/circuit-breakers', name: 'openllm-circuit-breakers', component: () => import('./pages/Routing.vue'), meta: { title: '熔断器' } },
  { path: 'recommend', name: 'openllm-recommend', component: () => import('./pages/P2RecommendView.vue'), meta: { title: '模型对比推荐' } },
  { path: 'reports-trend', name: 'openllm-reports-trend', component: () => import('./pages/P2ReportTrendView.vue'), meta: { title: '报表趋势' } },
]

/** 板块导航（ModuleLayout 菜单数据，对齐系统架构设计文档 v1.4.6） */
export const navItems = [
  {
    label: '模型中心',
    items: [
      { path: '/openllm/models', title: '模型管理' },
      { path: '/openllm/models/categories', title: '模型分类' },
      { path: '/openllm/models/local', title: '本地模型' },
      { path: '/openllm/models/comparison', title: '模型对比' },
      { path: '/openllm/models/market', title: '开源市场' },
      { path: '/openllm/downloads', title: '下载管理' },
      { path: '/openllm/providers', title: '提供商管理' },
      { path: '/openllm/providers/register', title: '提供商注册' },
      { path: '/openllm/favorites', title: '我的收藏' },
      { path: '/openllm/deploy', title: '模型部署' },
    ],
  },
  {
    label: 'AI 应用',
    items: [
      { path: '/openllm/apps', title: '应用管理' },
      { path: '/openllm/playground', title: 'Playground' },
      { path: '/openllm/prompt-templates', title: 'Prompt 模板' },
      { path: '/openllm/prompt-experiments', title: 'Prompt 实验' },
      { path: '/openllm/tool-calls', title: '工具调用监控' },
      { path: '/openllm/ab-tests', title: 'A/B 测试' },
    ],
  },
  {
    label: '对话与路由',
    items: [
      { path: '/openllm/conversations', title: '对话管理' },
      { path: '/openllm/routing/strategies', title: '路由策略' },
      { path: '/openllm/routing/circuit-breakers', title: '熔断器' },
      { path: '/openllm/recommend', title: '模型对比推荐' },
      { path: '/openllm/reports-trend', title: '报表趋势' },
    ],
  },
]
