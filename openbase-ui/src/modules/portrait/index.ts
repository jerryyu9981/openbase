import type { RouteRecordRaw } from 'vue-router'

/** 画像模块（DPS 特色，RT-208；无现成前端，按 API 分组全新设计） */
export const routes: RouteRecordRaw[] = [
  { path: '', redirect: '/portrait/list' },
  { path: 'list', name: 'portrait-list', component: () => import('./pages/PortraitList.vue'), meta: { title: '画像管理' } },
  // 管理子页静态路由须先于 ':id' 声明，避免被详情动态段吞并（走查修复：
  // 此前 permissions/monitor/api-manage/rate-limit 命中 ':id' → 渲染画像详情并 404）
  { path: 'permissions', name: 'portrait-permissions', component: () => import('./pages/DpsPermissionView.vue'), meta: { title: '权限管理' } },
  { path: 'monitor', name: 'portrait-monitor', component: () => import('./pages/DpsMonitorView.vue'), meta: { title: '系统监控' } },
  { path: 'api-manage', name: 'portrait-api-manage', component: () => import('./pages/DpsApiManageView.vue'), meta: { title: 'API 管理' } },
  { path: 'rate-limit', name: 'portrait-rate-limit', component: () => import('./pages/DpsRateLimitView.vue'), meta: { title: '限流管理' } },
  { path: ':id', name: 'portrait-detail', component: () => import('./pages/PortraitDetail.vue'), meta: { title: '画像详情' } },
  { path: 'search', name: 'portrait-search', component: () => import('./pages/PortraitSearch.vue'), meta: { title: '画像搜索' } },
  { path: 'tags', name: 'portrait-tags', component: () => import('./pages/Tags.vue'), meta: { title: '标签管理' } },
  { path: 'overview', name: 'portrait-overview', component: () => import('./pages/Overview.vue'), meta: { title: '数据总览' } },
  { path: 'rules', name: 'portrait-rules', component: () => import('./pages/Rules.vue'), meta: { title: '规则引擎' } },
  { path: 'reports', name: 'portrait-reports', component: () => import('./pages/PortraitList.vue'), meta: { title: '分析报表' } },
  { path: 'batch', name: 'portrait-batch', component: () => import('./pages/PortraitList.vue'), meta: { title: '批量任务' } },
]

/** 板块导航 */
export const navItems = [
  {
    label: '画像管理',
    items: [
      { path: '/portrait/overview', title: '数据总览' },
      { path: '/portrait/list', title: '画像列表' },
      { path: '/portrait/search', title: '画像搜索' },
      { path: '/portrait/tags', title: '标签管理' },
      { path: '/portrait/rules', title: '规则引擎' },
      { path: '/portrait/reports', title: '分析报表' },
      { path: '/portrait/rate-limit', title: '限流管理' },
      { path: '/portrait/api-manage', title: 'API 管理' },
      { path: '/portrait/permissions', title: '权限管理' },
      { path: '/portrait/monitor', title: '系统监控' },
      { path: '/portrait/batch', title: '批量任务' },
    ],
  },
]
