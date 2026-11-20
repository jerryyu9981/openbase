import type { DpsAnnotationRow, DpsPortrait } from '@/core/api/dps'

/**
 * 画像列表 / 搜索 / 360 的纯函数工具（P-08）
 *
 * - 列表前端降级搜索（A6 未提供服务端检索）；
 * - CSV 导出（A11 未提供导出接口）；
 * - 高级检索条件匹配与关键字高亮分段；
 * - 标注时间线（A10 审计过滤未提供，先用标注队列创建时间）；
 * - 属性字段化编辑（对象 ↔ 字段行）。
 */

export interface PortraitColumn {
  key: string
  label: string
  value: (row: DpsPortrait) => string
}

/** 列表/搜索的基础列定义（导出与列设置共用） */
export const PORTRAIT_COLUMNS: PortraitColumn[] = [
  { key: 'name', label: '画像名称', value: (row) => String(row.name ?? '') },
  { key: 'person_id', label: '画像码（person_id）', value: (row) => String(row.person_id ?? row.id ?? '') },
  { key: 'risk', label: '风险等级', value: (row) => riskLabelOf(row) },
  { key: 'tags', label: '标签', value: (row) => (row.tags || []).map(tagLabelOf).join(' / ') },
  { key: 'updated_at', label: '更新时间', value: (row) => formatDateTime(row.updated_at) },
  { key: 'created_at', label: '创建时间', value: (row) => formatDateTime(row.created_at) },
]

export function tagLabelOf(raw: Record<string, unknown> | string): string {
  if (typeof raw === 'string') return raw
  return String(raw.tag_name || raw.tag_code || raw.tag_value || '-')
}

export function riskScoreOf(row: DpsPortrait): number {
  const raw = row.risk_level ?? row.risk_score
  const value = Number(raw)
  return Number.isFinite(value) ? value : -1
}

export function riskLabelOf(row: DpsPortrait): string {
  const value = riskScoreOf(row)
  if (value < 0) return '未知'
  if (value >= 70) return '高'
  if (value >= 40) return '中'
  return '低'
}

export function formatDateTime(value?: string): string {
  if (!value) return '-'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false })
}

/** 关键字前端过滤（服务端检索 A6 未就绪时使用；页面须标注降级口径） */
export function filterPortraitRows(rows: DpsPortrait[], keyword: string): DpsPortrait[] {
  const trimmed = keyword.trim().toLowerCase()
  if (!trimmed) return rows
  return rows.filter(
    (row) =>
      String(row.name ?? '').toLowerCase().includes(trimmed) ||
      String(row.person_id ?? '').toLowerCase().includes(trimmed) ||
      String(row.id ?? '').toLowerCase().includes(trimmed),
  )
}

