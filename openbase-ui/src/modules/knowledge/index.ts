import type { RouteRecordRaw } from 'vue-router'

/** 知识库模块（OpenRAG 特色，RT-206） */
export const routes: RouteRecordRaw[] = [
  { path: '', redirect: '/knowledge/list' },
  { path: 'list', name: 'knowledge-list', component: () => import('./pages/KnowledgeList.vue'), meta: { title: '知识库' } },
  { path: ':id', name: 'knowledge-detail', component: () => import('./pages/KnowledgeDetail.vue'), meta: { title: '知识库详情' } },
]

/** 板块导航 */
export const navItems = [
  {
    label: '知识库',
    items: [{ path: '/knowledge/list', title: '知识库管理' }],
  },
]
