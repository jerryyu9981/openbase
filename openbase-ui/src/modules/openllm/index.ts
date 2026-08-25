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
  { path: 'models/market', name: 'openllm-market', component: () => import('./pages/GenericPage.vue'), meta: { title: '开源模型市场' } },
  { path: 'providers', name: 'openllm-providers', component: () => import('./pages/Providers.vue'), meta: { title: '提供商管理' } },
  { path: 'providers/register', name: 'openllm-provider-register', component: () => import('./pages/GenericPage.vue'), meta: { title: '提供商注册' } },
  { path: 'api-keys', name: 'openllm-api-keys', component: () => import('./pages/GenericPage.vue'), meta: { title: 'API 密钥' } },
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
  { path: 'monitoring/costs', name: 'openllm-costs', component: () => import('./pages/GenericPage.vue'), meta: { title: '成本分析' } },
  { path: 'monitoring/budgets', name: 'openllm-budgets', component: () => import('./pages/GenericPage.vue'), meta: { title: '预算管理' } },
  { path: 'monitoring/alerts', name: 'openllm-alerts', component: () => import('./pages/GenericPage.vue'), meta: { title: '告警中心' } },
  // 平台联动
  { path: 'routing/strategies', name: 'openllm-routing-strategies', component: () => import('./pages/GenericPage.vue'), meta: { title: '路由策略' } },
  { path: 'routing/circuit-breakers', name: 'openllm-circuit-breakers', component: () => import('./pages/GenericPage.vue'), meta: { title: '熔断器' } },
]
