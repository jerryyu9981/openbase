/**
 * 画像模板可视化草稿模型（P0）。
 *
 * 设计依据：《OpenBase-画像模板与标注模板可视化设计》§5／§6／§9。
 *
 * 关键约定：
 * - 草稿 **深拷贝** 原始模板后原地编辑，未识别的键（如 `ext_types`）原样保留并回写；
 * - 规则键位以运行态契约 `key` 为准（兼容旧写法 `tag_code`，统一按 `key` 输出）；
 * - 所有校验在前端即时可见，服务端 `/validate` 结果按 `path` 映射回同一套问题列表。
 */

export type SectionKey = 'basic' | 'dimensions' | 'attributes' | 'bindings' | 'evidence' | 'anomaly'

export interface ConditionLeaf {
  field: string
  op: string
  value?: unknown
  [key: string]: unknown
}

export interface ConditionGroup {
  all?: ConditionNode[]
  any?: ConditionNode[]
}

export type ConditionNode = ConditionLeaf | ConditionGroup

export interface RuleModel {
  key?: string
  tag_code?: string
  type?: string
  weight?: number
  description?: string
  mapping?: Record<string, number | string>
  intervals?: Array<Array<number | string>>
  when?: ConditionGroup
  [key: string]: unknown
}

export interface DimensionModel {
  code?: string
  name?: string
  weight?: number
  rules?: RuleModel[]
  [key: string]: unknown
}

export interface BindingModel {
  dimensions?: string[]
  annotation_template?: string
  [key: string]: unknown
}

export interface AnomalyRuleModel {
  condition?: string
  action?: string
  severity?: string
  [key: string]: unknown
}

export interface TemplateDraft {
  code: string
  name: string
  profile_type: string
  subject_type: string
  status: string
  description: string
  extends: string
  dimension_config: { dimensions: DimensionModel[]; [key: string]: unknown }
  attributes_schema: Record<string, string[]>
  tag_bindings: BindingModel[]
  evidence_policy: Record<string, unknown>
  anomaly_rules: Record<string, AnomalyRuleModel>
}

export interface TemplateIssue {
  id: string
  level: 'error' | 'warning'
  section: SectionKey
  path: string
  message: string
}

export const SECTION_LABELS: Record<SectionKey, string> = {
  basic: '基础信息',
  dimensions: '维度与权重',
  attributes: '属性字段',
  bindings: '标签绑定',
  evidence: '证据策略',
  anomaly: '异常规则',
}

export const SECTION_ORDER: SectionKey[] = ['basic', 'dimensions', 'attributes', 'bindings', 'evidence', 'anomaly']

/** 评分规则白名单（与 DPS `ScoringDispatcher.registered_types()` 一致） */
export const RULE_TYPES = [
  { type: 'legacy_map', label: '兼容映射', hint: '无 type 时的默认：内置枚举表或 0~100 数值直取' },
  { type: 'enum_score', label: '枚举映射', hint: '业务自定义取值表：枚举值 → 分数' },
  { type: 'boolean_flag', label: '布尔标志', hint: '真/假分别给分（缺省 100/0）' },
  { type: 'interval_score', label: '区间映射', hint: '数值落在 [low, high] 内取对应分数' },
  { type: 'ratio_target_score', label: '比率目标', hint: 'rate ≥ target 取 cap，低于 half_floor×target 记 0' },
  { type: 'grade_map_score', label: '质量评级', hint: '统一 1~4 级（1=差 … 4=优）→ 分数' },
]

export const RULE_TYPE_VALUES = RULE_TYPES.map((item) => item.type)

