/**
 * 登录态收敛导航 + 站内回跳安全校验（S6 设计草案 §4.4 / §5.1）
 *
 * 职责：
 * 1. `safeRedirect()`：把外部输入的 `redirect` 参数收敛为**站内相对路径**——拒绝协议相对
 *    （`//host`）、绝对 URL（`http(s)://`）、伪协议（`javascript:` / `data:` 等）以及
 *    反斜杠、编码绕过、控制字符与超长串，防止开放重定向与协议注入；
 * 2. 401 收敛导航：以「注册式导航器」解耦拦截器与路由器（避免 `http.ts` ↔ `router`
 *    循环依赖），由 `core/router/index.ts` 注册 `router.replace`，实现 SPA 内跳转
 *    （R-7 口径：替代整页 `window.location.href`）。
 *
 * 约束（§5.1）：`redirect` 仅保留站内 path + query（**天然不含 hash**，避免 OIDC 令牌
 * 残留进 URL/历史），不携带 `request_id`、不写 localStorage 与日志（AGENTS.md §3）。
 */

export const LOGIN_PATH = '/auth/login'
export const DEFAULT_REDIRECT = '/dashboard'

/** redirect 长度上限（防御超长查询串注入） */
const MAX_REDIRECT_LENGTH = 512

/** 协议头：识别 `javascript:` / `http:` / `data:` 等伪协议与绝对 URL */
const SCHEME_PATTERN = /^[a-zA-Z][a-zA-Z0-9+.-]*:/

/** 控制字符（NUL / CRLF / DEL 等） */
const CONTROL_CHARACTER_PATTERN = /[\u0000-\u001f\u007f]/

export interface LoginNavigateTarget {
  path: typeof LOGIN_PATH
  query: { redirect: string }
}

export type LoginNavigator = (target: LoginNavigateTarget) => void

let loginNavigator: LoginNavigator | null = null

/** 注册 SPA 登录收敛导航器（由 `core/router/index.ts` 注入 `router.replace`） */
export function registerLoginNavigator(navigator: LoginNavigator | null): void {
  loginNavigator = navigator
}

/** 当前站内路径（path + query；不含 hash，防止令牌/回调 fragment 被带入 redirect） */
export function currentInternalPath(): string {
  if (typeof window === 'undefined') return DEFAULT_REDIRECT
  const { pathname, search } = window.location
  return `${pathname || DEFAULT_REDIRECT}${search || ''}`
}

/**
 * 校验并规范化回跳路径；任何非站内相对路径一律回落 `DEFAULT_REDIRECT`。
 * 允许形如 `/`、`/portrait/list`、`/knowledge/list?page=2`、`/memory/sessions#top`。
 */
export function safeRedirect(raw: unknown): string {
  if (typeof raw !== 'string') return DEFAULT_REDIRECT
  const value = raw.trim()
  if (value.length === 0 || value.length > MAX_REDIRECT_LENGTH) return DEFAULT_REDIRECT
  if (CONTROL_CHARACTER_PATTERN.test(value)) return DEFAULT_REDIRECT
  if (!value.startsWith('/')) return DEFAULT_REDIRECT
  if (value.startsWith('//') || value.startsWith('/\\') || value.includes('\\')) return DEFAULT_REDIRECT
  if (SCHEME_PATTERN.test(value.slice(1))) return DEFAULT_REDIRECT

  let decoded: string
  try {
    decoded = decodeURIComponent(value)
  } catch {
    // 非法百分号编码（URIError）视为非法输入
    return DEFAULT_REDIRECT
  }
  if (decoded.startsWith('//') || decoded.includes('\\')) return DEFAULT_REDIRECT
  if (SCHEME_PATTERN.test(decoded.slice(1))) return DEFAULT_REDIRECT
  return value
}

/** 生成登录页收敛目标（`/auth/login?redirect=<站内路径>`） */
export function resolveLoginTarget(rawPath?: unknown): LoginNavigateTarget {
  const raw = typeof rawPath === 'string' && rawPath.length > 0 ? rawPath : currentInternalPath()
  return { path: LOGIN_PATH, query: { redirect: safeRedirect(raw) } }
}

/**
 * 401 收敛：生成目标并交已注册的 SPA 导航器执行。
 * 未注册导航器时仅返回目标（不整页跳转，避免打断沙箱/单测环境）。
 */
export function redirectToLogin(rawPath?: unknown): LoginNavigateTarget {
  const target = resolveLoginTarget(rawPath)
  loginNavigator?.(target)
  return target
}
