import type { RouteRecordRaw } from 'vue-router'

/** 记忆模块（OpenMemory 特色，RT-207） */
export const routes: RouteRecordRaw[] = [
  { path: '', redirect: '/memory' },
  { path: '', name: 'memory-list', component: () => import('./pages/MemoryList.vue'), meta: { title: '记忆管理' } },
  { path: ':id', name: 'memory-detail', component: () => import('./pages/MemoryDetail.vue'), meta: { title: '记忆详情' } },
  { path: 'search', name: 'memory-search', component: () => import('./pages/MemoryList.vue'), meta: { title: '记忆搜索' } },
  { path: 'sessions', name: 'memory-sessions', component: () => import('./pages/MemoryList.vue'), meta: { title: '会话管理' } },
  { path: 'graph', name: 'memory-graph', component: () => import('./pages/MemoryList.vue'), meta: { title: '记忆图谱' } },
  { path: 'decay', name: 'memory-decay', component: () => import('./pages/MemoryList.vue'), meta: { title: '衰减配置' } },
  { path: 'write', name: 'memory-write', component: () => import('./pages/MemoryList.vue'), meta: { title: '写入记忆' } },
]
