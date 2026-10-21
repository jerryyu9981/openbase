import { defineStore } from 'pinia'
import { authApi, type AuthUser } from '@/core/api/auth'
import { tokenStore } from '@/core/api/http'
import { describeError } from '@/core/api/error'

/**
 * 在途去重（v1.4.11）：bootstrap 预热与路由守卫会并发调用 `loadMe`，
 * 后端慢时会产生重复请求并叠加超时（实测白屏 30s+），此处合并为一次。
 */
let loadMeInFlight: Promise<void> | null = null

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null as AuthUser | null,
    loaded: false,
    /** 用户信息加载失败原因（Q-S6-D2：失败可观测，供页面呈现阻断提示） */
    loadError: null as string | null,
  }),
  getters: {
    isAuthenticated: (state) => state.user !== null || tokenStore.access !== '',
    permissions: (state): string[] => state.user?.permissions ?? [],
  },
  actions: {
    async login(username: string, password: string) {
      this.user = await authApi.login(username, password)
      this.loadError = null
      this.loaded = true
    },
    async loadMe() {
      if (!tokenStore.access) {
        this.loaded = true
        return
      }
      if (this.loaded) return
      if (loadMeInFlight) return loadMeInFlight
      loadMeInFlight = this._loadMe().finally(() => {
        loadMeInFlight = null
      })
      return loadMeInFlight
    },
    async _loadMe() {
      try {
        this.user = await authApi.me()
        this.loadError = null
      } catch (error) {
        // Q-S6-D2（S6-T4-4）：失败置 loaded=true + 记录 loadError 供页面呈现阻断提示；
        // 不静默清空登录态——token 失效由 401 收敛逻辑统一处置（清态 + SPA 跳登录）。
        this.user = null
        this.loadError = describeError(error).detail || '用户信息加载失败'
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
      this.loadError = null
    },
  },
})
