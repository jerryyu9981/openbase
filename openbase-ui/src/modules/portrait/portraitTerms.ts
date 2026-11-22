/**
 * 画像领域术语中文化（波次 A / A-09）
 *
 * 约束：取值（value）必须与后端枚举保持一致，仅翻译展示文案；
 * 新增枚举时在此登记，避免页面各自硬编码英文。
 */

export interface TermOption {
  value: string
  label: string
}

/** 与 DPS `template_engine.PROFILE_TYPES` 对齐 */
export const PROFILE_TYPE_OPTIONS: TermOption[] = [
  { value: 'persona', label: '人物画像' },
  { value: 'risk', label: '风险画像' },
  { value: 'business', label: '业务进度画像' },
  { value: 'topic', label: '专题画像' },
]

/** 与 DPS `template_engine.SUBJECT_TYPES` 对齐 */
export const SUBJECT_TYPE_OPTIONS: TermOption[] = [
  { value: 'person', label: '人员' },
  { value: 'unit', label: '单位' },
  { value: 'object', label: '对象' },
]

/** 与 DPS `template_engine.TEMPLATE_STATUSES` 对齐 */
export const TEMPLATE_STATUS_OPTIONS: TermOption[] = [
  { value: 'draft', label: '草稿' },
  { value: 'active', label: '启用' },
  { value: 'inactive', label: '停用' },
]

function toLabelMap(options: TermOption[]): Record<string, string> {
  const map: Record<string, string> = {}
  options.forEach((option) => {
    map[option.value] = option.label
  })
  return map
}

export const PROFILE_TYPE_LABELS = toLabelMap(PROFILE_TYPE_OPTIONS)
export const SUBJECT_TYPE_LABELS = toLabelMap(SUBJECT_TYPE_OPTIONS)
export const TEMPLATE_STATUS_LABELS = toLabelMap(TEMPLATE_STATUS_OPTIONS)

/** 取中文标签；未知值回退原值（不吞掉任何后端新增枚举）。 */
export function termLabel(map: Record<string, string>, value?: string | null): string {
  const key = String(value ?? '').trim()
  if (!key) return '-'
  return map[key] || key
}
