import type { RouteRecordRaw } from 'vue-router'

/**
 * 知识库模块（OpenRAG 特色，RT-206）。
 *
 * v1.4.11：管理后台 / API 控制台上收至公共功能域开发者资源
 * （`/platform/developers/knowledge-admin`、`/platform/developers/knowledge-console`），
 * 旧路径经 legacyRedirects 承接（禁 404）。
 * v1.4.6：`users` 迁至 `/platform/identity/users`、`settings` 迁至 `/platform/config/general`。
 */
export const routes: RouteRecordRaw[] = [
  { path: '', redirect: '/knowledge/list' },
  { path: 'list', name: 'knowledge-list', component: () => import('./pages/KnowledgeList.vue'), meta: { title: '知识库' } },
  { path: ':id', name: 'knowledge-detail', component: () => import('./pages/KnowledgeDetail.vue'), meta: { title: '知识库详情' } },
  { path: 'chat', name: 'knowledge-chat', component: () => import('./pages/ChatView.vue'), meta: { title: 'RAG 对话' } },
]

/** 板块导航 */
export const navItems = [
  {
    label: '知识库',
    items: [
      { path: '/knowledge/list', title: '知识库管理' },
      { path: '/knowledge/chat', title: 'RAG 对话' },
    ],
  },
]
