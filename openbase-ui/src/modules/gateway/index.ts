import type { RouteRecordRaw } from 'vue-router'

/**
 * 统一网关管理模块路由（v1.4.0，VC-006）
 * 板块：服务发现 / 聚合编排 —— 对齐《前端架构设计文档 v1.4.0》§2
 */
export const routes: RouteRecordRaw[] = [
  { path: '', redirect: '/gateway/services' },
  { path: 'services', name: 'gateway-services', component: () => import('./pages/GatewayServicesView.vue'), meta: { title: '服务列表' } },
  { path: 'aggregate', name: 'gateway-aggregate', component: () => import('./pages/GatewayAggregateView.vue'), meta: { title: '聚合测试' } },
]

/** 板块导航（ModuleLayout 菜单数据） */
export const navItems = [
  {
    label: '网关管理',
    items: [
      { path: '/gateway/services', title: '服务列表' },
      { path: '/gateway/aggregate', title: '聚合测试' },
    ],
  },
]
