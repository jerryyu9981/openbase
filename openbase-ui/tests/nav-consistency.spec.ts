/**
 * S6-T2-3 导航一致性断言（设计草案 §4.2 设计说明 4）
 *
 * 断言口径：
 * - 任一模块「菜单项集合 ⊆ 路由可匹配集合」（INV-2，菜单不得指向缺失路由）；
 * - 「routes − 菜单 ⊆ 显式白名单（详情/表单/重定向）」——白名单条目逐条有理由注释；
 * - 菜单项路径唯一（无重复项）；
 * - 菜单项路径以模块 `route_prefix` 为前缀（顶层壳 ↔ 模块内导航 ↔ 路由一致）；
 * - 子路由不得声明 `meta.navItems`（防 Vue Router `route.meta` shallow merge 覆盖父级导航，R-6）。
 */
import { describe, expect, it } from 'vitest'
import type { RouteRecordRaw } from 'vue-router'
import { findNavItemsOverrides } from '@/core/router'
import { routes as openllmRoutes, navItems as openllmNav } from '@/modules/openllm'
import { routes as memoryRoutes, navItems as memoryNav } from '@/modules/memory'
import { routes as knowledgeRoutes, navItems as knowledgeNav } from '@/modules/knowledge'
import { routes as portraitRoutes, navItems as portraitNav } from '@/modules/portrait'
import { routes as gatewayRoutes, navItems as gatewayNav } from '@/modules/gateway'

interface NavItem { path: string; title: string }
interface NavGroup { label: string; items: NavItem[] }

interface ModuleNavCase {
  id: string
  prefix: string
  routes: RouteRecordRaw[]
  navItems: NavGroup[]
}

const MODULE_NAV_CASES: ModuleNavCase[] = [
  { id: 'openllm', prefix: '/openllm', routes: openllmRoutes, navItems: openllmNav as NavGroup[] },
  { id: 'memory', prefix: '/memory', routes: memoryRoutes, navItems: memoryNav as NavGroup[] },
  { id: 'knowledge', prefix: '/knowledge', routes: knowledgeRoutes, navItems: knowledgeNav as NavGroup[] },
  { id: 'portrait', prefix: '/portrait', routes: portraitRoutes, navItems: portraitNav as NavGroup[] },
  { id: 'gateway', prefix: '/gateway', routes: gatewayRoutes, navItems: gatewayNav as NavGroup[] },
]

/**
 * 不入菜单的详情 / 表单 / 重定向路由显式白名单（相对路径，键 = 模块 id）。
 * 每条理由见右侧注释；白名单外出现「routes − 菜单」条目即视为遗漏（断言失败）。
 */
const NON_MENU_ROUTE_WHITELIST: Record<string, string[]> = {
  // AI 应用详情/新建表单（由列表页进入，不占菜单位）+ 注册/找回密码（auth-ext，登录态入口）
  openllm: ['apps/new', 'apps/:id', 'auth-ext'],
  // 记忆详情（由列表行进入）+ 系统监控（运维页，菜单只保留业务板块）
  memory: [':id', 'monitor'],
  // 知识库详情（由列表卡片进入）
  knowledge: [':id'],
  // 画像详情（由列表行进入；reports/batch 复用列表视图但已在菜单内）
  portrait: [':id'],
  // 网关模块全部路由均入菜单
  gateway: [],
}

/** 某模块可被路由匹配的相对路径集合（排除空路径 redirect 与显式 redirect 记录） */
function matcheableRelativePaths(routes: RouteRecordRaw[]): string[] {
  return routes
    .filter((route) => route.path !== '' && !route.redirect)
    .map((route) => String(route.path))
}

function menuPaths(navItems: NavGroup[]): string[] {
  return navItems.flatMap((group) => group.items.map((item) => item.path))
}

describe('S6-T2-3: 模块「菜单 ↔ 路由」一致性', () => {
  it.each(MODULE_NAV_CASES)('$id：菜单项 ⊆ 路由可匹配集合（无遗漏指向缺失路由）', ({ prefix, routes, navItems }) => {
    const matcheable = new Set(matcheableRelativePaths(routes).map((path) => `${prefix}/${path}`))
    const missing = menuPaths(navItems).filter((path) => !matcheable.has(path))
    expect(missing).toEqual([])
  })

  it.each(MODULE_NAV_CASES)('$id：routes − 菜单 ⊆ 显式白名单（逐条有理由）', ({ id, prefix, routes, navItems }) => {
    const menu = new Set(menuPaths(navItems))
    const notInMenu = matcheableRelativePaths(routes).filter((path) => !menu.has(`${prefix}/${path}`))
    const whitelist = NON_MENU_ROUTE_WHITELIST[id]
    const unexpected = notInMenu.filter((path) => !whitelist.includes(path))
    expect(unexpected).toEqual([])
  })

  it.each(MODULE_NAV_CASES)('$id：菜单项路径唯一且以模块 route_prefix 为前缀', ({ prefix, navItems }) => {
    const paths = menuPaths(navItems)
    expect(new Set(paths).size).toBe(paths.length)
    expect(paths.filter((path) => !path.startsWith(`${prefix}/`))).toEqual([])
  })

  it.each(MODULE_NAV_CASES)('$id：子路由声明 navItems 的条目为 0（防路线元信息覆盖）', ({ routes }) => {
    expect(findNavItemsOverrides(routes)).toEqual([])
  })

  it('navItems 覆盖检查非空化自检：合成违规子路由必须被检出', () => {
    const violating = [
      { path: 'models', meta: { navItems: [{ label: '越权覆盖', items: [] }] } },
      { path: 'list', meta: { title: '正常' } },
    ] as unknown as RouteRecordRaw[]
    expect(findNavItemsOverrides(violating)).toEqual(['models'])
  })
})
