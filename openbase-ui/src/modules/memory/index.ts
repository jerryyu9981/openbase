import type { RouteRecordRaw } from 'vue-router'

/** 记忆模块（OpenMemory 特色，RT-207） */
export const routes: RouteRecordRaw[] = [
  { path: '', redirect: '/memory/list' },
  { path: 'list', name: 'memory-list', component: () => import('./pages/MemoryList.vue'), meta: { title: '记忆管理' } },
  { path: ':id', name: 'memory-detail', component: () => import('./pages/MemoryDetail.vue'), meta: { title: '记忆详情' } },
  { path: 'search', name: 'memory-search', component: () => import('./pages/MemoryList.vue'), meta: { title: '记忆搜索' } },
  { path: 'sessions', name: 'memory-sessions', component: () => import('./pages/MemoryList.vue'), meta: { title: '会话管理' } },
  { path: 'graph', name: 'memory-graph', component: () => import('./pages/MemoryGraph.vue'), meta: { title: '记忆图谱' } },
  { path: 'api-gateway', name: 'memory-api-gateway', component: () => import('./pages/ApiGateway.vue'), meta: { title: 'API 网关' } },
  { path: 'admin', name: 'memory-admin', component: () => import('./pages/Admin.vue'), meta: { title: '管理后台' } },
  { path: 'monitor', name: 'memory-monitor', component: () => import('./pages/MemoryMonitorView.vue'), meta: { title: '系统监控' } },
  { path: 'decay', name: 'memory-decay', component: () => import('./pages/MemoryList.vue'), meta: { title: '衰减配置' } },
  { path: 'write', name: 'memory-write', component: () => import('./pages/MemoryList.vue'), meta: { title: '写入记忆' } },
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
      { path: '/memory/api-gateway', title: 'API 网关' },
      { path: '/memory/admin', title: '管理后台' },
      { path: '/memory/decay', title: '衰减配置' },
      { path: '/memory/write', title: '写入记忆' },
    ],
  },
]
