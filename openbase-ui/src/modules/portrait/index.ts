import type { RouteRecordRaw } from 'vue-router'

/** 画像模块（DPS 特色，RT-208；无现成前端，按 API 分组全新设计） */
export const routes: RouteRecordRaw[] = [
  { path: '', redirect: '/portrait' },
  { path: '', name: 'portrait-list', component: () => import('./pages/PortraitList.vue'), meta: { title: '画像管理' } },
  { path: ':id', name: 'portrait-detail', component: () => import('./pages/PortraitDetail.vue'), meta: { title: '画像详情' } },
  { path: 'search', name: 'portrait-search', component: () => import('./pages/PortraitList.vue'), meta: { title: '画像搜索' } },
  { path: 'tags', name: 'portrait-tags', component: () => import('./pages/PortraitList.vue'), meta: { title: '标签管理' } },
  { path: 'reports', name: 'portrait-reports', component: () => import('./pages/PortraitList.vue'), meta: { title: '分析报表' } },
  { path: 'batch', name: 'portrait-batch', component: () => import('./pages/PortraitList.vue'), meta: { title: '批量任务' } },
]