function csvCell(value: string): string {
  if (/[",\n\r]/.test(value)) return `"${value.replace(/"/g, '""')}"`
  return value
}

export function buildPortraitCsv(rows: DpsPortrait[], columns: PortraitColumn[] = PORTRAIT_COLUMNS): string {
  const header = columns.map((column) => csvCell(column.label)).join(',')
  const lines = rows.map((row) => columns.map((column) => csvCell(column.value(row))).join(','))
  return [header, ...lines].join('\r\n')
}

/* ------------------------------ 高级检索 ------------------------------ */

export type PortraitConditionField = 'keyword' | 'risk' | 'created_after' | 'created_before'

export interface PortraitCondition {
  id: string
  field: PortraitConditionField
  value: string
}

/** 高级检索条件匹配：多条件 AND；空值条件忽略 */
export function matchPortraitConditions(rows: DpsPortrait[], conditions: PortraitCondition[]): DpsPortrait[] {
  const active = conditions.filter((condition) => String(condition.value || '').trim())
  if (!active.length) return rows
  return rows.filter((row) =>
    active.every((condition) => {
      const value = String(condition.value).trim().toLowerCase()
      if (condition.field === 'keyword') {
        return (
          String(row.name ?? '').toLowerCase().includes(value) ||
          String(row.person_id ?? '').toLowerCase().includes(value) ||
          String(row.id ?? '').toLowerCase().includes(value)
        )
      }
      if (condition.field === 'risk') {
        const score = riskScoreOf(row)
        if (score < 0) return false
        if (value === 'high') return score >= 70
        if (value === 'mid') return score >= 40 && score < 70
        return score < 40
      }
      const created = String(row.created_at ?? '').slice(0, 10)
      if (!created) return false
      if (condition.field === 'created_after') return created >= value
      return created <= value
    }),
  )
}

export interface HighlightSegment {
  text: string
  hit: boolean
}

/** 关键字高亮分段（避免 v-html，渲染为普通 span/mark） */
export function splitHighlight(text: string, keyword: string): HighlightSegment[] {
  const source = String(text ?? '')
  const target = keyword.trim()
  if (!target) return [{ text: source, hit: false }]
  const lowerSource = source.toLowerCase()
  const lowerTarget = target.toLowerCase()
  const segments: HighlightSegment[] = []
  let cursor = 0
  while (cursor < source.length) {
    const index = lowerSource.indexOf(lowerTarget, cursor)
    if (index < 0) {
      segments.push({ text: source.slice(cursor), hit: false })
      break
    }
    if (index > cursor) segments.push({ text: source.slice(cursor, index), hit: false })
    segments.push({ text: source.slice(index, index + target.length), hit: true })
    cursor = index + target.length
  }
  return segments.length ? segments : [{ text: source, hit: false }]
}

/* ------------------------------ 标注时间线 ------------------------------ */

export interface AnnotationTimelineItem {
  id: string
  time: string
  title: string
  template: string
  status: string
  statusLabel: string
  levelText: string
}

const REVIEW_STATUS_LABELS: Record<string, string> = {
  pending: '待审核',
  approved: '已通过',
  rejected: '已驳回',
  modified: '已修改',
  draft: '草稿',
}

export function reviewStatusLabel(status?: string): string {
  return REVIEW_STATUS_LABELS[status || ''] || status || '-'
}

/** 标注时间线：按创建时间倒序，时间/模板/审核状态/级数 */
export function buildAnnotationTimeline(rows: DpsAnnotationRow[]): AnnotationTimelineItem[] {
  return [...rows]
    .sort((left, right) => String(right.created_at || '').localeCompare(String(left.created_at || '')))
    .map((row) => {
      const required = Number(row.review_levels_required || 0)
      const passed = Number(row.review_level || 0)
      return {
        id: String(row.id),
        time: formatDateTime(row.created_at),
        title: String(row.person_name || row.person_id || '未知主体'),
        template: String(row.annotation_template_name || row.annotation_template || '-'),
        status: String(row.review_status || ''),
        statusLabel: reviewStatusLabel(row.review_status),
        levelText: required > 0 ? `第 ${Math.min(passed, required)}/${required} 级` : '',
      }
    })
}

/* ------------------------------ 属性字段化编辑 ------------------------------ */

export interface AttributeFieldRow {
  key: string
  value: string
}

function attributeText(value: unknown): string {
  if (value === null) return 'null'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

export function attributeRowsFromObject(attributes: unknown): AttributeFieldRow[] {
  if (!attributes || typeof attributes !== 'object' || Array.isArray(attributes)) return []
  return Object.entries(attributes as Record<string, unknown>).map(([key, value]) => ({
    key,
    value: attributeText(value),
  }))
}

/** 值按 JSON 语义解析：数字/布尔/null/对象/数组；其余保持字符串 */
export function parseAttributeValue(value: string): unknown {
  const text = value.trim()
  if (text === '') return ''
  if (text === 'null') return null
  if (text === 'true') return true
  if (text === 'false') return false
  if (/^-?\d+(\.\d+)?$/.test(text)) return Number(text)
  if ((text.startsWith('{') && text.endsWith('}')) || (text.startsWith('[') && text.endsWith(']'))) {
    try {
      return JSON.parse(text)
    } catch {
      return value
    }
  }
  return value
}

/** 字段行 → 对象：空键忽略，重复键后者覆盖 */
export function attributeRowsToObject(rows: AttributeFieldRow[]): Record<string, unknown> {
  const result: Record<string, unknown> = {}
  for (const row of rows) {
    const key = row.key.trim()
    if (!key) continue
    result[key] = parseAttributeValue(row.value)
  }
  return result
}
