/**
 * 统一 HTTP 客户端：JWT 注入 + 401 静默刷新 + ErrorResponse 契约映射（RT-204）
 */
import axios, { AxiosError, type AxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import { classifyError, type ApiErrorKind } from './error'
import { redirectToLogin } from './redirect'

export interface ErrorResponse {
  code: string
  message: string
  detail: string | null
  request_id: string
}

/** 拦截器在错误对象上标记的分类结果（供页面消费，见 §2.4） */
export interface ApiErrorWithKind extends AxiosError<ErrorResponse> {
  bizKind?: ApiErrorKind
}

export interface ApiSuccess<T> {
  code: number
  message: string
  data: T
}

const TOKEN_KEY = 'ob_access_token'
const REFRESH_KEY = 'ob_refresh_token'

/**
 * C-11 人工测试模式（方案 §5 批 2）：URL 查询参数或 localStorage 开启时，
 * 为每个请求注入 X-Test-Case-Id / X-Test-Step-Id / X-Test-Run-Id 三个非身份测试头。
 * 关闭时零注入（不改动既有请求行为）。头取值口径对齐 audit/_extract_test_context。
 */
export const TEST_MODE_KEY = 'ob_test_mode'
export const TEST_CASE_KEY = 'ob_test_case_id'
export const TEST_STEP_KEY = 'ob_test_step_id'
export const TEST_RUN_KEY = 'ob_test_run_id'

export interface TestCaseHeaders {
  'X-Test-Case-Id'?: string
  'X-Test-Step-Id'?: string
  'X-Test-Run-Id'?: string
}

/**
 * 解析当前应注入的测试头。
 * 开启条件：URL 携带 `?test_case=` 或 localStorage `ob_test_mode==='1'`。
 * URL 参数优先于 localStorage；均未提供对应值时该头不注入。
 *
 * @param search URL query 串（`?a=b`；测试可显式注入，缺省读当前 location.search）
 */
export function resolveTestCaseHeaders(search: string = ''): TestCaseHeaders {
  const fromUrl = new URLSearchParams(search)
  const urlCase = fromUrl.get('test_case')
  const modeOn = typeof localStorage === 'undefined' ? false : localStorage.getItem(TEST_MODE_KEY) === '1'
  if (!urlCase && !modeOn) return {}

  const caseId = urlCase || (typeof localStorage !== 'undefined' ? localStorage.getItem(TEST_CASE_KEY) : '') || ''
  const headers: TestCaseHeaders = {}
  if (caseId) headers['X-Test-Case-Id'] = caseId

  const urlStep = fromUrl.get('test_step')
  const step = urlStep || (typeof localStorage !== 'undefined' ? localStorage.getItem(TEST_STEP_KEY) : '') || ''
  if (step) headers['X-Test-Step-Id'] = step

  const urlRun = fromUrl.get('test_run')
  const run = urlRun || (typeof localStorage !== 'undefined' ? localStorage.getItem(TEST_RUN_KEY) : '') || ''
  if (run) headers['X-Test-Run-Id'] = run

  return headers
}

export const tokenStore = {
  get access() { return localStorage.getItem(TOKEN_KEY) || '' },
  get refresh() { return localStorage.getItem(REFRESH_KEY) || '' },
  set(access: string, refresh?: string) {
    localStorage.setItem(TOKEN_KEY, access)
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_KEY)
  },
}

const http = axios.create({ baseURL: '/api/v1', timeout: 15000 })

http.interceptors.request.use((config) => {
  const token = tokenStore.access
  if (token) config.headers.Authorization = `Bearer ${token}`
  // C-11 测试模式：URL ?test_case= 或 localStorage ob_test_mode=1 → 注入测试头；关闭时零影响
  const testHeaders = resolveTestCaseHeaders(
    typeof window !== 'undefined' ? window.location.search : '',
  )
  for (const [key, value] of Object.entries(testHeaders)) {
    ;(config.headers as Record<string, string>)[key] = value
  }
  return config
})

