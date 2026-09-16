/**
 * S6-T2 模块导航壳断言（设计草案 §4.2 设计说明 1~5）
 *
 * 断言口径：
 * - S6-T2-1：深链/刷新时模块路由必达（含 `registry.initialized=true` 但未装载的缺陷场景）；
 * - S6-T2-2：模块来源唯一（`/modules` + 权限过滤），禁用模块 / 无权模块不可达且不进菜单；
 * - S6-T2-3：顶层导航高亮与当前路由一致（模块子页回退到 `route_prefix`）、图标映射覆盖 + 回退；
 * - S6-T2-4：装载幂等（连续调用路由表稳定）、`console.warn` = 0、`ModuleLayout` 空态兜底。
 *
 * 用例预算（DEF-FE-146-003 根因收口）：挂载 `AppLayout` / `ModuleLayout`（el-menu 三层 + 图标 +
 * 平台四域叶子）的用例实测单条 4~8s；`v8` 覆盖率插桩后放大约 4.7 倍，默认 5s 用例超时会随机击杀
 * 其中一条（Step 4 证据：本文件 1 条 `Test timed out in 5000ms`）。故对**整壳挂载**用例按用例显式
 * 声明 15000ms 预算，未放宽全局 `testTimeout`；不挂载壳的路由/注册表用例保持默认预算。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, type Router } from 'vue-router'
import { createPinia, setActivePinia, type Pinia } from 'pinia'
import { mount, type VueWrapper } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { h, type Component } from 'vue'
import {
  ChatDotRound,
  Collection,
  Connection,
  Memo,
  Odometer,
  OfficeBuilding,
  User,
} from '@element-plus/icons-vue'
import AppLayout from '@/core/layouts/AppLayout.vue'
import ModuleLayout from '@/core/layouts/ModuleLayout.vue'
import { bootstrapModuleRoutes, createAppRouter, findNavItemsOverrides } from '@/core/router'
import { useModuleRegistry } from '@/core/stores/moduleRegistry'
import { useAuthStore } from '@/core/stores/auth'
import { tokenStore } from '@/core/api/http'
import { modulesApi, type ModuleInfo } from '@/core/api/auth'

let pinia: Pinia

const MODULE_INFOS: ModuleInfo[] = [
  { id: 'openllm', name: 'OpenLLM', icon: 'ChatDotRound', route_prefix: '/openllm', entry: 'x', permission: 'openllm:view', status: 'enabled', sort_order: 10 },
  { id: 'knowledge', name: '知识库', icon: 'Collection', route_prefix: '/knowledge', entry: 'x', permission: 'openrag:view', status: 'enabled', sort_order: 20 },
  { id: 'memory', name: '记忆', icon: 'Memo', route_prefix: '/memory', entry: 'x', permission: 'openmemory:view', status: 'enabled', sort_order: 30 },
  { id: 'portrait', name: '画像', icon: 'User', route_prefix: '/portrait', entry: 'x', permission: 'dps:view', status: 'enabled', sort_order: 40 },
  { id: 'gateway', name: '网关', icon: 'Connection', route_prefix: '/gateway', entry: 'x', permission: 'gateway:view', status: 'enabled', sort_order: 50 },
]

function loginWith(permissions: string[]) {
  tokenStore.set('access-token')
  const auth = useAuthStore()
  auth.user = { id: 1, username: 'tester', permissions }
  auth.loaded = true
  return auth
}

function mountWith(component: Component, router: Router): VueWrapper {
  return mount(component, {
    global: {
      plugins: [ElementPlus, router, pinia],
      stubs: { RouterView: true },
    },
  })
}

/** 图标签名：取 svg 内 path 的 `d` 数据，规避 scoped 属性差异 */
function iconSignature(html: string): string {
  return (html.match(/ d="[^"]*"/g) || []).join('|')
}

function standaloneIconSignature(icon: Component): string {
  return iconSignature(mount({ render: () => h(icon) }).html())
}

beforeEach(() => {
  localStorage.clear()
  tokenStore.clear()
  pinia = createPinia()
  setActivePinia(pinia)
  vi.restoreAllMocks()
})

describe('S6-T2-1: 深链/刷新模块路由必达（幂等装载）', () => {
  it.each([
    ['/portrait/list', 'portrait'],
    ['/memory/sessions', 'memory'],
    ['/knowledge/chat', 'knowledge'],
    ['/openllm/conversations', 'openllm'],
  ])('registry 已初始化但未装载时，深链 %s 仍命中 %s 模块', async (target, moduleId) => {
    vi.spyOn(modulesApi, 'list').mockResolvedValue(MODULE_INFOS)
    loginWith(['*'])
    const registry = useModuleRegistry()
    await registry.init(['*'])
    // 复现缺陷前置：注册表已初始化，但模块路由尚未装载（loaded=false）
    registry.modules = registry.modules.map((module) => ({ ...module, loaded: false }))

    const { router } = createAppRouter(createMemoryHistory())
    expect(router.resolve(target).matched.length).toBe(0)

    await router.push(target)

    expect(router.currentRoute.value.path).toBe(target)
    expect(router.currentRoute.value.matched.length).toBeGreaterThan(0)
    expect(router.currentRoute.value.meta.module).toBe(moduleId)
  })
})

describe('S6-T2-2: 模块来源唯一（/modules + 权限过滤）', () => {
  it('禁用模块与无权模块不进注册表、路由不可达', async () => {
    const infos = MODULE_INFOS.map((module) =>
      module.id === 'portrait' ? { ...module, status: 'disabled' as const } : module,
    )
    vi.spyOn(modulesApi, 'list').mockResolvedValue(infos)
    loginWith(['openllm:view'])
    const registry = useModuleRegistry()
    await registry.init(['openllm:view'])

    expect(registry.enabledModules.map((module) => module.info.id)).toEqual(['openllm'])

    const { router } = createAppRouter(createMemoryHistory())
    await router.push('/knowledge/list')
    expect(router.currentRoute.value.path).toBe('/dashboard')

    await router.push('/portrait/list')
    expect(router.currentRoute.value.path).toBe('/dashboard')
  })

  it('通配权限放行全部启用模块', async () => {
    vi.spyOn(modulesApi, 'list').mockResolvedValue(MODULE_INFOS)
    loginWith(['*'])
    const registry = useModuleRegistry()
    await registry.init(['*'])
    expect(registry.enabledModules.map((module) => module.info.id)).toEqual([
      'openllm',
      'knowledge',
      'memory',
      'portrait',
      'gateway',
    ])
  })
})

describe('S6-T2-3: 导航一致性（顶层高亮 / 图标 / 权限矩阵）', () => {
  it('模块子页时顶层导航高亮回退到 route_prefix', async () => {
    vi.spyOn(modulesApi, 'list').mockResolvedValue(MODULE_INFOS)
    loginWith(['*'])
    const registry = useModuleRegistry()
    await registry.init(['*'])

    const { router } = createAppRouter(createMemoryHistory())
    await router.push('/portrait/list')
    expect(router.currentRoute.value.meta.module).toBe('portrait')

    const wrapper = mountWith(AppLayout, router)
    const menu = wrapper.findComponent({ name: 'ElMenu' })
    expect(menu.props('defaultActive')).toBe('/portrait')
  }, 15000)

  it('三层菜单：顶层 + 权限过滤业务模块 + 平台四域（gateway 迁出、平台受限叶子按权限码裁剪）', async () => {
    const infos = MODULE_INFOS.map((module) =>
      module.id === 'portrait' ? { ...module, status: 'disabled' as const } : module,
    )
    vi.spyOn(modulesApi, 'list').mockResolvedValue(infos)
    loginWith(['openllm:view', 'openrag:view']) // 无 '*'：业务模块按权限码、平台受限叶子按权限码裁剪
    const registry = useModuleRegistry()
    await registry.init(['openllm:view', 'openrag:view'])

    const { router } = createAppRouter(createMemoryHistory())
    await router.push('/knowledge/list')

    const wrapper = mountWith(AppLayout, router)
    const texts = wrapper.findAll('.el-menu-item').map((item) => item.text())
    // 顶层：仪表盘 + 个人设置（无权限码恒可见）
    expect(texts).toContain('仪表盘')
    expect(texts).toContain('个人设置')
    // 业务模块：仅 openllm + knowledge（memory/portrait 权限不足、portrait 停用、gateway 已迁出）
    expect(texts).toContain('OpenLLM')
    expect(texts).toContain('知识库')
    expect(texts).not.toContain('记忆')
    expect(texts).not.toContain('画像')
    expect(texts).not.toContain('网关')
    // 平台受限叶子按权限码裁剪（缺失则菜单不可见，与路由守卫/接口 403 同源）
    expect(texts).not.toContain('日志中心') // 缺 log:read
    expect(texts).not.toContain('测试记录') // 缺 test:record
    expect(texts).not.toContain('模块开关') // 缺 module:manage
    // 平台非受限叶子仍可见（迁移后原系统页可达）
    expect(texts).toContain('租户管理')
    expect(texts).toContain('全局配置')
    // 模块子页高亮回退到 route_prefix
    expect(wrapper.findComponent({ name: 'ElMenu' }).props('defaultActive')).toBe('/knowledge')
  }, 15000)

  it('模块图标按 ModuleInfo.icon 映射，未命中回退 ChatDotRound', async () => {
    const iconModules: ModuleInfo[] = [
      { id: 'm-llm', name: 'OpenLLM', icon: 'ChatDotRound', route_prefix: '/m-llm', entry: 'x', permission: 'p', status: 'enabled', sort_order: 1 },
      { id: 'm-kb', name: '知识库', icon: 'Collection', route_prefix: '/m-kb', entry: 'x', permission: 'p', status: 'enabled', sort_order: 2 },
      { id: 'm-mem', name: '记忆', icon: 'Memo', route_prefix: '/m-mem', entry: 'x', permission: 'p', status: 'enabled', sort_order: 3 },
      { id: 'm-por', name: '画像', icon: 'User', route_prefix: '/m-por', entry: 'x', permission: 'p', status: 'enabled', sort_order: 4 },
      { id: 'm-gw', name: '网关', icon: 'Connection', route_prefix: '/m-gw', entry: 'x', permission: 'p', status: 'enabled', sort_order: 5 },
      { id: 'm-sys', name: '系统管理', icon: 'OfficeBuilding', route_prefix: '/m-sys', entry: 'x', permission: 'p', status: 'enabled', sort_order: 6 },
      { id: 'm-dash', name: '仪表盘模块', icon: 'Odometer', route_prefix: '/m-dash', entry: 'x', permission: 'p', status: 'enabled', sort_order: 7 },
      { id: 'm-unknown', name: '未知图标', icon: 'NoSuchModuleIcon', route_prefix: '/m-unknown', entry: 'x', permission: 'p', status: 'enabled', sort_order: 8 },
    ]
    vi.spyOn(modulesApi, 'list').mockResolvedValue(iconModules)
    loginWith(['*'])
    const registry = useModuleRegistry()
    await registry.init(['*'])

    const { router } = createAppRouter(createMemoryHistory())
    await router.push('/dashboard')
    const wrapper = mountWith(AppLayout, router)

    const svgs = wrapper.findAll('.el-menu-item .el-icon svg')
    // 扁平顺序前 10 项 = 顶层（仪表盘/个人设置）+ 业务模块（8 个，gateway 口径不缩），未命中回退 ChatDotRound
    const expectedHead: Component[] = [
      Odometer, // 顶部：仪表盘
      User, // 顶部：个人设置
      ChatDotRound, // m-llm
      Collection, // m-kb
      Memo, // m-mem
      User, // m-por
      Connection, // m-gw
      OfficeBuilding, // m-sys
      Odometer, // m-dash
      ChatDotRound, // m-unknown 未命中回退
    ]
    // 平台四域叶子在其后追加（v1.4.6 三层菜单），前项校验不因新增叶子而失效
    expect(svgs.length).toBeGreaterThanOrEqual(expectedHead.length)
    expectedHead.forEach((icon, index) => {
      expect(iconSignature(svgs[index].html())).toBe(standaloneIconSignature(icon))
    })
  }, 15000)
})

describe('S6-T2-4: 装载幂等与告警清零 / 空态兜底', () => {
  it('mountModuleRoutes 连续调用 3 次路由表规模稳定且无 console.warn', async () => {
    const warnMessages: string[] = []
    const warn = vi.spyOn(console, 'warn').mockImplementation((...args: unknown[]) => {
      warnMessages.push(args.map((arg) => String(arg)).join(' '))
    })
    vi.spyOn(modulesApi, 'list').mockResolvedValue(MODULE_INFOS)
    loginWith(['*'])
    const registry = useModuleRegistry()
    await registry.init(['*'])

    const { router, mountModuleRoutes } = createAppRouter(createMemoryHistory())
    const base = router.getRoutes().length
    await mountModuleRoutes()
    const afterFirst = router.getRoutes().length
    await mountModuleRoutes()
    await mountModuleRoutes()

    expect(afterFirst).toBeGreaterThan(base)
    expect(router.getRoutes().length).toBe(afterFirst)
    expect(warnMessages).toEqual([])
    expect(warn).not.toHaveBeenCalled()
  })

  it('ModuleLayout 在 navItems 缺失时不渲染空菜单条（空态兜底）', async () => {
    vi.spyOn(modulesApi, 'list').mockResolvedValue(MODULE_INFOS)
    loginWith(['*'])
    const registry = useModuleRegistry()
    await registry.init(['*'])

    const { router } = createAppRouter(createMemoryHistory())
    await router.push('/dashboard')
    const wrapper = mountWith(ModuleLayout, router)
    expect(router.currentRoute.value.meta.navItems).toBeUndefined()
    expect(wrapper.find('.module-menu').exists()).toBe(false)
    expect(wrapper.find('.module-content').exists()).toBe(true)
  }, 15000)

  it('ModuleLayout 在 navItems 存在时渲染二级导航分组', async () => {
    vi.spyOn(modulesApi, 'list').mockResolvedValue(MODULE_INFOS)
    loginWith(['*'])
    const registry = useModuleRegistry()
    await registry.init(['*'])
    const { router } = createAppRouter(createMemoryHistory())
    // v1.4.6 gateway 已迁出业务模块（非模块路由）；改用 openllm（仍为业务模块、具 navItems）
    await router.push('/openllm/conversations')
    const wrapper = mountWith(ModuleLayout, router)
    expect(wrapper.find('.module-menu').exists()).toBe(true)
    const groups = (router.currentRoute.value.meta.navItems as unknown[]) || []
    expect(groups.length).toBeGreaterThan(0)
  }, 15000)

  it('一致性检查非空化自检：合成违规子路由必须被检出', () => {
    expect(findNavItemsOverrides([{ path: 'x', meta: {} } as never])).toEqual([])
    expect(findNavItemsOverrides([{ path: 'y', meta: { navItems: [] } } as never])).toEqual(['y'])
  })
})

describe('S6-T2-1(B): 冷启动预热——首帧深链解析前完成模块装载（F-4 统一路由告警）', () => {
  it('未预热时首帧 resolve 深链无匹配（RED 现象：No match found 告警根因）', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => undefined)
    vi.spyOn(modulesApi, 'list').mockResolvedValue(MODULE_INFOS)
    loginWith(['*'])

    const bundle = createAppRouter(createMemoryHistory())
    // 冷启动：模块路由尚未装载，浏览器首帧 `router.resolve` 命中此分支 → vue-router 告警
    expect(bundle.router.resolve('/openllm/conversations').matched.length).toBe(0)
    expect(warn).toHaveBeenCalled()
  })

  it('预热后首帧 resolve 深链即匹配且无 console.warn（GREEN）', async () => {
    const warnMessages: string[] = []
    vi.spyOn(console, 'warn').mockImplementation((...args: unknown[]) => {
      warnMessages.push(args.map((arg) => String(arg)).join(' '))
    })
    vi.spyOn(modulesApi, 'list').mockResolvedValue(MODULE_INFOS)
    loginWith(['*'])

    const bundle = createAppRouter(createMemoryHistory())
    await bootstrapModuleRoutes(bundle)

    for (const target of ['/openllm/conversations', '/knowledge/chat', '/memory/sessions', '/portrait/list']) {
      expect(bundle.router.resolve(target).matched.length).toBeGreaterThan(0)
    }
    expect(warnMessages).toEqual([])
  })

  it('无登录态时预热直接返回（公共路由即可，不触碰模块 API）', async () => {
    const listSpy = vi.spyOn(modulesApi, 'list').mockResolvedValue(MODULE_INFOS)
    const bundle = createAppRouter(createMemoryHistory())
    await bootstrapModuleRoutes(bundle)
    expect(listSpy).not.toHaveBeenCalled()
    expect(bundle.router.resolve('/auth/login').matched.length).toBeGreaterThan(0)
  })
})
