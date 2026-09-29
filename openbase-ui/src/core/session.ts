/**
 * 前端会话标识（v1.4.8 D2 / R-396）
 *
 * 契约（《OpenBase-会话标识提交派单-openbase-ui-v1.0.0》§2）：
 *   - `session_id` 为**可选**字段，缺省时后端按用户记账；
 *   - 同一会话多轮**复用同一标识**，新建会话生成**新标识**；
 *   - 标识为随机值，**不含任何凭据或业务含义**（不做用户/租户编码）。
 *
 * 载体：`sessionStorage`（同一标签页会话内复用）；存储不可用（隐私模式等）时退化为内存值。
 */
const STORAGE_KEY = 'openbase.session_id'

let memorySessionId = ''

/** 生成随机会话标识（优先 crypto.randomUUID，降级为随机串） */
function randomId(): string {
  const globalCrypto = (globalThis as { crypto?: Crypto }).crypto
  if (globalCrypto && typeof globalCrypto.randomUUID === 'function') {
    return globalCrypto.randomUUID()
  }
  return `sess-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`
}

function readStorage(): string {
  try {
    return globalThis.sessionStorage?.getItem(STORAGE_KEY) || ''
  } catch {
    return ''
  }
}

function writeStorage(value: string): void {
  try {
    globalThis.sessionStorage?.setItem(STORAGE_KEY, value)
  } catch {
    // 存储不可用时仅保留内存值
  }
}

/** 读取当前会话标识；不存在时生成并持久化（多轮复用同一标识） */
export function getSessionId(): string {
  const stored = memorySessionId || readStorage()
  if (stored) {
    memorySessionId = stored
    return stored
  }
  memorySessionId = randomId()
  writeStorage(memorySessionId)
  return memorySessionId
}

/** 新建会话标识（不改变当前会话） */
export function newSessionId(): string {
  return randomId()
}

/** 重置会话标识（新建会话时调用），返回新标识 */
export function resetSessionId(): string {
  memorySessionId = randomId()
  writeStorage(memorySessionId)
  return memorySessionId
}

/** 向请求体注入会话标识（**显式传入优先**，缺省取当前会话标识） */
export function withSessionId<T extends Record<string, unknown>>(
  payload: T,
): T & { session_id: string } {
  const explicit = (payload as { session_id?: string }).session_id
  return {
    ...payload,
    session_id: explicit && explicit.trim() ? explicit : getSessionId(),
  }
}
