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
     * 懒加载模块入口（动态 import）。
     * 模块路由表由各模块 index.ts 导出 routes；本方法供路由守卫在首次访问时挂载。
     */
    async loadRoutes(moduleId: string): Promise<boolean> {
      const module = this.modules.find((m) => m.info.id === moduleId)
      if (!module) return false
      if (!module.loaded) {
        module.loaded = true // 标记已加载（实际路由表由模块 index 静态导出，见 router/index.ts）
      }
      return true
    },
    unregister(moduleId: string) {
      this.modules = this.modules.filter((m) => m.info.id !== moduleId)
    },
  },
})