/** 认证公共端点：其 401 属正常业务失败（如密码错误），不参与「会话失效收敛」 */
const AUTH_PUBLIC_ENDPOINTS = ['/auth/login', '/auth/refresh', '/auth/oidc/authorize']

function isAuthEndpoint(url?: string): boolean {
  if (!url) return false
  return AUTH_PUBLIC_ENDPOINTS.some((endpoint) => url.includes(endpoint))
}

/** 在错误对象上标记分类结果（供页面按 kind 渲染） */
function markKind(error: AxiosError<ErrorResponse>, kind: ApiErrorKind): void {
  ;(error as ApiErrorWithKind).bizKind = kind
}

let refreshing: Promise<string> | null = null

async function refreshAccessToken(): Promise<string> {
  const { data } = await axios.post<ApiSuccess<{ access_token: string }>>(
    '/api/v1/auth/refresh',
    { refresh_token: tokenStore.refresh },
  )
  tokenStore.set(data.data.access_token)
  return data.data.access_token
}

/**
 * 单飞刷新（S6-T4-2）：并发 401 复用同一 refresh 任务，成功后自动复位，
 * 使后续新一轮 401 可再次刷新（失败时 token 已清空 → 不会进入刷新分支，故不循环）。
 */
async function ensureRefreshed(): Promise<string> {
  if (!refreshing) {
    refreshing = refreshAccessToken().finally(() => {
      refreshing = null
    })
  }
  return refreshing
}

/** 会话失效收敛：清态 + SPA 内 replace 到登录页（保留站内 redirect） */
function convergeToLogin(error: AxiosError<ErrorResponse>): Promise<never> {
  tokenStore.clear()
  markKind(error, 'unauthorized')
  redirectToLogin()
  return Promise.reject(error)
}

http.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ErrorResponse>) => {
    // 主动取消（点击停止 / 组件卸载 / 新请求抢占，AbortController.abort()）
    // 在浏览器侧表现为 net::ERR_ABORTED，axios 抛出 CanceledError 拒绝。
    // 这类「取消」不是请求失败，直接透传给调用方（依据 signal.aborted 自行处理），
    // 不弹全局错误提示，避免与停止生成等预期行为混淆。
    if (axios.isCancel(error) || error.code === AxiosError.ERR_CANCELED) {
      return Promise.reject(error)
    }

    const original = (error.config ?? {}) as AxiosRequestConfig & { _retry?: boolean }
    const status = error.response?.status
    const body = error.response?.data

    // 401 会话失效（S6-T4-1/2）：静默刷新单飞 + 重放一次；刷新失败或无 refresh 凭证 → 收敛登录
    if (status === 401 && !isAuthEndpoint(original.url)) {
      if (!original._retry && tokenStore.refresh) {
        original._retry = true
        try {
          const token = await ensureRefreshed()
          original.headers = { ...original.headers, Authorization: `Bearer ${token}` }
          return http(original)
        } catch {
          // 刷新失败（含超时/网络异常）→ 清态收敛登录，不重试、不循环、不白屏
          return convergeToLogin(error)
        }
      }
      // 无 refresh 凭证，或重放后仍 401 → 直接收敛登录（上限一次刷新，防无限循环）
      return convergeToLogin(error)
    }

    const message = body?.message || error.message || '请求失败'
    // 统一错误分类（§2.4）：页面按 kind 呈现；403/404/401 默认不弹全局 toast（由页面级提示承载），
    // 5xx/网络/未知仍弹全局 toast 保证可观测。
    const classified = classifyError(error)
    markKind(error, classified.kind)
    if (classified.kind !== 'forbidden' && classified.kind !== 'not-found' && classified.kind !== 'unauthorized') {
      ElMessage.error(message)
    }
    return Promise.reject(error)
  },
)

export function isApiError(error: unknown): error is AxiosError<ErrorResponse> {
  return axios.isAxiosError(error)
}

export { http }
