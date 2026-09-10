/**
 * S6-T4 FE-R1-2 登录态 / 吊销回归（设计草案 §4.4 + §5.1 契约与呈现规范）
 *
 * 断言口径（S6-T4-1 ~ S6-T4-4）：
 * - S6-T4-1：token 失效/吊销 → SPA 收敛 `/auth/login` 且回跳参数为**站内路径**；
 *   恶意 redirect（协议相对 `//`、绝对 URL `http(s)://`、伪协议 `javascript:` 等）一律回落 `/dashboard`；
 * - S6-T4-2：401 收敛目标由 SPA 导航器承载；`redirect`/`request_id`/token 不落入 URL 与 localStorage；
 * - S6-T4-3：OIDC 回调成功后清空 `window.location.hash`（防令牌残留）；缺令牌/IdP 错误 → 可重试错误页（非白屏）；
 * - S6-T4-4：`loadMe` 失败可观测（Q-S6-D2：`loaded=true` + `loadError`，不静默清态）。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'
import { createPinia, setActivePinia, type Pinia } from 'pinia'

import {
  DEFAULT_REDIRECT,
  LOGIN_PATH,
  currentInternalPath,
  registerLoginNavigator,
  redirectToLogin,
  resolveLoginTarget,
  safeRedirect,
  type LoginNavigateTarget,
} from '@/core/api/redirect'
import { tokenStore } from '@/core/api/http'
import { authApi } from '@/core/api/auth'
import { useAuthStore } from '@/core/stores/auth'
import Login from '@/pages/Login.vue'
import OidcCallback from '@/pages/OidcCallback.vue'

let pinia: Pinia
let navigatorSpy: ReturnType<typeof vi.fn>

beforeEach(() => {
  localStorage.clear()
  tokenStore.clear()
  vi.restoreAllMocks()
  pinia = createPinia()
  setActivePinia(pinia)
  navigatorSpy = vi.fn()
  registerLoginNavigator(navigatorSpy as unknown as (target: LoginNavigateTarget) => void)
  window.history.replaceState(null, '', '/')
})

describe('S6-T4-1: safeRedirect 站内回跳校验', () => {
  it('拒绝 4 类外链/协议注入（协议相对 / 绝对 http(s) / 伪协议 javascript）', () => {
    const malicious = [
      '//evil.example.com/steal',
      'https://evil.example.com/steal',
      'http://evil.example.com',
      'javascript:alert(document.cookie)',
    ]
    for (const value of malicious) {
      expect(safeRedirect(value)).toBe(DEFAULT_REDIRECT)
    }
  })

  it('拒绝编码绕过 / 反斜杠 / 控制字符 / 超长 / 非字符串 / 非站内相对路径', () => {
    expect(safeRedirect('/%2F%2Fevil.example.com')).toBe(DEFAULT_REDIRECT)
    expect(safeRedirect('/\\evil.example.com')).toBe(DEFAULT_REDIRECT)
    expect(safeRedirect('/a\u0000b')).toBe(DEFAULT_REDIRECT)
    // 非法百分号编码 → decodeURIComponent 抛 URIError，按非法输入回落
    expect(safeRedirect('/%')).toBe(DEFAULT_REDIRECT)
    expect(safeRedirect('/%E0%A4%A')).toBe(DEFAULT_REDIRECT)
    expect(safeRedirect(`/${'a'.repeat(600)}`)).toBe(DEFAULT_REDIRECT)
    expect(safeRedirect(undefined)).toBe(DEFAULT_REDIRECT)
    expect(safeRedirect(null)).toBe(DEFAULT_REDIRECT)
    expect(safeRedirect(123)).toBe(DEFAULT_REDIRECT)
    expect(safeRedirect('')).toBe(DEFAULT_REDIRECT)
    expect(safeRedirect('   ')).toBe(DEFAULT_REDIRECT)
    expect(safeRedirect('dashboard')).toBe(DEFAULT_REDIRECT)
    expect(safeRedirect('/javascript:alert(1)')).toBe(DEFAULT_REDIRECT)
    expect(safeRedirect('/data:text/html,<script>')).toBe(DEFAULT_REDIRECT)
  })

  it('保留站内相对路径（含 query / hash / 首尾空白规范化）', () => {
    expect(safeRedirect('/portrait/list')).toBe('/portrait/list')
    expect(safeRedirect('/knowledge/list?page=2')).toBe('/knowledge/list?page=2')
    expect(safeRedirect('/memory/sessions#top')).toBe('/memory/sessions#top')
    expect(safeRedirect('  /dashboard  ')).toBe('/dashboard')
    expect(safeRedirect('/')).toBe('/')
  })
})

describe('S6-T4-1: 401 收敛登录目标（SPA 路径 + 站内 redirect）', () => {
  it('resolveLoginTarget 生成 /auth/login + 站内 redirect；非法值回落 /dashboard', () => {
    expect(resolveLoginTarget('/portrait/list')).toEqual({ path: LOGIN_PATH, query: { redirect: '/portrait/list' } })
    expect(resolveLoginTarget('//evil.example.com')).toEqual({ path: LOGIN_PATH, query: { redirect: DEFAULT_REDIRECT } })
    expect(resolveLoginTarget('https://evil.example.com')).toEqual({
      path: LOGIN_PATH,
      query: { redirect: DEFAULT_REDIRECT },
    })
  })

  it('redirectToLogin 经注册的 SPA 导航器收敛（非整页跳转）', () => {
    const target = redirectToLogin('/portrait/list?tab=1')
    expect(navigatorSpy).toHaveBeenCalledWith(target)
    expect(target.path).toBe(LOGIN_PATH)
    expect(target.query.redirect).toBe('/portrait/list?tab=1')
  })

  it('currentInternalPath 仅返回站内 path + query（不含 hash，防令牌残留）', () => {
    window.history.replaceState(null, '', '/portrait/list?tab=1#access_token=leak-token')
    const path = currentInternalPath()
    expect(path).toBe('/portrait/list?tab=1')
    expect(path).not.toContain('access_token')
    expect(path).not.toContain('leak-token')
  })
})

describe('S6-T4-1: 登录成功按 safeRedirect 回跳', () => {
  async function mountLogin(query: string): Promise<{ router: Router; wrapper: VueWrapper }> {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/auth/login', component: Login },
        { path: '/dashboard', component: { template: '<div>dash</div>' } },
        { path: '/portrait/list', component: { template: '<div>list</div>' } },
      ],
    })
    await router.push(`/auth/login${query}`)
    const wrapper = mount(Login, { global: { plugins: [ElementPlus, router, pinia] } })
    await flushPromises()
    vi.spyOn(useAuthStore(), 'login').mockResolvedValue(undefined as never)
    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('admin')
    await inputs[1].setValue('admin123')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    return { router, wrapper }
  }

  it('合法站内 redirect → 回跳目标页', async () => {
    const { router } = await mountLogin('?redirect=/portrait/list')
    expect(router.currentRoute.value.path).toBe('/portrait/list')
  }, 15000)

  it('恶意 redirect（协议相对）→ 回落 /dashboard', async () => {
    const { router } = await mountLogin('?redirect=//evil.example.com/steal')
    expect(router.currentRoute.value.path).toBe('/dashboard')
  }, 15000)

  it('恶意 redirect（javascript 伪协议，编码形式）→ 回落 /dashboard', async () => {
    const { router } = await mountLogin('?redirect=javascript%3Aalert(1)')
    expect(router.currentRoute.value.path).toBe('/dashboard')
  }, 15000)

  it('无 redirect 参数 → 回跳 /dashboard', async () => {
    const { router } = await mountLogin('')
    expect(router.currentRoute.value.path).toBe('/dashboard')
  }, 15000)
})

describe('S6-T4-3: OIDC 回调与状态清理', () => {
  async function mountOidc(fragment: string, query = ''): Promise<{ router: Router; wrapper: VueWrapper }> {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/auth/oidc/callback', component: OidcCallback },
        { path: '/auth/login', component: { template: '<div>login</div>' } },
        { path: '/dashboard', component: { template: '<div>dash</div>' } },
        { path: '/portrait/list', component: { template: '<div>list</div>' } },
      ],
    })
    await router.push(`/auth/oidc/callback${query}`)
    window.history.replaceState(null, '', `/auth/oidc/callback${query}${fragment}`)
    const wrapper = mount(OidcCallback, { global: { plugins: [ElementPlus, router, pinia] } })
    await flushPromises()
    return { router, wrapper }
  }

  it('回调成功 → 落 token、清空 hash（无令牌残留于地址栏）、replace 目标页', async () => {
    const { router } = await mountOidc('#access_token=at-oidc&refresh_token=rt-oidc')
    expect(tokenStore.access).toBe('at-oidc')
    expect(window.location.hash).toBe('')
    expect(window.location.href).not.toContain('access_token')
    expect(window.location.href).not.toContain('at-oidc')
    expect(router.currentRoute.value.path).toBe('/dashboard')
  }, 15000)

  it('回调成功按站内 redirect 回跳；恶意 redirect 回落 /dashboard', async () => {
    const safe = await mountOidc('#access_token=at-2', '?redirect=/portrait/list')
    expect(safe.router.currentRoute.value.path).toBe('/portrait/list')

    localStorage.clear()
    tokenStore.clear()
    const malicious = await mountOidc('#access_token=at-3', '?redirect=//evil.example.com')
    expect(malicious.router.currentRoute.value.path).toBe('/dashboard')
  }, 15000)

  it('IdP 回传错误（code/state 校验失败）→ 可重试错误页并清理 hash（无令牌残留）', async () => {
    const { wrapper } = await mountOidc('#error=access_denied&error_description=user%20denied&state=bad')
    expect(wrapper.find('[data-test="oidc-error"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('OIDC 回调失败')
    expect(wrapper.text()).toContain('user denied')
    expect(wrapper.find('[data-test="oidc-back-login"]').exists()).toBe(true)
    expect(window.location.hash).toBe('')
    expect(wrapper.text().trim().length).toBeGreaterThan(0)
  }, 15000)

  it('缺令牌且无 error → 错误页（提示缺少令牌）非白屏', async () => {
    const { wrapper } = await mountOidc('')
    expect(wrapper.find('[data-test="oidc-error"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('缺少令牌')
    expect(wrapper.find('[data-test="oidc-back-login"]').exists()).toBe(true)
  }, 15000)
})

describe('S6-T4-4 / Q-S6-D2: loadMe 失败可观测且不静默清态', () => {
  it('loadMe 失败 → loaded=true + loadError 可观测 + 登录态保留（不清态）', async () => {
    tokenStore.set('access-keep', 'refresh-keep')
    vi.spyOn(authApi, 'me').mockRejectedValue(new Error('me boom'))
    const store = useAuthStore()
    await store.loadMe()
    expect(store.loaded).toBe(true)
    expect(store.loadError).toBeTruthy()
    expect(store.user).toBeNull()
    expect(tokenStore.access).toBe('access-keep')
    expect(tokenStore.refresh).toBe('refresh-keep')
  })

  it('loadMe 成功 → 写入用户并清空 loadError', async () => {
    tokenStore.set('access-x', 'refresh-x')
    vi.spyOn(authApi, 'me').mockResolvedValue({ id: 1, username: 'admin', permissions: ['*'] })
    const store = useAuthStore()
    await store.loadMe()
    expect(store.user?.username).toBe('admin')
    expect(store.loadError).toBeNull()
  })

  it('无 token → 不请求 /auth/me，直接 loaded=true', async () => {
    const meSpy = vi.spyOn(authApi, 'me')
    const store = useAuthStore()
    await store.loadMe()
    expect(meSpy).not.toHaveBeenCalled()
    expect(store.loaded).toBe(true)
  })

  it('logout → 清空 token / 用户态 / loadError', async () => {
    tokenStore.set('access-x', 'refresh-x')
    vi.spyOn(authApi, 'me').mockRejectedValue(new Error('boom'))
    const store = useAuthStore()
    await store.loadMe()
    store.logout()
    expect(store.user).toBeNull()
    expect(store.loadError).toBeNull()
    expect(tokenStore.access).toBe('')
    expect(tokenStore.refresh).toBe('')
  })
})
