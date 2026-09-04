/**
 * 统一 HTTP 客户端：JWT 注入 + 401 静默刷新 + ErrorResponse 契约映射（RT-204）
 */
import axios, { AxiosError, type AxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'

export interface ErrorResponse {
  code: string
  message: string
  detail: string | null
  request_id: string
}

export interface ApiSuccess<T> {
  code: number
  message: string
  data: T
}

const TOKEN_KEY = 'ob_access_token'
const REFRESH_KEY = 'ob_refresh_token'

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
  return config
})

let refreshing: Promise<string> | null = null

async function refreshAccessToken(): Promise<string> {
  const { data } = await axios.post<ApiSuccess<{ access_token: string }>>(
    '/api/v1/auth/refresh',
    { refresh_token: tokenStore.refresh },
  )
  tokenStore.set(data.data.access_token)
  return data.data.access_token
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

    const original = error.config as AxiosRequestConfig & { _retry?: boolean }
    const status = error.response?.status
    const body = error.response?.data

    // 401 静默刷新（仅一次）
    if (status === 401 && !original._retry && tokenStore.refresh) {
      original._retry = true
      try {
        refreshing = refreshing || refreshAccessToken()
        const token = await refreshing
        refreshing = null
        original.headers = { ...original.headers, Authorization: `Bearer ${token}` }
        return http(original)
      } catch {
        refreshing = null
        tokenStore.clear()
        window.location.href = '/auth/login'
      }
    }

    const message = body?.message || error.message || '请求失败'
    ElMessage.error(message)
    return Promise.reject(error)
  },
)

export function isApiError(error: unknown): error is AxiosError<ErrorResponse> {
  return axios.isAxiosError(error)
}

export { http }
