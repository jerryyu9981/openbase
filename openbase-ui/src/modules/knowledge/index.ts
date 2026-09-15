import type { RouteRecordRaw } from 'vue-router'

/** 知识库模块（OpenRAG 特色，RT-206）。
 * v1.4.6：`users` 迁至 `/platform/identity/users`、`settings` 迁至 `/platform/config/general`
 * （legacyRedirects 承接旧 `/knowledge/users`、`/knowledge/settings`，禁 404）。 */
export const routes: RouteRecordRaw[] = [
  { path: '', redirect: '/knowledge/list' },
  { path: 'list', name: 'knowledge-list', component: () => import('./pages/KnowledgeList.vue'), meta: { title: '知识库' } },
  { path: ':id', name: 'knowledge-detail', component: () => import('./pages/KnowledgeDetail.vue'), meta: { title: '知识库详情' } },
  { path: 'chat', name: 'knowledge-chat', component: () => import('./pages/ChatView.vue'), meta: { title: 'RAG 对话' } },
  { path: 'admin', name: 'knowledge-admin', component: () => import('./pages/KnowledgeAdminView.vue'), meta: { title: '知识库管理后台' } },
  { path: 'console', name: 'knowledge-console', component: () => import('./pages/KnowledgeConsoleView.vue'), meta: { title: 'API 控制台' } },
]

/** 板块导航 */
export const navItems = [
  {
    label: '知识库',
    items: [
      { path: '/knowledge/list', title: '知识库管理' },
      { path: '/knowledge/chat', title: 'RAG 对话' },
      { path: '/knowledge/admin', title: '管理后台' },
      { path: '/knowledge/console', title: '控制台' },
    ],
  },
]
