import type { DpsAnnotationField, DpsPortraitTemplate } from '@/core/api/dps'

/**
 * 标注字段设计器共用模型（设计文档 §7 P-06）。
 *
 * - 行模型与表单输入解耦（options/range 以文本编辑）；
 * - 校验规则与后端一致：key 唯一、enum 必填 options、number 区间合法、至少 1 个字段；
 * - 标签提示按 `tag_code = "{target_dimension}:{key}"` 与归属模板评分规则比对。
 */

export const ANNOTATION_FIELD_TYPES = ['string', 'enum', 'number', 'date', 'list'] as const
export type AnnotationFieldType = (typeof ANNOTATION_FIELD_TYPES)[number]

export interface AnnotationFieldRow {
  key: string
  type: AnnotationFieldType
  required: boolean
  optionsText: string
  rangeText: string
  target_dimension: string
}

export function toFieldRows(schema?: DpsAnnotationField[]): AnnotationFieldRow[] {
  return (schema || []).map((field) => ({
    key: String(field.key || ''),
    type: (field.type || 'string') as AnnotationFieldType,
    required: Boolean(field.required),
    optionsText: Array.isArray(field.options) ? field.options.join(',') : '',
    rangeText: Array.isArray(field.range) ? field.range.join(',') : '',
    target_dimension: String(field.target_dimension || ''),
  }))
}

export function fromFieldRows(rows: AnnotationFieldRow[]): DpsAnnotationField[] {
  return rows.map((row) => {
    const field: DpsAnnotationField = { key: row.key.trim(), type: row.type, required: row.required }
    if (row.type === 'enum' && row.optionsText.trim()) {
      field.options = row.optionsText.split(',').map((item) => item.trim()).filter(Boolean)
    }
    if (row.type === 'number' && row.rangeText.trim()) {
      const parts = row.rangeText.split(',').map((item) => Number(item.trim()))
      if (parts.length === 2 && parts.every((item) => Number.isFinite(item))) field.range = [parts[0], parts[1]]
    }
    if (row.target_dimension.trim()) field.target_dimension = row.target_dimension.trim()
    return field
  })
}

function parseRange(text: string): [number, number] | null {
  const parts = text.split(',').map((item) => Number(item.trim()))
  if (parts.length !== 2 || parts.some((item) => !Number.isFinite(item))) return null
  return [parts[0], parts[1]]
}

/** 设计器即时校验；返回空数组表示可保存 */
export function validateFieldRows(rows: AnnotationFieldRow[]): string[] {
  const issues: string[] = []
  if (!rows.length) issues.push('至少需要 1 个字段')

  const seen = new Map<string, number>()
  rows.forEach((row) => {
    const key = row.key.trim()
    if (!key) {
      issues.push('存在未填写 key 的字段')
      return
    }
    seen.set(key, (seen.get(key) || 0) + 1)
  })
  seen.forEach((count, key) => {
    if (count > 1) issues.push(`字段 key 重复：${key}`)
  })

  rows.forEach((row) => {
    const label = row.key.trim() || '(未命名字段)'
    if (row.type === 'enum' && !row.optionsText.trim()) issues.push(`字段 ${label} 为 enum 时必须提供 options`)
    if (row.type === 'number' && row.rangeText.trim()) {
      const range = parseRange(row.rangeText)
      if (!range) {
        issues.push(`字段 ${label} 的 range 必须是「最小值,最大值」两个数值`)
      } else if (range[0] > range[1]) {
        issues.push(`字段 ${label} 的 range 下限不得大于上限`)
      }
    }
  })

  return issues
}

/** 字段将生成的标签编码（无目标维度时为空字符串） */
export function fieldTagCode(row: AnnotationFieldRow): string {
  if (!row.target_dimension.trim() || !row.key.trim()) return ''
  return `${row.target_dimension.trim()}:${row.key.trim()}`
}

/**
 * 字段旁的实时提示：
 * - 无目标维度 → 仅记录，不进画像；
 * - 有目标维度且命中归属模板评分规则 → 生成标签并影响评分；
 * - 有目标维度但无评分规则 → 生成标签但仅写标签。
 */
export function buildFieldTagHint(row: AnnotationFieldRow, scoringTagCodes: Set<string>): string {
  if (!row.target_dimension.trim()) return '不进画像（仅记录字段值）'
  if (!row.key.trim()) return '填写 key 后生成标签'
  const tag = fieldTagCode(row)
  if (scoringTagCodes.has(tag)) return `生成标签 ${tag}，命中评分项`
  return `生成标签 ${tag}（归属模板无对应评分项，仅写标签）`
}

/** 归属画像模板 → 评分规则标签编码集合（`dimension:ruleKey`） */
export function scoringTagCodesFromTemplate(template?: DpsPortraitTemplate | null): Set<string> {
  const raw = template?.dimension_config
  const config = typeof raw === 'string' ? safeParse(raw) : raw
  const result = new Set<string>()
  const dimensions = (config as { dimensions?: unknown } | null)?.dimensions
  if (!Array.isArray(dimensions)) return result
  for (const dimension of dimensions) {
    const record = (dimension || {}) as Record<string, unknown>
    const dimensionCode = String(record.code || '')
    const rules = Array.isArray(record.rules) ? record.rules : []
    for (const rule of rules) {
      const ruleRecord = (rule || {}) as Record<string, unknown>
      const key = String(ruleRecord.key ?? ruleRecord.tag_code ?? '').trim()
      if (!key) continue
      result.add(dimensionCode ? `${dimensionCode}:${key}` : key)
    }
  }
  return result
}

/** 归属画像模板的维度候选（target_dimension 只能是这些 code 或留空） */
export function dimensionOptionsFromTemplate(template?: DpsPortraitTemplate | null): Array<{ code: string; label: string }> {
  const raw = template?.dimension_config
  const config = typeof raw === 'string' ? safeParse(raw) : raw
  const dimensions = (config as { dimensions?: unknown } | null)?.dimensions
  if (!Array.isArray(dimensions)) return []
  return dimensions.map((item) => {
    const record = (item || {}) as Record<string, unknown>
    const code = String(record.code || '')
    const name = String(record.name || code)
    return { code, label: code === name ? code : `${name}（${code}）` }
  })
}

function safeParse(text: string): unknown {
  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}