/** 条件算子（label 与 DPS `OP_LABELS` 对齐） */
export const OPERATORS = [
  { op: 'eq', label: '等于' },
  { op: 'ne', label: '不等于' },
  { op: 'in', label: '属于' },
  { op: 'not_in', label: '不属于' },
  { op: 'contains', label: '包含' },
  { op: 'not_contains', label: '不包含' },
  { op: 'regex', label: '匹配正则' },
  { op: 'gt', label: '大于' },
  { op: 'gte', label: '大于等于' },
  { op: 'lt', label: '小于' },
  { op: 'lte', label: '小于等于' },
  { op: 'between', label: '区间内' },
  { op: 'exists', label: '有值' },
  { op: 'not_exists', label: '无值' },
  { op: 'before', label: '早于' },
  { op: 'after', label: '晚于' },
  { op: 'is_true', label: '为真' },
  { op: 'is_false', label: '为假' },
]

/** 无需取值输入的算子 */
export const NO_VALUE_OPS = ['exists', 'not_exists', 'is_true', 'is_false']

/** 取值为数组的算子 */
export const ARRAY_VALUE_OPS = ['in', 'not_in', 'between']

/** 条件组最大嵌套层数（与 DPS 一致） */
export const CONDITION_MAX_DEPTH = 3

export function deepClone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value ?? null)) as T
}

export function isPlainObject(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === 'object' && !Array.isArray(value)
}

export function isConditionGroup(node: ConditionNode): node is ConditionGroup {
  return isPlainObject(node) && ('all' in node || 'any' in node)
}

export function ruleKey(rule: RuleModel): string {
  return String(rule.key ?? rule.tag_code ?? '')
}

/** 原始模板 → 可视化草稿（保留未知键） */
export function toDraft(template: Record<string, unknown> | null | undefined): TemplateDraft {
  const source = deepClone(template || {})
  const dimensionConfig = isPlainObject(source.dimension_config) ? source.dimension_config : {}
  const dimensions = Array.isArray(dimensionConfig.dimensions) ? dimensionConfig.dimensions : []
  const attributes = isPlainObject(source.attributes_schema) ? source.attributes_schema : {}
  const bindings = Array.isArray(source.tag_bindings) ? source.tag_bindings : []
  const evidence = isPlainObject(source.evidence_policy) ? source.evidence_policy : {}
  const anomaly = isPlainObject(source.anomaly_rules) ? source.anomaly_rules : {}

  return {
    code: String(source.code || ''),
    name: String(source.name || ''),
    profile_type: String(source.profile_type || 'persona'),
    subject_type: String(source.subject_type || 'person'),
    status: String(source.status || 'draft'),
    description: String(source.description || ''),
    extends: String(source.extends || ''),
    dimension_config: { ...dimensionConfig, dimensions: deepClone(dimensions) as DimensionModel[] },
    attributes_schema: deepClone(attributes) as Record<string, string[]>,
    tag_bindings: deepClone(bindings) as BindingModel[],
    evidence_policy: deepClone(evidence),
    anomaly_rules: deepClone(anomaly) as Record<string, AnomalyRuleModel>,
  }
}

/** 可视化草稿 → 保存载荷（沿用现有 JSONB 键位，不新增列） */
export function fromDraft(draft: TemplateDraft): Record<string, unknown> {
  return {
    code: draft.code.trim(),
    name: draft.name.trim(),
    profile_type: draft.profile_type,
    subject_type: draft.subject_type,
    status: draft.status,
    description: draft.description,
    extends: draft.extends || null,
    dimension_config: deepClone(draft.dimension_config),
    attributes_schema: deepClone(draft.attributes_schema),
    tag_bindings: deepClone(draft.tag_bindings),
    evidence_policy: deepClone(draft.evidence_policy),
    anomaly_rules: deepClone(draft.anomaly_rules),
  }
}

/** 维度权重合计（两位小数展示） */
export function weightSum(draft: TemplateDraft): number {
  const total = (draft.dimension_config.dimensions || []).reduce(
    (sum, dimension) => sum + (typeof dimension.weight === 'number' ? dimension.weight : 0),
    0,
  )
  return Math.round(total * 100) / 100
}

