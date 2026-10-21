import type { RouteRecordRaw } from 'vue-router'

/**
 * OpenLLM 业务模块路由（v1.4.11：治理类页面上收至公共功能域）
 *
 * 上收至 `/platform/governance/**` 的页面：提供商管理/注册、模型分类、路由策略、
 * 熔断器、模型部署、下载管理、工具调用监控、A/B 测试、Prompt 模板、Prompt 实验。
 * 旧路径经 legacyRedirects 统一重定向（禁 404）。
 *
 * 本模块仅保留场景化能力：模型资产浏览、AI 应用、对话与效果分析。
 */
export const routes: RouteRecordRaw[] = [
  { path: '', redirect: '/openllm/models' },
  // 模型中心
  { path: 'models', name: 'openllm-models', component: () => import('./pages/Models.vue'), meta: { title: '模型管理' } },
  { path: 'models/local', name: 'openllm-local-models', component: () => import('./pages/LocalModels.vue'), meta: { title: '本地模型' } },
  { path: 'models/comparison', name: 'openllm-comparison', component: () => import('./pages/Comparison.vue'), meta: { title: '模型对比' } },
  { path: 'models/market', name: 'openllm-market', component: () => import('./pages/ModelMarketView.vue'), meta: { title: '开源模型市场' } },
  { path: 'favorites', name: 'openllm-favorites', component: () => import('./pages/Favorites.vue'), meta: { title: '我的收藏' } },
  // AI 应用
  { path: 'apps', name: 'openllm-apps', component: () => import('./pages/Apps.vue'), meta: { title: 'AI 应用' } },
  { path: 'apps/new', name: 'openllm-app-new', component: () => import('./pages/AppForm.vue'), meta: { title: '创建应用' } },
  { path: 'apps/:id', name: 'openllm-app-detail', component: () => import('./pages/AppForm.vue'), meta: { title: '应用详情' } },
  { path: 'playground', name: 'openllm-playground', component: () => import('./pages/Playground.vue'), meta: { title: 'Playground' } },
  // 对话与分析
  { path: 'conversations', name: 'openllm-conversations', component: () => import('./pages/Conversations.vue'), meta: { title: '对话管理' } },
  { path: 'recommend', name: 'openllm-recommend', component: () => import('./pages/P2RecommendView.vue'), meta: { title: '模型对比推荐' } },
  { path: 'reports-trend', name: 'openllm-reports-trend', component: () => import('./pages/P2ReportTrendView.vue'), meta: { title: '报表趋势' } },
]

/** 板块导航（ModuleLayout 菜单数据） */
export const navItems = [
  {
    label: '模型中心',
    items: [
      { path: '/openllm/models', title: '模型管理' },
      { path: '/openllm/models/local', title: '本地模型' },
      { path: '/openllm/models/comparison', title: '模型对比' },
      { path: '/openllm/models/market', title: '开源市场' },
      { path: '/openllm/favorites', title: '我的收藏' },
    ],
  },
  {
    label: 'AI 应用',
    items: [
      { path: '/openllm/apps', title: '应用管理' },
      { path: '/openllm/playground', title: 'Playground' },
    ],
  },
  {
    label: '对话与分析',
    items: [
      { path: '/openllm/conversations', title: '对话管理' },
      { path: '/openllm/recommend', title: '模型对比推荐' },
      { path: '/openllm/reports-trend', title: '报表趋势' },
    ],
  },
]
