import { defineStore } from 'pinia'
import { authApi, type AuthUser } from '@/core/api/auth'
import { tokenStore } from '@/core/api/http'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null as AuthUser | null,
    loaded: false,
  }),
  getters: {
    isAuthenticated: (state) => state.user !== null || tokenStore.access !== '',
    permissions: (state): string[] => state.user?.permissions ?? [],
  },
  actions: {
    async login(username: string, password: string) {
      this.user = await authApi.login(username, password)
      this.loaded = true
    },
    async loadMe() {
      if (!tokenStore.access) {
        this.loaded = true
        return
      }
      try {
        this.user = await authApi.me()
      } catch {
        // 刷新失败由拦截器处理跳转
      } finally {
        this.loaded = true
      }
    },
    hasPermission(permission: string): boolean {
      const perms = this.permissions
      return perms.includes('*') || perms.includes(permission)
    },
    logout() {
      tokenStore.clear()
      this.user = null
    },
  },
})
