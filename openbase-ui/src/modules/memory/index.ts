import type { RouteRecordRaw } from 'vue-router'

/** 记忆模块（OpenMemory 特色，RT-207）。
 * v1.4.6：`admin`→`/platform/identity/memory-admin`、`api-gateway`→`/platform/observability/service-discovery`、
 * `monitor`→`/platform/observability/monitoring`（统一监控），旧路径经 legacyRedirects 承接（禁 404）。 */
export const routes: RouteRecordRaw[] = [
  { path: '', redirect: '/memory/list' },
  { path: 'list', name: 'memory-list', component: () => import('./pages/MemoryList.vue'), meta: { title: '记忆管理' } },
  { path: ':id', name: 'memory-detail', component: () => import('./pages/MemoryDetail.vue'), meta: { title: '记忆详情' } },
  { path: 'search', name: 'memory-search', component: () => import('./pages/MemorySearch.vue'), meta: { title: '记忆搜索' } },
  { path: 'sessions', name: 'memory-sessions', component: () => import('./pages/MemorySessions.vue'), meta: { title: '会话管理' } },
  { path: 'graph', name: 'memory-graph', component: () => import('./pages/MemoryGraph.vue'), meta: { title: '记忆图谱' } },
  { path: 'decay', name: 'memory-decay', component: () => import('./pages/MemoryDecay.vue'), meta: { title: '衰减配置' } },
  { path: 'write', name: 'memory-write', component: () => import('./pages/MemoryWrite.vue'), meta: { title: '写入记忆' } },
]

/** 板块导航 */
export const navItems = [
  {
    label: '记忆管理',
    items: [
      { path: '/memory/list', title: '记忆列表' },
      { path: '/memory/search', title: '记忆搜索' },
      { path: '/memory/sessions', title: '会话管理' },
      { path: '/memory/graph', title: '记忆图谱' },
      { path: '/memory/decay', title: '衰减配置' },
      { path: '/memory/write', title: '写入记忆' },
    ],
  },
]