export function sectionOfPath(path: string): SectionKey {
  const head = String(path || '').split('.')[0]
  if (head === 'dimension_config') return 'dimensions'
  if (head === 'attributes_schema') return 'attributes'
  if (head === 'tag_bindings') return 'bindings'
  if (head === 'evidence_policy') return 'evidence'
  if (head === 'anomaly_rules') return 'anomaly'
  return 'basic'
}

export interface FieldOption {
  value: string
  label: string
  type: 'enum' | 'text' | 'number' | 'date' | 'boolean'
}

/** 条件字段选择器数据源：规则 key（即标签编码）+ 属性字段 */
export function fieldCatalog(draft: TemplateDraft): FieldOption[] {
  const options = new Map<string, FieldOption>()
  for (const dimension of draft.dimension_config.dimensions || []) {
    for (const rule of dimension.rules || []) {
      const key = ruleKey(rule)
      if (!key) continue
      const mapping = isPlainObject(rule.mapping) ? Object.keys(rule.mapping) : []
      const type: FieldOption['type'] =
        rule.type === 'boolean_flag' ? 'boolean'
          : rule.type === 'interval_score' || rule.type === 'ratio_target_score' ? 'number'
            : mapping.length ? 'enum' : 'text'
      options.set(key, { value: key, label: `${key}${dimension.name ? `（${dimension.name}）` : ''}`, type })
    }
  }
  for (const [group, fields] of Object.entries(draft.attributes_schema || {})) {
    for (const field of fields || []) {
      if (!options.has(field)) options.set(field, { value: field, label: `${field}（${group}）`, type: 'text' })
    }
  }
  return [...options.values()]
}

export function newRule(): RuleModel {
  // 默认用 legacy_map（无需映射表即可保存），业务人员配好 key 即可先跑通闭环
  return { key: '', type: 'legacy_map', weight: 1, description: '' }
}

export function newDimension(): DimensionModel {
  return { code: '', name: '', weight: 0.2, rules: [newRule()] }
}

export function newBinding(): BindingModel {
  return { dimensions: [], annotation_template: '' }
}

export function newAnomalyRule(): AnomalyRuleModel {
  return { condition: '', action: '', severity: 'warn' }
}

export function newConditionLeaf(field = ''): ConditionLeaf {
  return { field, op: 'eq', value: '' }
}

export function newConditionGroup(kind: 'all' | 'any' = 'all'): ConditionGroup {
  return { [kind]: [newConditionLeaf()] }
}

/** 只读表达式预览：`a ∈ {高, 极高} AND b ≥ 9` */
export function describeCondition(group?: ConditionGroup | null): string {
  if (!group) return ''
  const render = (node: ConditionNode): string => {
    if (isConditionGroup(node)) {
      const key: 'all' | 'any' = 'all' in node ? 'all' : 'any'
      const children = (node[key] || []).map(render).filter(Boolean)
      if (!children.length) return ''
      const joined = children.join(key === 'all' ? ' AND ' : ' OR ')
      return children.length > 1 ? `(${joined})` : joined
    }
    const op = OPERATORS.find((item) => item.op === node.op)
    if (!op) return node.field || ''
    const value = Array.isArray(node.value) ? `[${node.value.join(', ')}]` : String(node.value ?? '')
    return NO_VALUE_OPS.includes(node.op) ? `${node.field} ${op.label}` : `${node.field} ${op.label} ${value}`
  }
  return render(group)
}

