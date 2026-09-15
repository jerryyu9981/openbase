/**
 * 个人与帮助路由（v1.4.6 IA 归位）
 *
 * `/personal/**` 独立于平台管理四域；`/personal/settings` 登录即可，无平台权限码。
 */
import type { RouteRecordRaw } from 'vue-router'

export const personalRoutes: RouteRecordRaw[] = [
  { path: 'personal/settings', name: 'personal-settings', component: () => import('@/pages/personal/SettingsView.vue'), meta: { title: '个人设置', icon: 'User' } },
]