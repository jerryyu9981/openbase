/**
 * 开发代理错误语义（v7.8.0）。
 *
 * Vite 的 `/api` 代理在后端未启动/重启时会由 http-proxy 返回**空 body 的 500**，
 * 浏览器与日志会把它误判为服务端 5xx。统一映射为 503 + JSON，表示「上游不可用、可重试」。
 */

export const UPSTREAM_UNAVAILABLE_CODE = 'SYS_UPSTREAM_UNAVAILABLE'
export const UPSTREAM_UNAVAILABLE_MESSAGE = 'OpenBase API 尚未就绪或不可达，请稍后重试'

interface WritableResponse {
  headersSent?: boolean
  writableEnded?: boolean
  writeHead: (status: number, headers: Record<string, string>) => unknown
  end: (body?: string) => unknown
}

/** 处理 Vite `proxy.on('error')`：把上游连接失败写成 503 JSON（已发头时只收尾）。 */
export function handleDevProxyError(
  _error: unknown,
  _request: unknown,
  response: unknown,
): void {
  const res = response as WritableResponse | undefined
  if (!res || typeof res.writeHead !== 'function') return

  if (!res.headersSent) {
    res.writeHead(503, { 'Content-Type': 'application/json; charset=utf-8' })
  }
  if (!res.writableEnded) {
    res.end(
      JSON.stringify({
        code: UPSTREAM_UNAVAILABLE_CODE,
        message: UPSTREAM_UNAVAILABLE_MESSAGE,
        data: null,
      }),
    )
  }
}
