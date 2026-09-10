import { defineStore } from 'pinia'
import { modulesApi, type ModuleInfo } from '@/core/api/auth'

/**
 * 动态模块注册（RT-203）：manifest 注册表 + 懒加载入口 + 权限过滤
 */
export interface RegisteredModule {
  info: ModuleInfo
  loaded: boolean
}

export const useModuleRegistry = defineStore('moduleRegistry', {
  state: () => ({
    modules: [] as RegisteredModule[],
    initialized: false,
  }),
  getters: {
    enabledModules: (state) => state.modules.filter((m) => m.info.status === 'enabled'),
  },
  actions: {
    async init(permissions: string[]) {
      if (this.initialized) return
      const items = await modulesApi.list()
      const all = permissions.includes('*')
      this.modules = items
        .filter((m) => all || permissions.includes(m.permission))
        .map((info) => ({ info, loaded: false }))
      this.initialized = true
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
    unregister(moduleId: string) {
      this.modules = this.modules.filter((m) => m.info.id !== moduleId)
    },
  },
})
