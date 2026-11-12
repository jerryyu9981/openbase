/**
 * 上下文裁剪策略（批次 4 R7）
 *
 * 后端契约：《批次 3 全链路贯通修复规格》§2 —— 聊天请求可选 `context_policy`
 * （strategy / max_tokens / preserve_recent_n），响应回显 `context_meta`。
 *
 * 本模块只做三件事，保持纯函数、无 Vue 依赖，便于单测与复用：
 *   1. 校验并裁剪本地保存的策略（与后端白名单同口径）；
 *   2. 读写浏览器 localStorage（仅影响当前浏览器，不落后端配置）；
 *   3. 从 SSE routing / done 事件载荷中提取并格式化 `context_meta`。
 */

export type ContextStrategy = 'recent' | 'head_tail' | 'system_priority' | 'summarize_old'

export interface ContextPolicy {
  strategy: ContextStrategy
  /** 上下文 token 预算；缺省沿用 OpenLLM 现有窗口预算 */
  max_tokens?: number
  /** 仅 system_priority 生效：保留最近 N 条 */
  preserve_recent_n?: number
}

export interface ContextMeta {
  strategy?: string
  budget_tokens?: number
  history_messages?: number
  included_messages?: number
  dropped_messages?: number
  history_tokens?: number
  summarized?: boolean
  /** 上游是否真正应用了策略；门户兜底补齐时为 false */
  applied?: boolean
  source?: string
}

export const CONTEXT_POLICY_STORAGE_KEY = 'openbase.contextPolicy'

/** 后端 `CONTEXT_POLICY_STRATEGIES` 同口径白名单 */
export const CONTEXT_STRATEGIES: ContextStrategy[] = [
  'recent',
  'head_tail',
  'system_priority',
  'summarize_old',
]

export const CONTEXT_STRATEGY_LABELS: Record<ContextStrategy, string> = {
  recent: '保留最近（默认）',
  head_tail: '首尾保留',
  system_priority: '系统优先',
  summarize_old: '早期摘要',
}

export const CONTEXT_STRATEGY_DESCRIPTIONS: Record<ContextStrategy, string> = {
  recent: '从最新消息向前保留，超出预算时丢弃最旧消息（现网默认行为）。',
  head_tail: '保留开头 1/4 与结尾 3/4，超出预算先丢中段、再丢头部。',
  system_priority: '全部 system 消息与最近 N 条优先保留，其余按由旧到新丢弃。',
  summarize_old: '保留最近消息至预算 80%，更早消息压缩为一行摘要占位。',
}

const MAX_TOKENS_LIMIT = 200000
const PRESERVE_RECENT_LIMIT = 100

function isContextStrategy(value: unknown): value is ContextStrategy {
  return typeof value === 'string' && (CONTEXT_STRATEGIES as string[]).includes(value)
}

/** 宽松转正整数：数字或纯数字字符串；非法返回 undefined */
function toPositiveInteger(value: unknown): number | undefined {
  const numeric = typeof value === 'string' && value.trim() !== '' ? Number(value) : value
  if (typeof numeric !== 'number' || !Number.isInteger(numeric) || numeric <= 0) return undefined
  return numeric
}

/** 宽松转非负整数：数字或纯数字字符串；非法返回 undefined */
function toNonNegativeInteger(value: unknown): number | undefined {
  const numeric = typeof value === 'string' && value.trim() !== '' ? Number(value) : value
  if (typeof numeric !== 'number' || !Number.isInteger(numeric) || numeric < 0) return undefined
  return numeric
}

/**
 * 校验并裁剪策略。
 *
 * - 非对象 → null（视为未配置）；
 * - strategy 非法 → 回落 `recent`；
 * - max_tokens 非正整数或超过上限 → 丢弃该项；
 * - preserve_recent_n 仅 system_priority 输出，非负整数且不超过上限；
 * - 结果等价于默认（recent 且无预算）→ null，避免无意义透传。
 */
export function normalizeContextPolicy(raw: unknown): ContextPolicy | null {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null
  const record = raw as Record<string, unknown>
  const strategy: ContextStrategy = isContextStrategy(record.strategy) ? record.strategy : 'recent'
  const policy: ContextPolicy = { strategy }

  const maxTokens = toPositiveInteger(record.max_tokens)
  if (maxTokens !== undefined && maxTokens <= MAX_TOKENS_LIMIT) {
    policy.max_tokens = maxTokens
  }

  if (strategy === 'system_priority') {
    const preserveRecent = toNonNegativeInteger(record.preserve_recent_n)
    if (preserveRecent !== undefined && preserveRecent <= PRESERVE_RECENT_LIMIT) {
      policy.preserve_recent_n = preserveRecent
    }
  }

  if (policy.strategy === 'recent' && policy.max_tokens === undefined) return null
  return policy
}

/** 读取本地策略（无配置 / 解析失败 → null） */
export function loadContextPolicy(): ContextPolicy | null {
  if (typeof localStorage === 'undefined') return null
  try {
    const raw = localStorage.getItem(CONTEXT_POLICY_STORAGE_KEY)
    if (!raw) return null
    return normalizeContextPolicy(JSON.parse(raw))
  } catch {
    return null
  }
}

/** 保存本地策略；null 或等价默认值时清除配置 */
export function saveContextPolicy(policy: ContextPolicy | null): void {
  if (typeof localStorage === 'undefined') return
  const normalized = policy === null ? null : normalizeContextPolicy(policy)
  if (normalized === null) {
    localStorage.removeItem(CONTEXT_POLICY_STORAGE_KEY)
    return
  }
  localStorage.setItem(CONTEXT_POLICY_STORAGE_KEY, JSON.stringify(normalized))
}

/**
 * 从 SSE 事件载荷提取 `context_meta`。
 *
 * 兼容两种形态：顶层 `{context_meta}`（routing 事件）与
 * `{data: {context_meta}}`（done 事件/同步响应包裹）。
 */
export function extractContextMeta(payload: unknown): ContextMeta | null {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return null
  const record = payload as Record<string, unknown>
  const nested = record.data
  if (nested && typeof nested === 'object' && !Array.isArray(nested)) {
    const nestedMeta = (nested as Record<string, unknown>).context_meta
    if (nestedMeta && typeof nestedMeta === 'object' && !Array.isArray(nestedMeta)) {
      return nestedMeta as ContextMeta
    }
  }
  const candidate = record.context_meta
  if (candidate && typeof candidate === 'object' && !Array.isArray(candidate)) {
    return candidate as ContextMeta
  }
  return null
}

/** 单行摘要（Playground 回显用）；无 meta 返回空串 */
export function formatContextMeta(meta: ContextMeta | null): string {
  if (!meta) return ''
  const strategyLabel = isContextStrategy(meta.strategy)
    ? CONTEXT_STRATEGY_LABELS[meta.strategy]
    : meta.strategy || '未知策略'
  const parts = [`上下文 ${strategyLabel}`]
  if (
    typeof meta.included_messages === 'number' &&
    typeof meta.history_messages === 'number'
  ) {
    parts.push(`入参 ${meta.included_messages}/${meta.history_messages} 条`)
  }
  if (typeof meta.budget_tokens === 'number') {
    parts.push(`预算 ${meta.budget_tokens} tokens`)
  }
  if (meta.applied === false) {
    parts.push('上游未应用')
  }
  return parts.join(' · ')
}
