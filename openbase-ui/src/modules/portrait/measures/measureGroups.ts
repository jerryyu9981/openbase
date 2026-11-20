import type { DpsMeasureSuggestion } from '@/core/api/dps'

/**
 * 措施建议分组与导出（P-08）
 *
 * 后端按建议平铺返回，不提供维度分组/导出接口；前端按 `source_tag` / `tag_code`
 * 的维度前缀分组，并生成 CSV。分组仅改变呈现，不改变后端原文与免责声明。
 */

const DIMENSION_LABELS: Record<string, string> = {
  basic: '基础属性',
  behavior: '行为特征',
  behavioral: '行为特征',
  psychology: '心理评估',
  psychological: '心理评估',
  social: '社会关系',
  correction: '矫正表现',
  risk: '风险等级',
  service: '服务特征',
}

export function dimensionLabelOf(dimension: string): string {
  return DIMENSION_LABELS[dimension] || (dimension === 'uncategorized' ? '未分组' : dimension || '未分组')
}

export function measureDimensionOf(suggestion: DpsMeasureSuggestion): string {
  const tag = String(suggestion.source_tag || suggestion.tag_code || '').trim()
  if (!tag) return 'uncategorized'
  return tag.includes(':') ? tag.slice(0, tag.indexOf(':')) : 'other'
}

export interface MeasureGroup {
  dimension: string
  label: string
  items: DpsMeasureSuggestion[]
}

/** 按维度分组：未分组置末；组内保持后端返回顺序 */
export function groupMeasureSuggestions(suggestions: DpsMeasureSuggestion[]): MeasureGroup[] {
  const groups = new Map<string, DpsMeasureSuggestion[]>()
  for (const suggestion of suggestions) {
    const dimension = measureDimensionOf(suggestion)
    const list = groups.get(dimension) || []
    list.push(suggestion)
    groups.set(dimension, list)
  }
  return Array.from(groups.entries())
    .sort(([left], [right]) => {
      if (left === 'uncategorized') return 1
      if (right === 'uncategorized') return -1
      return left.localeCompare(right)
    })
    .map(([dimension, items]) => ({ dimension, label: dimensionLabelOf(dimension), items }))
}

function csvCell(value: string): string {
  if (/[",\n\r]/.test(value)) return `"${value.replace(/"/g, '""')}"`
  return value
}

/** 措施建议 CSV：维度 / 措施码 / 建议内容 / 标签 / 来源标签 */
export function measureSuggestionsCsv(suggestions: DpsMeasureSuggestion[]): string {
  const header = ['维度', '措施码', '建议内容', '标签', '来源标签'].map(csvCell).join(',')
  const lines = suggestions.map((suggestion) =>
    [
      dimensionLabelOf(measureDimensionOf(suggestion)),
      String(suggestion.measure_code ?? ''),
      String(suggestion.measure_text ?? ''),
      String(suggestion.tag_code ?? ''),
      String(suggestion.source_tag ?? ''),
    ]
      .map(csvCell)
      .join(','),
  )
  return [header, ...lines].join('\r\n')
}
