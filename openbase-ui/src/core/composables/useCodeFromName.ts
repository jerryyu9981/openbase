/**
 * 名称 → 编码生成（波次 A / A-05）
 *
 * 口径：
 * - 前端只对**可确定**的 ASCII 名称生成候选编码（小写 snake_case）；
 * - 中文名称不做前端音译（避免引入额外拼音依赖与前后端口径漂移），
 *   可留空提交，由服务端 `security.naming` 用 pypinyin 生成；
 *   此时 `canGenerate=false`，CodeField 提示「可留空，由服务端生成」。
 */

import { computed, type ComputedRef } from 'vue'

const NON_CODE_CHARS = /[^a-z0-9]+/g

/** 由名称生成候选编码；无法确定（含中文/纯符号/数字开头）时返回空串。 */
export function codeFromName(name: string): string {
  const text = String(name || '').trim().toLowerCase()
  if (!text) return ''
  const ascii = text.normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
  const slug = ascii.replace(NON_CODE_CHARS, '_').replace(/_+/g, '_').replace(/^_|_$/g, '')
  if (!slug || /^\d/.test(slug)) return ''
  return slug.slice(0, 100)
}

export interface UseCodeFromNameResult {
  /** 当前名称对应的候选编码（可能为空串） */
  suggested: ComputedRef<string>
  /** 是否可生成（false 时由服务端兜底） */
  canGenerate: ComputedRef<boolean>
  /** 取当前候选编码 */
  generate: () => string
}

/** 组合式封装：传入名称 getter（或字符串），返回候选编码与可生成标记。 */
export function useCodeFromName(source: string | (() => string)): UseCodeFromNameResult {
  const getName = typeof source === 'function' ? source : () => source
  const suggested = computed(() => codeFromName(getName()))
  const canGenerate = computed(() => suggested.value.length > 0)
  return {
    suggested,
    canGenerate,
    generate: () => suggested.value,
  }
}
