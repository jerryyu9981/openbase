import { defineStore } from 'pinia'
import { modulesApi, type ModuleInfo } from '@/core/api/auth'

/**
 * 动态模块注册（RT-203）：manifest 注册表 + 懒加载入口 + 权限过滤
 */
export interface RegisteredModule {
  info: ModuleInfo
  loaded: boolean
}

/**
 * 在途去重（v1.4.11）：bootstrap 预热与路由守卫会并发 `init`，后端慢时会重复请求，
 * 合并为一次并在成功后同步模块路由，避免「注册表已就绪但路由未装载」。
 */
let initInFlight: Promise<void> | null = null
/** 模块清单预取（v1.4.11）：不依赖权限，可与 `/auth/me` 并行发起，缩短首屏等待 */
let listInFlight: Promise<ModuleInfo[]> | null = null

export const useModuleRegistry = defineStore('moduleRegistry', {
  state: () => ({
    modules: [] as RegisteredModule[],
    initialized: false,
    /** 已解析的模块清单缓存（v1.4.11）：启动预取结果供 init 复用，避免重复请求 */
    listCache: null as ModuleInfo[] | null,
  }),
  getters: {
    enabledModules: (state) => state.modules.filter((m) => m.info.status === 'enabled'),
  },
  actions: {
    /** 预取模块清单（与 `/auth/me` 并行；结果缓存供 init 复用，失败不缓存） */
    prefetch(force = false): Promise<ModuleInfo[]> {
      if (!force && this.listCache) return Promise.resolve(this.listCache)
      if (!listInFlight) {
        listInFlight = modulesApi.list()
          .then((items) => {
            this.listCache = items
            return items
          })
          .finally(() => {
            listInFlight = null
          })
      }
      return listInFlight
    },
    async init(permissions: string[]) {
      if (this.initialized) return
      if (initInFlight) return initInFlight
      initInFlight = this._init(permissions).finally(() => {
        initInFlight = null
      })
      return initInFlight
    },
    async _init(permissions: string[]) {
      const items = await this.prefetch()
      const all = permissions.includes('*')
      this.modules = items
        .filter((m) => all || permissions.includes(m.permission))
        .map((info) => ({ info, loaded: false }))
      this.initialized = true
      // 注册表就绪即同步路由：即使 init 在导航之后才完成，模块页也随即可达
      const enabledIds = new Set(
        items.filter((m) => m.status === 'enabled').map((m) => m.id),
      )
      const { syncModuleRoutes } = await import('@/core/router')
      await syncModuleRoutes(enabledIds)
    },
    /**
     * 懒加载模块入口：委托真实装载（`router/index.ts` 的 `mountModuleRoutes`，单一实现）。
     *
     * 动态 import 规避 `router/index.ts` ↔ 本 store 的循环依赖；返回值语义 =
     * 「该模块路由当前已装载」（模块不存在 / 被禁用 / 装载失败时为 false）。
     */
    async loadRoutes(moduleId: string): Promise<boolean> {
      const module = this.modules.find((m) => m.info.id === moduleId)
      if (!module) return false
      if (!module.loaded) {
        const { mountModuleRoutes } = await import('@/core/router')
        await mountModuleRoutes()
      }
      return module.loaded
    },
    /**
     * 重新拉取模块注册表并同步路由（v1.4.11：模块开关**即时生效**）。
     *
     * 后端仍以 `effective=next_login` 记录审计语义，但前端在切换成功后立即：
     * 重建注册表 → 卸载停用模块路由 → 装载启用模块路由，侧栏菜单随之增删。
     */
    async reload(permissions: string[]) {
      // 开关状态已变化：强制重新拉取（忽略启动缓存）
      const items = await this.prefetch(true)
      const all = permissions.includes('*')
      const previousLoaded = new Map(this.modules.map((m) => [m.info.id, m.loaded]))
      this.modules = items
        .filter((m) => all || permissions.includes(m.permission))
        .map((info) => ({ info, loaded: previousLoaded.get(info.id) ?? false }))
      this.initialized = true
      const enabledIds = new Set(
        items.filter((m) => m.status === 'enabled').map((m) => m.id),
      )
      const { syncModuleRoutes } = await import('@/core/router')
      await syncModuleRoutes(enabledIds)
    },
    unregister(moduleId: string) {
      this.modules = this.modules.filter((m) => m.info.id !== moduleId)
    },
  },
})