/** 前端即时校验（与 DPS `/validate` 口径一致；服务端结果覆盖式追加）。 */
export function collectIssues(draft: TemplateDraft): TemplateIssue[] {
  const issues: TemplateIssue[] = []
  const push = (level: TemplateIssue['level'], section: SectionKey, path: string, message: string) => {
    issues.push({ id: `${path}#${issues.length}`, level, section, path, message })
  }

  if (!draft.code.trim()) push('error', 'basic', 'code', 'code 不能为空')
  if (!draft.name.trim()) push('error', 'basic', 'name', 'name 不能为空')

  const dimensions = draft.dimension_config.dimensions || []
  if (!dimensions.length) push('error', 'dimensions', 'dimension_config.dimensions', '至少需要 1 个维度')

  const dimensionCodes = new Set<string>()
  dimensions.forEach((dimension, index) => {
    const base = `dimension_config.dimensions[${index}]`
    const code = String(dimension.code || '').trim()
    if (!code) push('error', 'dimensions', `${base}.code`, '维度 code 不能为空')
    else if (dimensionCodes.has(code)) push('error', 'dimensions', `${base}.code`, `维度 code 重复：${code}`)
    else dimensionCodes.add(code)
    if (!String(dimension.name || '').trim()) push('error', 'dimensions', `${base}.name`, '维度名称不能为空')
    if (typeof dimension.weight !== 'number' || dimension.weight < 0 || dimension.weight > 1) {
      push('error', 'dimensions', `${base}.weight`, '权重必须在 0~1 之间')
    }
    const rules = dimension.rules || []
    if (!rules.length) push('error', 'dimensions', `${base}.rules`, '每个维度至少 1 条规则')
    const ruleKeys = new Set<string>()
    rules.forEach((rule, ruleIndex) => {
      const rulePath = `${base}.rules[${ruleIndex}]`
      const key = ruleKey(rule).trim()
      if (!key) push('error', 'dimensions', `${rulePath}.key`, '规则 key（标签编码）不能为空')
      else if (ruleKeys.has(key)) push('error', 'dimensions', `${rulePath}.key`, `同维度内规则 key 重复：${key}`)
      else ruleKeys.add(key)

      const type = rule.type || 'legacy_map'
      if (!RULE_TYPE_VALUES.includes(type)) {
        push('error', 'dimensions', `${rulePath}.type`, `未注册的规则类型：${type}`)
        return
      }
      if (type === 'enum_score' || type === 'legacy_map' || type === 'grade_map_score') {
        const mapping = isPlainObject(rule.mapping) ? rule.mapping : {}
        if (type !== 'legacy_map' && !Object.keys(mapping).length) {
          push('error', 'dimensions', `${rulePath}.mapping`, '映射表不能为空')
        }
        Object.entries(mapping).forEach(([mapKey, score]) => {
          const numeric = Number(score)
          if (!Number.isFinite(numeric) || numeric < 0 || numeric > 100) {
            push('error', 'dimensions', `${rulePath}.mapping.${mapKey}`, `映射分数必须是 0~100：${mapKey}`)
          }
        })
      }
      if (type === 'interval_score') {
        const intervals = Array.isArray(rule.intervals) ? rule.intervals : []
        if (!intervals.length) push('error', 'dimensions', `${rulePath}.intervals`, '区间映射不能为空')
        intervals.forEach((interval, intervalIndex) => {
          if (!Array.isArray(interval) || interval.length !== 3) {
            push('error', 'dimensions', `${rulePath}.intervals[${intervalIndex}]`, '区间必须是 [low, high, score]')
            return
          }
          const [low, high, score] = interval.map(Number)
          if (![low, high, score].every(Number.isFinite)) {
            push('error', 'dimensions', `${rulePath}.intervals[${intervalIndex}]`, '区间三列必须是数值')
          } else {
            if (low > high) push('error', 'dimensions', `${rulePath}.intervals[${intervalIndex}]`, '区间下限不得大于上限')
            if (score < 0 || score > 100) push('error', 'dimensions', `${rulePath}.intervals[${intervalIndex}]`, '区间分数必须是 0~100')
          }
        })
      }
      if (type === 'ratio_target_score') {
        const target = Number(rule.target ?? 1)
        if (!Number.isFinite(target) || target <= 0 || target > 1) {
          push('error', 'dimensions', `${rulePath}.target`, 'target 必须满足 0 < target ≤ 1')
        }
      }
      if (type === 'boolean_flag') {
        for (const name of ['true_score', 'false_score']) {
          const raw = rule[name]
          if (raw === undefined || raw === '') continue
          const numeric = Number(raw)
          if (!Number.isFinite(numeric) || numeric < 0 || numeric > 100) {
            push('error', 'dimensions', `${rulePath}.${name}`, `${name} 必须是 0~100 的数值`)
          }
        }
      }
      if (rule.when) issues.push(...validateCondition(rule.when, `${rulePath}.when`, 'dimensions', 0))
    })
  })

  const total = weightSum(draft)
  if (dimensions.length && Math.abs(total - 1) > 0.001) {
    push('warning', 'dimensions', 'dimension_config.dimensions', `维度权重合计 ${total.toFixed(2)}，建议等于 1.00`)
  }

  const fieldSeen = new Map<string, string>()
  Object.entries(draft.attributes_schema || {}).forEach(([group, fields]) => {
    if (!Array.isArray(fields)) {
      push('error', 'attributes', `attributes_schema.${group}`, '字段分组必须是 key 数组')
      return
    }
    fields.forEach((field, index) => {
      if (!String(field || '').trim()) {
        push('error', 'attributes', `attributes_schema.${group}[${index}]`, '字段 key 不能为空')
        return
      }
      const previous = fieldSeen.get(field)
      if (previous && previous !== group) {
        push('warning', 'attributes', `attributes_schema.${group}[${index}]`, `字段 key 重复（已在 ${previous}）：${field}`)
      } else {
        fieldSeen.set(field, group)
      }
    })
  })

  const bindingSeen = new Set<string>()
  ;(draft.tag_bindings || []).forEach((binding, index) => {
    const path = `tag_bindings[${index}]`
    const annotationTemplate = String(binding.annotation_template || '').trim()
    if (!annotationTemplate) push('error', 'bindings', `${path}.annotation_template`, '标注模板 code 不能为空')
    else if (bindingSeen.has(annotationTemplate)) {
      push('warning', 'bindings', `${path}.annotation_template`, `标注模板重复绑定：${annotationTemplate}`)
    } else bindingSeen.add(annotationTemplate)
    if (!Array.isArray(binding.dimensions) || !binding.dimensions.length) {
      push('error', 'bindings', `${path}.dimensions`, '至少绑定 1 个维度')
    }
  })

  const levels = draft.evidence_policy?.review_levels
  if (levels !== undefined && levels !== null && levels !== '') {
    const numeric = Number(levels)
    if (!Number.isInteger(numeric) || numeric < 1 || numeric > 5) {
      push('error', 'evidence', 'evidence_policy.review_levels', 'review_levels 必须是 1~5 的整数')
    }
  }

  Object.entries(draft.anomaly_rules || {}).forEach(([name, rule]) => {
    if (!String(rule?.condition || '').trim()) {
      push('error', 'anomaly', `anomaly_rules.${name}.condition`, '异常规则条件不能为空')
    }
  })

  return issues
}

function validateCondition(
  group: ConditionGroup,
  path: string,
  section: SectionKey,
  depth: number,
): TemplateIssue[] {
  const issues: TemplateIssue[] = []
  const push = (target: string, message: string) => {
    issues.push({ id: `${target}#${issues.length}`, level: 'error', section, path: target, message })
  }
  if (depth > CONDITION_MAX_DEPTH) {
    push(path, `条件组嵌套超过 ${CONDITION_MAX_DEPTH} 层`)
    return issues
  }
  if (!isConditionGroup(group)) {
    push(path, '条件组必须包含 all 或 any')
    return issues
  }
  const key: 'all' | 'any' = 'all' in group ? 'all' : 'any'
  const children = group[key] || []
  if (!children.length) push(`${path}.${key}`, '条件组不能为空')
  children.forEach((node, index) => {
    const nodePath = `${path}.${key}[${index}]`
    if (isConditionGroup(node)) {
      issues.push(...validateCondition(node, nodePath, section, depth + 1))
      return
    }
    if (!String(node.field || '').trim()) push(`${nodePath}.field`, '条件字段不能为空')
    if (!OPERATORS.some((item) => item.op === node.op)) push(`${nodePath}.op`, `不支持的条件算子：${node.op}`)
  })
  return issues
}
