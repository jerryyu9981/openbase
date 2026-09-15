import type { RouteRecordRaw } from 'vue-router'

/**
 * 统一网关模块路由（v1.4.0，VC-006）—— v1.4.6 已整体迁入平台管理「可观测与审计」域
 * （ADR-146-08），本文件不再由 router 装载；保留组件指向为避免历史引用悬空（禁 404）。
 * 服务发现 → `/platform/observability/service-discovery`；聚合测试 → `/platform/observability/gateway-test`。
 */
export const routes: RouteRecordRaw[] = [
  { path: '', redirect: '/platform/observability/service-discovery' },
  { path: 'services', name: 'gateway-services', component: () => import('@/pages/platform/observability/GatewayServicesView.vue'), meta: { title: '服务列表' } },
  { path: 'aggregate', name: 'gateway-aggregate', component: () => import('@/pages/platform/observability/GatewayAggregateView.vue'), meta: { title: '聚合测试' } },
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
