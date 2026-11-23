/**
 * DPS dps-proxy API 封装（v1.4.5 R-381；v1.4.10 扩展 22 方法 ＋ 2 跨上游协作）
 * 全部走 OpenBase /api/v1/dps-proxy/*，前端不直连 DPS（身份头由 OpenBase proxy 构造注入，前端不可伪造）。
 * 对齐《OpenBase-API接口设计文档-v1.4.5》§1（8 端点）与《OpenBase-API接口设计文档-v1.4.10》§1／§1.1／§3（22 端点）。
 *
 * 前端禁则（API 文档 v1.4.10 §5）：不直连 DPS；不构造身份头；不做权限判定；
 * 不假设 `tag_bindings` 结构（原样透传）；不提供「解除归属」入口（上游无此语义）。
 */
import { http, type ApiSuccess } from '@/core/api/http'
import { withSessionId } from '@/core/session'
import type { ChatMessage } from '@/core/api/llm'

export interface DpsPortrait {
  person_id?: string
  name?: string
  /** 标签行：PG 为 `{tag_code, tag_name, score}`，SQLite 回退为 `{tag_name, tag_value, dimension}` */
  tags?: Array<Record<string, unknown> | string>
  risk_level?: string
  risk_score?: number
  basic_score?: number
  behavioral_score?: number
  psychological_score?: number
  social_score?: number
  correction_score?: number
  overall_score?: number
  /** 解析后的 attributes（默认含 `attributes_json` 中的模板命名空间） */
  attributes?: Record<string, unknown>
  /** T-DM-02：指定 template_code 查询时，画像结果口径是否已过期 */
  stale?: boolean
  /** 过期原因：template_missing | version_unknown | version_mismatch | result_missing */
  stale_reason?: string | null
  template_version?: string | null
  current_template_version?: string | null
  version?: number
  status?: string
  created_at?: string
  updated_at?: string
  [key: string]: unknown
}

/** 画像异步计算任务（R3 长期） */
export interface DpsPortraitCalcTask {
  task_id: string
  status: 'pending' | 'running' | 'succeeded' | 'failed' | string
  result?: Record<string, unknown> | null
  error?: string | null
  [key: string]: unknown
}

export interface DpsTagCategory {
  id?: string
  name?: string
  description?: string
  /** 对齐画像模板 dimension_config.dimensions[].code；配置后标注模板 target_dimension 受校验 */
  dimension_code?: string | null
  org_id?: string
  tenant_id?: string
  created_at?: string
  [key: string]: unknown
}

/** 画像模板对象（#12；`dimension_config`／`tag_bindings` 等 JSON 配置块原样透传，前端不解析内部结构） */
export interface DpsPortraitTemplate {
  code: string
  name?: string
  profile_type?: string
  subject_type?: string
  /** 继承的父模板 code（深度 ≤2、禁自环／禁成环、父须存在） */
  extends?: string | null
  version?: number
  status?: string
  description?: string
  dimension_config?: unknown
  attributes_schema?: unknown
  tag_bindings?: unknown
  /** 证据策略（P3） */
  evidence_policy?: DpsEvidencePolicy | null
  /** 异常规则（P3；结构化条件可执行，字符串条件仅提示） */
  anomaly_rules?: unknown
  /** 模板分类（v2.12.0；绑定 L3 分类） */
  category_id?: string | null
  /** composite=复合模板 / component=子模板 */
  template_kind?: 'composite' | 'component' | string
  /** manual=人工命名 / fallback=迁移回退（待补充中文名） */
  name_source?: 'manual' | 'fallback' | string
  /** T-DM-01：停用响应中仍引用该模板的 active 标注模板数量 */
  affected_annotation_templates?: number
  /** T-DM-01：父模板停用门禁是否生效 */
  parent_gate_enforced?: boolean
  [key: string]: unknown
}

/** 模板分类节点（v2.12.0） */
export interface DpsTemplateCategory {
  id: string
  code: string
  name: string
  parent_id?: string | null
  path: string
  level: number
  sort_order?: number
  status?: string
  children?: DpsTemplateCategory[]
  [key: string]: unknown
}

/** 复合模板挂载的子模板（v2.12.0） */
export interface DpsTemplateComponent {
  id?: string
  parent_code: string
  child_code: string
  sort_order: number
  required: boolean
  weight_override?: number | null
  child_name?: string
  child_kind?: string
  child_version?: string | number
  child_status?: string
  [key: string]: unknown
}

/** 标注范围预检结果（v2.12.0；单模板或模板类） */
export interface DpsAnnotationScopeResult {
  scope_type: 'template' | 'category'
  scope_code: string
  template_count: number
  templates: Array<{ code: string; name?: string }>
  annotation_template_count: number
  field_count: number
  /** 模板 >50 或字段 >500 时为 true，需前端二次确认 */
  requires_confirmation: boolean
}

/** 标注字段（`field_schema` 元素；type 仅 5 类） */
export interface DpsAnnotationField {
  key: string
  type: 'string' | 'enum' | 'number' | 'date' | 'list'
  required?: boolean
  /** `type=enum` 必填 */
  options?: string[]
  /** `type=number` 的 [low, high] */
  range?: [number, number] | number[]
  /** 有值即参与标签联动（tag_code = "{dimension}:{key}"） */
  target_dimension?: string
  [key: string]: unknown
}

/** 标注模板对象（#18；`template_code` 为强归属，非空且不可置空） */
export interface DpsAnnotationTemplate {
  code: string
  name?: string
  version?: number
  status?: string
  /** 归属画像模板（强归属，不可置空） */
  template_code?: string
  scenario?: string
  field_schema?: DpsAnnotationField[]
  [key: string]: unknown
}

export interface DpsTemplateFilter {
  status?: string
  profile_type?: string
  subject_type?: string
  /** A7：name/code 模糊匹配（服务端，DPS ≥2.16.0） */
  keyword?: string
  /** A7：模板分类精确匹配 */
  category_id?: string
  /** A7：composite / component */
  template_kind?: string
  page?: number
  page_size?: number
}

export interface DpsAnnotationTemplateFilter {
  template_code?: string
  scenario?: string
  page?: number
  page_size?: number
}

export interface DpsPaged<T> {
  items: T[]
  total?: number
}

/** 标注队列行（GET /portrait/annotations；`fields` 为落库结构化字段） */
export interface DpsAnnotationRow {
  id: string
  person_id?: string
  person_name?: string
  annotation_template?: string
  annotation_template_name?: string
  profile_template_code?: string
  review_status?: string
  /** P4：已通过审核级数（0 = 未通过任何级） */
  review_level?: number
  /** P4：创建时快照的应审级数（1~5） */
  review_levels_required?: number
  fields?: Record<string, unknown>
  content?: string
  created_at?: string
  author_id?: string
  /** A2：已领取/审核人（未领取为空） */
  reviewer_id?: string | null
  [key: string]: unknown
}

/** A4：标注详情条目（`GET /portrait/annotations/{id}`；审核对照一次取全） */
export interface DpsAnnotationDetailAnnotation extends DpsAnnotationRow {
  profile_id?: string
  reviewer_id?: string | null
  review_comment?: string | null
  evidence_source?: string | null
  updated_at?: string
  /** 是否存在结构化字段（存量库无 payload 列为 false） */
  structured?: boolean
  evidence_source_persisted?: boolean
  review_progress_persisted?: boolean
}

export interface DpsAnnotationDetail {
  annotation: DpsAnnotationDetailAnnotation
}

export interface DpsAnnotationQuery {
  annotation_template?: string
  review_status?: string
  person_id?: string
  /** A2：`me` 由服务端按身份头解析；其他值为 reviewer_id 精确匹配 */
  reviewer?: string
  /** A2：审核级数（0~5） */
  level?: number
  page?: number
  page_size?: number
}

/** A1：队列聚合统计条目 */
export interface DpsAnnotationStatItem {
  key: string
  label: string
  count: number
}

/** A1：队列聚合统计（GET /annotations/stats） */
export interface DpsAnnotationStats {
  group_by: 'template' | 'status' | 'level' | 'reviewer' | string
  total: number
  items: DpsAnnotationStatItem[]
  /** 存量库缺列时对应分组退化 */
  degraded?: boolean
}

/** A2：领取结果（幂等） */
export interface DpsAnnotationClaimResult {
  annotation_id: string
  reviewer: string
  claimed: boolean
  already: boolean
}

export interface DpsAnnotationQueue {
  items: DpsAnnotationRow[]
  total: number
  page: number
  page_size: number
}

/** 模板包（#1；前端不修改包内容，结构校验以 DPS 白名单为准） */
export interface DpsTemplatePackage {
  format_version?: string
  package_hash?: string
  items?: unknown[]
  dependencies?: unknown[]
  package?: Record<string, unknown>
  [key: string]: unknown
}

export interface DpsPackageImportRequest {
  package: Record<string, unknown>
  /** 冲突策略：overwrite／skip／rename（未指定且存在冲突 → 409） */
  conflict_policy?: 'overwrite' | 'skip' | 'rename'
  /** 导入须显式携带；`true` = 预检（不写入） */
  dry_run: boolean
}

export interface DpsPackageImportResult {
  would_create?: number
  would_skip?: number
  would_conflict?: number
  errors?: unknown[]
  created?: number
  skipped?: number
  renamed?: string[]
  identical?: boolean
  [key: string]: unknown
}

export interface DpsTemplateDiffEntry {
  change_type?: 'create' | 'update' | 'delete' | string
  path?: string
  before?: unknown
  after?: unknown
  [key: string]: unknown
}

export interface DpsTemplateDiff {
  code?: string
  from_version?: number
  to_version?: number
  changes?: DpsTemplateDiffEntry[]
  [key: string]: unknown
}

export interface DpsRollbackRequest {
  target_version: number
  reason?: string
}

export interface DpsRollbackResult {
  template_code?: string
  new_version?: number
  rolled_back_to?: number
  equivalence_check?: boolean
  [key: string]: unknown
}

export interface DpsScoringIssue {
  code: string
  severity: 'BLOCK' | 'WARN'
  dimension?: string
  tag_code?: string
  annotation_template?: string | null
  field_key?: string | null
  portrait_template?: string
  detail?: Record<string, unknown>
  message?: string
  /** v2.14.0 A12：修复建议与修复目标（只读） */
  suggestion?: string
  fix_target?: {
    portrait_template?: string
    annotation_template?: string
    field_key?: string
    tag_code?: string
  }
}

export interface DpsScoringConsistencySection {
  block: number
  warn: number
  issues: DpsScoringIssue[]
  error?: string
}

export interface DpsScoringConsistencyReport {
  scanned: { templates: number; annotation_templates: number; fields: number }
  summary: { block: number; warn: number; by_code: Record<string, number> }
  issues: DpsScoringIssue[]
  basis: string
  pagination?: { limit: number; offset: number; total: number }
}

export interface DpsPreflightResult {
  valid?: boolean
  checks?: Array<{ item?: string; passed?: boolean; detail?: string }>
  impact?: DpsImpactResult
  /** v2.13.0：评分口径一致性段（BLOCK/WARN 明细） */
  scoring_consistency?: DpsScoringConsistencySection
  [key: string]: unknown
}

/** 模板可视化元数据（GET /dps-proxy/meta/schema；DPS 只读） */
export interface DpsTemplateMetaSchema {
  field_types?: Array<{ type?: string; label?: string; ops?: string[] }>
  operators?: Array<{ op?: string; label?: string }>
  condition_max_depth?: number
  rule_types?: Array<{
    type?: string
    label?: string
    description?: string
    params?: Array<{ name?: string; label?: string; kind?: string; required?: boolean }>
    example?: Record<string, unknown>
  }>
  profile_types?: string[]
  subject_types?: string[]
  template_statuses?: string[]
  weight_sum_tolerance?: number
  rule_key_field?: string
  registration_guidance?: string
  [key: string]: unknown
}

/** 模板校验问题项（字段级 path，供前端节点定位） */
export interface DpsTemplateValidationIssue {
  path?: string
  code?: string
  message?: string
  severity?: 'error' | 'warning' | string
}

export interface DpsTemplateValidationResult {
  valid?: boolean
  errors?: DpsTemplateValidationIssue[]
  weight_sum?: number
  [key: string]: unknown
}

export interface DpsTemplatePreviewRule {
  key?: string
  type?: string
  weight?: number
  value?: unknown
  status?: 'scored' | 'missing' | 'skipped' | 'error' | string
  when_matched?: boolean | null
  score?: number | null
  message?: string
}

export interface DpsTemplatePreviewDimension {
  code?: string
  name?: string
  weight?: number
  score?: number
  confidence?: number
  skipped?: number
  rules?: DpsTemplatePreviewRule[]
}

export interface DpsTemplatePreviewResult {
  valid?: boolean
  errors?: DpsTemplateValidationIssue[]
  weight_sum?: number
  normalized?: boolean
  overall_score?: number
  dimensions?: DpsTemplatePreviewDimension[]
  sample_keys?: string[]
  elapsed_ms?: number
  [key: string]: unknown
}

/** 模板实际评分项（继承解析后，与画像计算口径一致） */
export interface DpsScoringRule {
  key: string
  tag_key: string
  type: string
  weight: number
  description: string
  default_score: number
  when?: unknown
}

export interface DpsScoringDimension {
  code: string
  name: string
  weight: number
  /** P1：产出该维度标签的标注模板（为空表示无标注来源） */
  annotation_sources?: string[]
  /** P1：无标注来源标记（分数只能来自历史标签/接口导入） */
  source_gap?: boolean
  rules: DpsScoringRule[]
}

export interface DpsTemplateScoringItems {
  template_code: string
  extends: string | null
  source: string
  dimension_count: number
  rule_count: number
  /** P1：无标注来源的维度 code 列表（social / crime 等缺口提示） */
  dimensions_without_annotation_source?: string[]
  dimensions: DpsScoringDimension[]
}

/* ==================== P2 可解释性（族谱 / 字段映射 / 维度明细） ==================== */

/** 族谱节点（`depth=0` 为当前模板） */
export interface DpsLineageNode {
  code: string
  name: string
  status?: string | null
  version?: string | null
  depth: number
  current: boolean
}

/** 画像模板的标注模板绑定（`ownership_mismatch` = 归属 ≠ 绑定方） */
export interface DpsLineageBinding {
  annotation_template: string
  dimensions: string[]
  exists: boolean
  status?: string | null
  owned_by?: string | null
  ownership_mismatch: boolean
  bound_by?: string
}

/** 字段计分规则（由 `score_map` / `score_direction` 归一） */
export interface DpsAnnotationScoreRule {
  type: string
  score_direction: string
  score_map: Record<string, number> | null
  summary: string
}

/** 标注字段 → 标签 → 评分项映射 */
export interface DpsAnnotationFieldMappingEntry {
  key: string
  label: string
  type: string
  target_dimension: string | null
  tag_key: string | null
  tag_code: string | null
  score_rule: DpsAnnotationScoreRule | null
  affects_scoring: DpsLineageScoringHit[]
  /** affects=命中评分项 / tag_only=仅写标签 / no_tag=无目标维度 */
  scoring_status: 'affects' | 'tag_only' | 'no_tag' | string
  missing_fallback: number
}

export interface DpsLineageTagOutput {
  tag_code: string
  field_key: string
  tag_key: string
}

export interface DpsLineageScoringHit {
  dimension: string
  rule_key: string
  weight: number
  description: string
  tag_code?: string
  field_key?: string
  type?: string
}

/** 标注模板视图（被当前模板绑定 ∪ 归属当前模板 ∪ 全局未绑定） */
export interface DpsLineageAnnotationView {
  code: string
  name: string
  status?: string | null
  owned_by?: string | null
  bound_to_current: boolean
  bound_dimensions: string[]
  unbound: boolean
  fields: DpsAnnotationFieldMappingEntry[]
  tag_outputs: DpsLineageTagOutput[]
  scoring_hits: DpsLineageScoringHit[]
  unmatched_tag_outputs: string[]
}

export interface DpsLineageGap {
  dimensions_without_annotation_source: string[]
  unbound_annotation_templates: string[]
  bound_annotation_templates_missing: string[]
  ownership_mismatches: Array<{
    annotation_template: string
    owned_by?: string | null
    bound_by?: string | null
  }>
  tag_outputs_without_scoring_rule: string[]
  items: Array<{ type: string; severity: string; code?: string; message: string }>
}

/** 模板四联视图（族谱 / 标注模板 / 标签产出 / 评分项 + 缺口） */
export interface DpsTemplateLineage {
  template_code: string
  name?: string
  status?: string
  version?: string
  extends?: string | null
  lineage: DpsLineageNode[]
  bindings: DpsLineageBinding[]
  annotation_templates: DpsLineageAnnotationView[]
  /** 模板未激活时为 null（无运行时评分口径） */
  scoring: DpsTemplateScoringItems | null
  gaps: DpsLineageGap
}

/** 标注字段映射（标注工作台逐字段提示） */
export interface DpsAnnotationFieldMapping {
  annotation_template: string
  name?: string
  owned_by?: string | null
  portrait_template?: string | null
  portrait_template_status?: string | null
  scoring_available: boolean
  notes: string[]
  fields: DpsAnnotationFieldMappingEntry[]
  summary: { field_count: number; affects_scoring: number; tag_only: number; no_tag: number }
}

/** 维度规则级明细（缺值 `missing=true`，按 50 分计入） */
export interface DpsDimensionRuleDetail {
  key: string
  tag_key: string
  description: string
  weight: number
  score: number
  value: unknown
  missing: boolean
  scoring_type: string
}

export interface DpsDimensionDetail {
  code: string
  name: string
  weight: number
  score: number
  confidence: number
  level: string
  rule_count: number
  present_count: number
  missing_count: number
  rules: DpsDimensionRuleDetail[]
}

export interface DpsPortraitDimensionDetails {
  person_id: string
  template_code?: string | null
  source: 'template' | 'default' | string
  overall_score: number
  missing_policy: { score: number; note: string }
  dimensions: DpsDimensionDetail[]
}

/* ==================== P3 策略执行（证据来源 / 异常预警 / 孤儿治理） ==================== */

/** 模板证据策略（P4 起 `review_levels` 1~5 级均已生效） */
export interface DpsEvidencePolicy {
  require_source?: boolean
  review_levels?: number
  [key: string]: unknown
}

/** 审核响应的证据校验结果 */
export interface DpsEvidenceCheck {
  required: boolean
  provided: boolean
  satisfied: boolean
  review_levels: number
  review_levels_supported: boolean
  persisted?: boolean
  enforced?: boolean
}

/** 异常规则求值结果（`evaluable=false` 表示条件不可执行） */
export interface DpsAnomalyAlert {
  rule: string
  action?: string | null
  matched: boolean
  evaluable: boolean
  reason?: string | null
  annotation_id?: string
  created_at?: string
}

/** 画像异常预警聚合（P3） */
export interface DpsPortraitAnomalyAlerts {
  person_id: string
  template_code?: string | null
  scanned: number
  alerts: DpsAnomalyAlert[]
  /** 字符串表达式等不可求值的规则名（页面显示警示） */
  unevaluated_rules?: string[]
}

/** 孤儿标注模板治理项（只读建议，不自动改数据） */
export interface DpsOrphanAnnotationTemplate {
  code: string
  name?: string
  status?: string
  owned_by?: string | null
  suggested_action: 'bind_to_owner' | 'deprecate' | string
  reason: string
}

/** 标注创建载荷（P3 增加证据来源） */
export interface DpsAnnotationCreatePayload {
  action: 'create' | string
  person_id: string
  annotation_template?: string
  template_code?: string
  fields?: Record<string, unknown>
  content?: string
  created_by?: string
  /** 证据来源（文书编号）；模板 `require_source=true` 时审核通过前必填 */
  evidence_source?: string
  [key: string]: unknown
}

export interface DpsLineageSource {
  annotation_id?: string
  template_code?: string
  source?: string
  adapter_id?: string
  created_at?: string
  [key: string]: unknown
}

export interface DpsLineageResult {
  tag_code?: string
  sources?: DpsLineageSource[]
  [key: string]: unknown
}

/** 影响面查询参数（三层维度；`field_key` 显式不支持 → 400） */
export interface DpsImpactQuery {
  template_code?: string
  annotation_template_code?: string
  tag_code?: string
}

export interface DpsImpactResult {
  tag_count?: number
  profile_count?: number
  annotation_template_count?: number
  annotation_count?: number
  /** 口径说明（原文；`tag_count=0` 时前端须强制展开） */
  basis?: string | Record<string, unknown>
  [key: string]: unknown
}

export interface DpsMeasureSuggestion {
  tag_code?: string
  measure_code?: string
  measure_text?: string
  source_tag?: string
  [key: string]: unknown
}

export interface DpsMeasureResult {
  suggestions?: DpsMeasureSuggestion[]
  /** 免责声明（后端原文，前端不得改写） */
  disclaimer?: string
  [key: string]: unknown
}

export interface DpsScoringType {
  code?: string
  name?: string
  status?: string
  description?: string
  [key: string]: unknown
}

export interface DpsAnnotationGenerateRequest {
  text: string
  annotation_template: string
  [key: string]: unknown
}

export interface DpsAnnotationCandidate {
  annotation?: { id?: string; review_status?: string; [key: string]: unknown }
  source?: string
  adapter_id?: string
  [key: string]: unknown
}

/** 扁平标签检索条目（v1.5.0 A9） */
export interface DpsTagSearchItem {
  category_id: string
  category_name: string
  dimension_code?: string | null
  value_id: string
  value: string
  color?: string
  order_num?: number
  parent_value_id?: string | null
}

/** 已持久化 AI 候选（v1.5.0 A14） */
export interface DpsPersistedCandidate {
  id: string
  batch_id: string
  adapter_id: string
  annotation_template: string
  upstream_annotation_id: string
  review_status: string
  person_id?: string | null
  profile_id?: string | null
  fields: Record<string, unknown>
  created_at: string
}

/** CSV 导出结果（v1.5.0 A11） */
export interface DpsCsvExport {
  blob: Blob
  filename: string
  truncated: boolean
}

function buildCsvExport(response: { data: Blob; headers: unknown }): DpsCsvExport {
  const headers = (response.headers || {}) as Record<string, string | undefined>
  const disposition = String(headers['content-disposition'] || '')
  const matched = /filename="?([^";]+)"?/i.exec(disposition)
  return {
    blob: response.data,
    filename: matched?.[1] || 'export.csv',
    truncated: String(headers['x-export-truncated'] || '').toLowerCase() === 'true',
  }
}

/** 复核提交（DPS 既有端点 `POST /portrait/annotations/{id}/review`） */
export interface DpsReviewSubmitRequest {
  review_status: 'approved' | 'rejected' | 'modified'
  comment?: string
  modified_value?: unknown
}

/** P4：审核进度（逐级审核；`finalized=true` 表示终审完成） */
export interface DpsAnnotationReviewProgress {
  level: number
  required: number
  finalized: boolean
}

/** P4：审核留痕条目（`GET /portrait/annotations/{id}/review-log`） */
export interface DpsAnnotationReviewLogItem {
  review_level: number
  action: string
  reviewer?: string | null
  comment?: string | null
  created_at?: string
}

export interface DpsAnnotationReviewLog {
  annotation_id: string
  items: DpsAnnotationReviewLogItem[]
  total: number
}

/** AI 复核辅助（经 llm_proxy → OpenLLM，非本版 22 端点） */
export interface DpsReviewAssistRequest {
  model?: string
  messages: ChatMessage[]
  session_id?: string
}

export interface DpsReviewAssistResult {
  choices?: Array<{ message?: { content?: string }; [key: string]: unknown }>
  [key: string]: unknown
}

/** v1.12.0（XR-DPS-05）：DPS 运行态指标（上游 `GET /api/v2/metrics`） */
export interface DpsRuntimeMetrics {
  qps_1m: number
  cpu_percent: number
  memory_mb: number | null
  memory_percent: number | null
  uptime_seconds: number
  requests_total: number
  collected_at: string
}

/** 限流只读状态（上游 `GET /api/v2/rate-limits/status`） */
export interface DpsRateLimitStatus {
  tenant_id?: string
  endpoint?: string
  window_start?: string
  count?: number
  limit?: number
  window?: number
  utilization?: number
  source?: string
  [key: string]: unknown
}

/** 告警规则只读（上游 `GET /api/v2/alerts/rules`） */
export interface DpsAlertRule {
  id?: number
  name?: string
  condition?: string
  threshold?: number
  duration?: string
  notification_channel?: string
  enabled?: boolean | number
  [key: string]: unknown
}

/** API 注册表只读（上游 `GET /api/v2/api-registry`） */
export interface DpsApiRegistryEntry {
  endpoint?: string
  method?: string
  version?: string | number
  status?: string
  sunset_date?: string | null
  description?: string | null
  created_at?: string
  updated_at?: string
  [key: string]: unknown
}

/** 错误码只读（上游 `GET /api/v2/error-codes`） */
export interface DpsErrorCode {
  code?: string
  http_status?: number
  message?: string
  description?: string | null
  category?: string
  is_builtin?: boolean | number
  [key: string]: unknown
}

/** 角色权限只读（上游 `GET /api/v2/permissions/roles`） */
export interface DpsRole {
  id?: number
  name?: string
  description?: string | null
  permissions?: string | string[] | null
  is_builtin?: boolean | number
  [key: string]: unknown
}

export const dpsApi = {
  /** 画像列表（GET /api/v1/dps-proxy/portraits；v1.5.0 支持服务端 keyword/external_id） */
  async listPortraits(params?: {
    page?: number
    page_size?: number
    keyword?: string
    external_id?: string
    /** T-DM-02：指定画像模板口径（stale 过滤必须同时提供） */
    template_code?: string
    /** T-DM-02：仅看过期画像 */
    stale?: boolean
    /** v2.19.0（波次 B）：组织编码筛选 */
    org_code?: string
  }): Promise<{ items: DpsPortrait[]; total?: number }> {
    const { data } = await http.get<{ code: number; data: { items: DpsPortrait[]; total?: number } }>('/dps-proxy/portraits', { params })
    return data.data
  },

  /** 画像详情（GET /api/v1/dps-proxy/portraits/{person_id}；`templateCode` 指定模板口径） */
  async getPortrait(personId: string, templateCode?: string): Promise<DpsPortrait> {
    const { data } = await http.get<{ code: number; data: DpsPortrait }>(
      `/dps-proxy/portraits/${encodeURIComponent(personId)}`,
      { params: templateCode ? { template_code: templateCode } : undefined },
    )
    return data.data
  },

  /** 按外部身份标识查询画像（GET /api/v1/dps-proxy/portraits/by-external/{external_id}，批次 5） */
  async getPortraitByExternal(externalId: string): Promise<DpsPortrait> {
    const { data } = await http.get<{ code: number; data: DpsPortrait }>(
      `/dps-proxy/portraits/by-external/${encodeURIComponent(externalId)}`,
    )
    return data.data
  },

  /**
   * 画像增量更新（PATCH /api/v1/dps-proxy/portraits/{person_id}，批次 5）
   *
   * 深合并语义（dict 递归 / list 去重追加 / 标量覆盖 / null 删除）；
   * 传入 `version` 时携带 `If-Match` 做乐观锁，版本不符上游返回 409。
   */
  async updatePortrait(
    personId: string,
    body: Record<string, unknown>,
    version?: number,
  ): Promise<DpsPortrait> {
    const config = version === undefined ? undefined : { headers: { 'If-Match': String(version) } }
    const { data } = await http.patch<{ code: number; data: DpsPortrait }>(
      `/dps-proxy/portraits/${encodeURIComponent(personId)}`,
      body,
      config,
    )
    return data.data
  },

  /**
   * 删除画像（DELETE /api/v1/dps-proxy/portraits/{person_id}，批次 5.1）
   *
   * 上游为软删除（status=deleted，保留历史与标注审计），删除后不可见；
   * 重复删除幂等（响应 `already_deleted=true`），不存在返回 404。
   */
  async deletePortrait(personId: string): Promise<{ person_id?: string; status?: string; already_deleted?: boolean }> {
    const { data } = await http.delete<{
      code: number
      data: { person_id?: string; status?: string; already_deleted?: boolean }
    }>(`/dps-proxy/portraits/${encodeURIComponent(personId)}`)
    return data.data
  },

  /** 画像计算（POST /api/v1/dps-proxy/portraits/calculate） */
  async calculatePortrait(payload: Record<string, unknown>): Promise<Record<string, unknown>> {
    try {
      const { data } = await http.post<{ code: number; data: Record<string, unknown> }>('/dps-proxy/portraits/calculate', payload)
      return data.data
    } catch (error) {
      // R3：门户超时放宽到 30s；仍返回 504 时给出可读提示（计算可能已提交）
      const status = (error as { response?: { status?: number } })?.response?.status
      if (status === 504) {
        throw new Error('计算可能已提交，请在详情页刷新确认')
      }
      throw error
    }
  },

  /** 画像异步计算任务（R3 长期：GET /api/v1/dps-proxy/portraits/tasks/{task_id}） */
  async getPortraitTask(taskId: string): Promise<DpsPortraitCalcTask> {
    const { data } = await http.get<{ code: number; data: DpsPortraitCalcTask }>(
      `/dps-proxy/portraits/tasks/${encodeURIComponent(taskId)}`,
    )
    return data.data
  },

  /** 画像计算任务列表（v2.20.1：GET /dps-proxy/portraits/tasks） */
  async listPortraitCalcTasks(
    params: {
      status?: string
      person_id?: string
      template_code?: string
      page?: number
      page_size?: number
    } = {},
  ): Promise<{ items: DpsPortraitCalcTask[]; total: number; page: number; page_size: number }> {
    const { data } = await http.get<
      ApiSuccess<{ items: DpsPortraitCalcTask[]; total: number; page: number; page_size: number }>
    >('/dps-proxy/portraits/tasks', { params })
    return data.data
  },

  /** 人工重试失败任务（v2.20.1：POST /dps-proxy/portraits/tasks/{task_id}/retry） */
  async retryPortraitCalcTask(
    taskId: string,
  ): Promise<{ task_id: string; status: string; retried: boolean }> {
    const { data } = await http.post<
      ApiSuccess<{ task_id: string; status: string; retried: boolean }>
    >(`/dps-proxy/portraits/tasks/${encodeURIComponent(taskId)}/retry`, {})
    return data.data
  },

  /** 轮询画像异步任务：2s 间隔、默认 60s 超时；failed/超时抛可读错误；onStatus 透出每次轮询状态 */
  async waitPortraitTask(
    taskId: string,
    options?: {
      intervalMs?: number
      timeoutMs?: number
      onStatus?: (task: DpsPortraitCalcTask) => void
    },
  ): Promise<DpsPortraitCalcTask> {
    const intervalMs = options?.intervalMs ?? 2000
    const timeoutMs = options?.timeoutMs ?? 60000
    const deadline = Date.now() + timeoutMs
    for (;;) {
      const task = await this.getPortraitTask(taskId)
      options?.onStatus?.(task)
      if (task.status === 'succeeded') return task
      if (task.status === 'failed') throw new Error(task.error || '画像计算失败')
      if (Date.now() >= deadline) throw new Error('计算超时，请在详情页刷新确认')
      await new Promise((resolve) => setTimeout(resolve, intervalMs))
    }
  },

  /** 标签分类（GET /api/v1/dps-proxy/tags/categories） */
  async listTagCategories(): Promise<{ items: DpsTagCategory[] }> {
    const { data } = await http.get<{ code: number; data: { items: DpsTagCategory[] } }>('/dps-proxy/tags/categories')
    return data.data
  },

  /** 创建标签分类（POST /api/v1/dps-proxy/tags/categories） */
  async createTagCategory(payload: { name: string; description?: string; dimension_code?: string }): Promise<DpsTagCategory> {
    const { data } = await http.post<{ code: number; data: DpsTagCategory }>('/dps-proxy/tags/categories', payload)
    return data.data
  },

  /** 更新标签分类（PUT /api/v1/dps-proxy/tags/categories/{id}） */
  async updateTagCategory(categoryId: string, payload: { name?: string; description?: string; dimension_code?: string }): Promise<DpsTagCategory> {
    const { data } = await http.put<{ code: number; data: DpsTagCategory }>(`/dps-proxy/tags/categories/${encodeURIComponent(categoryId)}`, payload)
    return data.data
  },

  /** 删除标签分类（DELETE /api/v1/dps-proxy/tags/categories/{id}） */
  async deleteTagCategory(categoryId: string): Promise<unknown> {
    const { data } = await http.delete<{ code: number; data: unknown }>(`/dps-proxy/tags/categories/${encodeURIComponent(categoryId)}`)
    return data.data
  },

  /** 报表概览（GET /api/v1/dps-proxy/reports/overview） */
  async getReportsOverview(): Promise<Record<string, unknown>> {
    const { data } = await http.get<{ code: number; data: Record<string, unknown> }>('/dps-proxy/reports/overview')
    return data.data
  },

  /** 批量任务状态（GET /api/v1/dps-proxy/batch/tasks/{task_id}） */
  async getBatchTaskStatus(taskId: string): Promise<Record<string, unknown>> {
    const { data } = await http.get<{ code: number; data: Record<string, unknown> }>(`/dps-proxy/batch/tasks/${encodeURIComponent(taskId)}`)
    return data.data
  },

  /** 审计日志（GET /api/v1/dps-proxy/audit/logs） */
  async listAuditLogs(params?: {
    start_time?: string
    end_time?: string
    user_id?: string
    resource_type?: string
    resource_id?: string
    action?: string
    result?: string
    page?: number
    page_size?: number
  }): Promise<{ items: Record<string, unknown>[]; total?: number }> {
    const { data } = await http.get<{
      code: number
      data: { items: Record<string, unknown>[]; total?: number }
    }>('/dps-proxy/audit/logs', { params })
    return data.data
  },

  /** 实体审计时间线（GET /api/v1/dps-proxy/audit；v1.5.0 A10） */
  async getAuditTimeline(params: {
    entity_type: string
    entity_id: string
    page?: number
    page_size?: number
    order?: 'asc' | 'desc'
  }): Promise<{
    items: Record<string, unknown>[]
    total: number
    page: number
    page_size: number
    entity_type: string
    entity_id: string
  }> {
    const { data } = await http.get<{
      code: number
      data: {
        items: Record<string, unknown>[]
        total: number
        page: number
        page_size: number
        entity_type: string
        entity_id: string
      }
    }>('/dps-proxy/audit', { params })
    return data.data
  },

  /** 标签检索（GET /api/v1/dps-proxy/tags；v1.5.0 A9，扁平标签值＋分类元数据） */
  async listTags(params?: {
    keyword?: string
    category_id?: string
    page?: number
    page_size?: number
  }): Promise<DpsPaged<DpsTagSearchItem>> {
    const { data } = await http.get<ApiSuccess<DpsPaged<DpsTagSearchItem>>>('/dps-proxy/tags', { params })
    return data.data
  },

  /** 标注 CSV 导出（GET /api/v1/dps-proxy/annotations/export；v1.5.0 A11） */
  async exportAnnotationsCsv(params?: {
    annotation_template?: string
    review_status?: string
    person_id?: string
  }): Promise<DpsCsvExport> {
    const response = await http.get<Blob>('/dps-proxy/annotations/export', {
      params,
      responseType: 'blob',
    })
    return buildCsvExport(response)
  },

  /** 画像 CSV 导出（GET /api/v1/dps-proxy/portraits/export；v1.5.0 A11） */
  async exportPortraitsCsv(params?: {
    keyword?: string
    external_id?: string
  }): Promise<DpsCsvExport> {
    const response = await http.get<Blob>('/dps-proxy/portraits/export', {
      params,
      responseType: 'blob',
    })
    return buildCsvExport(response)
  },

  /** AI 候选生成并持久化（POST /api/v1/dps-proxy/annotation-candidates；v1.5.0 A14） */
  async generatePersistedAnnotationCandidate(body: {
    adapter_id: string
    text: string
    annotation_template?: string
    person_id?: string
    profile_id?: string
    batch_id?: string
  }): Promise<{ batch_id: string; candidate: DpsPersistedCandidate }> {
    const { data } = await http.post<ApiSuccess<{ batch_id: string; candidate: DpsPersistedCandidate }>>(
      '/dps-proxy/annotation-candidates',
      body,
    )
    return data.data
  },

  /** 按批次恢复候选（GET /api/v1/dps-proxy/annotation-candidates?batch_id=；v1.5.0 A14） */
  async listAnnotationCandidates(batchId: string): Promise<{
    batch_id: string
    items: DpsPersistedCandidate[]
    total: number
  }> {
    const { data } = await http.get<ApiSuccess<{
      batch_id: string
      items: DpsPersistedCandidate[]
      total: number
    }>>('/dps-proxy/annotation-candidates', { params: { batch_id: batchId } })
    return data.data
  },

  /** 最近候选批次（GET /api/v1/dps-proxy/annotation-candidates/latest；v1.5.0 A14） */
  async getLatestAnnotationCandidates(params?: {
    adapter_id?: string
    annotation_template?: string
  }): Promise<{ batch_id: string | null; items: DpsPersistedCandidate[]; total: number }> {
    const { data } = await http.get<ApiSuccess<{
      batch_id: string | null
      items: DpsPersistedCandidate[]
      total: number
    }>>('/dps-proxy/annotation-candidates/latest', { params })
    return data.data
  },

  /** 上游健康（GET /api/v1/dps-proxy/health） */
  async getDpsHealth(): Promise<{ status?: string; version?: string }> {
    const { data } = await http.get<{ code: number; data: { status?: string; version?: string } }>('/dps-proxy/health')
    return data.data
  },

  /* ==================== v1.12.0｜运行态观测只读（XR-DPS-05） ==================== */

  /** 运行态指标（GET /dps-proxy/metrics；上游 DPS `GET /api/v2/metrics`） */
  async getRuntimeMetrics(): Promise<DpsRuntimeMetrics> {
    const { data } = await http.get<{ code: number; data: DpsRuntimeMetrics }>('/dps-proxy/metrics')
    return data.data
  },

  /** 限流状态只读（GET /dps-proxy/rate-limits/status；查询参数透传） */
  async getRateLimitStatus(params?: { tenant_id?: string }): Promise<DpsRateLimitStatus[]> {
    const { data } = await http.get<{ code: number; data: DpsRateLimitStatus[] }>(
      '/dps-proxy/rate-limits/status',
      { params },
    )
    return data.data
  },

  /** 告警规则只读（GET /dps-proxy/alerts/rules） */
  async getAlertRules(): Promise<DpsAlertRule[]> {
    const { data } = await http.get<{ code: number; data: DpsAlertRule[] }>('/dps-proxy/alerts/rules')
    return data.data
  },

  /** API 注册表只读（GET /dps-proxy/api-registry；支持 version/status 透传） */
  async getApiRegistry(params?: { version?: string; status?: string }): Promise<DpsApiRegistryEntry[]> {
    const { data } = await http.get<{ code: number; data: DpsApiRegistryEntry[] }>(
      '/dps-proxy/api-registry',
      { params },
    )
    return data.data
  },

  /** 错误码只读（GET /dps-proxy/error-codes；支持 category 透传） */
  async getErrorCodes(params?: { category?: string }): Promise<DpsErrorCode[]> {
    const { data } = await http.get<{ code: number; data: DpsErrorCode[] }>(
      '/dps-proxy/error-codes',
      { params },
    )
    return data.data
  },

  /** 角色权限只读（GET /dps-proxy/permissions/roles；上游写面已 410 收口） */
  async getPermissionRoles(): Promise<DpsRole[]> {
    const { data } = await http.get<{ code: number; data: DpsRole[] }>('/dps-proxy/permissions/roles')
    return data.data
  },

  /* ==================== v1.4.10｜契约 10 新增端点（#1~#10） ==================== */

  /** 模板包导出（POST /dps-proxy/template-packages/export，#1；权限动作 = portrait_template:create） */
  async exportPackage(body: Record<string, unknown>): Promise<DpsTemplatePackage> {
    const { data } = await http.post<ApiSuccess<DpsTemplatePackage>>('/dps-proxy/template-packages/export', body)
    return data.data
  },

  /** 模板包导入（POST /dps-proxy/template-packages/import，#2；须带 `dry_run`，不得默认实做） */
  async importPackage(body: DpsPackageImportRequest): Promise<DpsPackageImportResult> {
    const { data } = await http.post<ApiSuccess<DpsPackageImportResult>>('/dps-proxy/template-packages/import', body)
    return data.data
  },

  /** 版本对比（GET /dps-proxy/templates/{code}/diff?from=&to=，#3） */
  async diffVersions(code: string, from: number | string, to: number | string): Promise<DpsTemplateDiff> {
    const { data } = await http.get<ApiSuccess<DpsTemplateDiff>>(`/dps-proxy/templates/${encodeURIComponent(code)}/diff`, {
      params: { from, to },
    })
    return data.data
  },

  /** 版本回滚（POST /dps-proxy/templates/{code}/rollback，#4；写操作，二次确认四要素前置） */
  async rollbackTemplate(code: string, body: DpsRollbackRequest): Promise<DpsRollbackResult> {
    const { data } = await http.post<ApiSuccess<DpsRollbackResult>>(`/dps-proxy/templates/${encodeURIComponent(code)}/rollback`, body)
    return data.data
  },

  /** 预检（GET /dps-proxy/templates/{code}/preflight，#5；只读，不写入） */
  async preflightTemplate(code: string): Promise<DpsPreflightResult> {
    const { data } = await http.get<ApiSuccess<DpsPreflightResult>>(`/dps-proxy/templates/${encodeURIComponent(code)}/preflight`)
    return data.data
  },

  /** 评分口径一致性治理报告（GET /dps-proxy/governance/scoring-consistency；只读，v2.13.0） */
  async getScoringConsistency(params?: {
    category_code?: string
    only_active?: boolean
    limit?: number
    offset?: number
  }): Promise<DpsScoringConsistencyReport> {
    const { data } = await http.get<ApiSuccess<DpsScoringConsistencyReport>>(
      '/dps-proxy/governance/scoring-consistency',
      { params },
    )
    return data.data
  },

  /** 模板可视化元数据（GET /dps-proxy/meta/schema；算子/规则参数模式，只读） */
  async getTemplateMetaSchema(): Promise<DpsTemplateMetaSchema> {
    const { data } = await http.get<ApiSuccess<DpsTemplateMetaSchema>>('/dps-proxy/meta/schema')
    return data.data
  },

  /** 模板服务端全量校验（POST /dps-proxy/templates/{code}/validate；只读，可校验未保存草稿） */
  async validateTemplate(code: string, template?: Record<string, unknown>): Promise<DpsTemplateValidationResult> {
    const { data } = await http.post<ApiSuccess<DpsTemplateValidationResult>>(
      `/dps-proxy/templates/${encodeURIComponent(code)}/validate`,
      template ? { template } : {},
    )
    return data.data
  },

  /** 模板样例试算（POST /dps-proxy/templates/{code}/preview；dry-run 无副作用） */
  async previewTemplate(
    code: string,
    template: Record<string, unknown> | undefined,
    sample: Record<string, unknown>,
  ): Promise<DpsTemplatePreviewResult> {
    const { data } = await http.post<ApiSuccess<DpsTemplatePreviewResult>>(
      `/dps-proxy/templates/${encodeURIComponent(code)}/preview`,
      { ...(template ? { template } : {}), sample },
    )
    return data.data
  },

  /** 标签血缘反查（GET /dps-proxy/lineage/tags/{tag_code}，#6；无谱系 → 404） */
  async getTagLineage(tagCode: string): Promise<DpsLineageResult> {
    const { data } = await http.get<ApiSuccess<DpsLineageResult>>(`/dps-proxy/lineage/tags/${encodeURIComponent(tagCode)}`)
    return data.data
  },

  /** 影响面查询（GET /dps-proxy/lineage/impact，#7；三层维度，`field_key` 不支持 → 400） */
  async queryImpact(params: DpsImpactQuery): Promise<DpsImpactResult> {
    const { data } = await http.get<ApiSuccess<DpsImpactResult>>('/dps-proxy/lineage/impact', { params })
    return data.data
  },

  /** 措施建议（GET /dps-proxy/measures/suggest?person_id=，#8；只读） */
  async suggestMeasures(personId: string): Promise<DpsMeasureResult> {
    const { data } = await http.get<ApiSuccess<DpsMeasureResult>>('/dps-proxy/measures/suggest', {
      params: { person_id: personId },
    })
    return data.data
  },

  /** AI 标注候选生成（POST /dps-proxy/annotation-adapters/{adapter_id}/generate，#9；默认关闭态零写入） */
  async generateAnnotationCandidates(adapterId: string, body: DpsAnnotationGenerateRequest): Promise<DpsAnnotationCandidate> {
    const { data } = await http.post<ApiSuccess<DpsAnnotationCandidate>>(
      `/dps-proxy/annotation-adapters/${encodeURIComponent(adapterId)}/generate`,
      body,
    )
    return data.data
  },

  /** 评分类型列表（GET /dps-proxy/scoring-types，#10；只读） */
  async listScoringTypes(params?: { page?: number; page_size?: number }): Promise<DpsPaged<DpsScoringType>> {
    const { data } = await http.get<ApiSuccess<DpsPaged<DpsScoringType>>>('/dps-proxy/scoring-types', { params })
    return data.data
  },

  /* ==================== v1.4.10｜补代理 12 端点（#11~#22） ==================== */

  /** 画像模板列表（GET /dps-proxy/templates，#11；过滤 status／profile_type／subject_type） */
  async listTemplates(params?: DpsTemplateFilter): Promise<DpsPaged<DpsPortraitTemplate>> {
    const { data } = await http.get<ApiSuccess<DpsPaged<DpsPortraitTemplate>>>('/dps-proxy/templates', { params })
    return data.data
  },

  /** 画像模板详情（GET /dps-proxy/templates/{code}，#12；原样呈现不假设结构） */
  async getTemplate(code: string): Promise<DpsPortraitTemplate> {
    const { data } = await http.get<ApiSuccess<DpsPortraitTemplate>>(`/dps-proxy/templates/${encodeURIComponent(code)}`)
    return data.data
  },

  /** 模板实际评分项（GET /dps-proxy/templates/{code}/scoring-items；含继承解析后的维度权重与规则） */
  async getTemplateScoringItems(code: string): Promise<DpsTemplateScoringItems> {
    const { data } = await http.get<ApiSuccess<DpsTemplateScoringItems>>(
      `/dps-proxy/templates/${encodeURIComponent(code)}/scoring-items`,
    )
    return data.data
  },

  /** 模板四联视图（GET /dps-proxy/templates/{code}/lineage；P2 族谱/标注模板/标签产出/评分项） */
  async getTemplateLineage(code: string): Promise<DpsTemplateLineage> {
    const { data } = await http.get<ApiSuccess<DpsTemplateLineage>>(
      `/dps-proxy/templates/${encodeURIComponent(code)}/lineage`,
    )
    return data.data
  },

  // ── v2.12.0 模板分类树与子模板挂载 ─────────────────────────

  /** 分类树（GET /dps-proxy/template-categories/tree） */
  async getTemplateCategoryTree(): Promise<DpsTemplateCategory[]> {
    const { data } = await http.get<ApiSuccess<{ items: DpsTemplateCategory[] }>>(
      '/dps-proxy/template-categories/tree',
    )
    return data.data.items
  },

  /** 分类平铺列表（GET /dps-proxy/template-categories） */
  async listTemplateCategories(): Promise<DpsTemplateCategory[]> {
    const { data } = await http.get<ApiSuccess<{ items: DpsTemplateCategory[] }>>(
      '/dps-proxy/template-categories',
    )
    return data.data.items
  },

  /** 标注范围预检（GET /dps-proxy/annotation-scopes/resolve；超阈值 → requires_confirmation） */
  async resolveAnnotationScope(params: {
    type: 'template' | 'category'
    code: string
    only_mounted?: boolean
  }): Promise<DpsAnnotationScopeResult> {
    const { data } = await http.get<ApiSuccess<DpsAnnotationScopeResult>>(
      '/dps-proxy/annotation-scopes/resolve',
      { params },
    )
    return data.data
  },

  /** 新建分类（POST /dps-proxy/template-categories） */
  async createTemplateCategory(payload: {
    code: string
    name: string
    parent_id?: string | null
    sort_order?: number
  }): Promise<DpsTemplateCategory> {
    const { data } = await http.post<ApiSuccess<DpsTemplateCategory>>(
      '/dps-proxy/template-categories',
      payload,
    )
    return data.data
  },

  /** 编辑分类（PUT /dps-proxy/template-categories/{id}；code 不可改） */
  async updateTemplateCategory(
    categoryId: string,
    payload: { name?: string; sort_order?: number; status?: string },
  ): Promise<DpsTemplateCategory> {
    const { data } = await http.put<ApiSuccess<DpsTemplateCategory>>(
      `/dps-proxy/template-categories/${encodeURIComponent(categoryId)}`,
      payload,
    )
    return data.data
  },

  /** 移动分类（POST /dps-proxy/template-categories/{id}/move） */
  async moveTemplateCategory(categoryId: string, parentId: string | null): Promise<DpsTemplateCategory> {
    const { data } = await http.post<ApiSuccess<DpsTemplateCategory>>(
      `/dps-proxy/template-categories/${encodeURIComponent(categoryId)}/move`,
      { parent_id: parentId },
    )
    return data.data
  },

  /** 子模板挂载清单（GET /dps-proxy/templates/{code}/components） */
  async listTemplateComponents(code: string): Promise<DpsTemplateComponent[]> {
    const { data } = await http.get<ApiSuccess<{ items: DpsTemplateComponent[] }>>(
      `/dps-proxy/templates/${encodeURIComponent(code)}/components`,
    )
    return data.data.items
  },

  /** 挂载子模板（POST /dps-proxy/templates/{code}/components） */
  async mountTemplateComponent(
    code: string,
    payload: {
      child_code: string
      sort_order?: number
      required?: boolean
      weight_override?: number | null
    },
  ): Promise<{ parent_code: string; child_code: string; components: DpsTemplateComponent[] }> {
    const { data } = await http.post<
      ApiSuccess<{ parent_code: string; child_code: string; components: DpsTemplateComponent[] }>
    >(`/dps-proxy/templates/${encodeURIComponent(code)}/components`, payload)
    return data.data
  },

  /** 卸载子模板（DELETE /dps-proxy/templates/{code}/components/{child}） */
  async unmountTemplateComponent(code: string, childCode: string): Promise<DpsTemplateComponent[]> {
    const { data } = await http.delete<ApiSuccess<{ components: DpsTemplateComponent[] }>>(
      `/dps-proxy/templates/${encodeURIComponent(code)}/components/${encodeURIComponent(childCode)}`,
    )
    return data.data.components
  },

  /** 子模板排序（PUT /dps-proxy/templates/{code}/components/order） */
  async reorderTemplateComponents(code: string, childCodes: string[]): Promise<DpsTemplateComponent[]> {
    const { data } = await http.put<ApiSuccess<{ items: DpsTemplateComponent[] }>>(
      `/dps-proxy/templates/${encodeURIComponent(code)}/components/order`,
      { child_codes: childCodes },
    )
    return data.data.items
  },

  /** 标注字段映射（GET /dps-proxy/annotation-templates/{code}/field-mapping；P2 字段→标签→评分项） */
  async getAnnotationFieldMapping(
    code: string,
    params?: { portrait_template?: string },
  ): Promise<DpsAnnotationFieldMapping> {
    const { data } = await http.get<ApiSuccess<DpsAnnotationFieldMapping>>(
      `/dps-proxy/annotation-templates/${encodeURIComponent(code)}/field-mapping`,
      { params },
    )
    return data.data
  },

  /** 画像维度规则级明细（GET /dps-proxy/portraits/{id}/dimension-details；P2 标签值/得分/缺值兜底） */
  async getPortraitDimensionDetails(
    personId: string,
    params?: { template_code?: string; dimension?: string },
  ): Promise<DpsPortraitDimensionDetails> {
    const { data } = await http.get<ApiSuccess<DpsPortraitDimensionDetails>>(
      `/dps-proxy/portraits/${encodeURIComponent(personId)}/dimension-details`,
      { params },
    )
    return data.data
  },

  /** 画像异常预警聚合（GET /dps-proxy/portraits/{id}/anomaly-alerts；P3 只读） */
  async getPortraitAnomalyAlerts(
    personId: string,
    params?: { template_code?: string; limit?: number },
  ): Promise<DpsPortraitAnomalyAlerts> {
    const { data } = await http.get<ApiSuccess<DpsPortraitAnomalyAlerts>>(
      `/dps-proxy/portraits/${encodeURIComponent(personId)}/anomaly-alerts`,
      { params },
    )
    return data.data
  },

  /** 孤儿标注模板治理报告（GET /dps-proxy/governance/orphan-annotation-templates；P3 只读） */
  async getOrphanAnnotationTemplates(): Promise<{
    items: DpsOrphanAnnotationTemplate[]
    total: number
  }> {
    const { data } = await http.get<
      ApiSuccess<{ items: DpsOrphanAnnotationTemplate[]; total: number }>
    >('/dps-proxy/governance/orphan-annotation-templates')
    return data.data
  },

  /** 画像模板创建（POST /dps-proxy/templates；400 含字段级原因／409 code 冲突；v2.18.0 起 code 可省略，由服务端按中文名生成） */
  async createTemplate(body: Partial<DpsPortraitTemplate>): Promise<DpsPortraitTemplate> {
    const { data } = await http.post<ApiSuccess<DpsPortraitTemplate>>('/dps-proxy/templates', body)
    return data.data
  },

  /** 画像模板更新（PUT /dps-proxy/templates/{code}，#14；版本递增 ＋ history 留痕） */
  async updateTemplate(code: string, body: Record<string, unknown>): Promise<DpsPortraitTemplate> {
    const { data } = await http.put<ApiSuccess<DpsPortraitTemplate>>(`/dps-proxy/templates/${encodeURIComponent(code)}`, body)
    return data.data
  },

  /** 画像模板激活（POST /dps-proxy/templates/{code}/activate，#15；写，幂等） */
  async activateTemplate(code: string): Promise<DpsPortraitTemplate> {
    const { data } = await http.post<ApiSuccess<DpsPortraitTemplate>>(`/dps-proxy/templates/${encodeURIComponent(code)}/activate`)
    return data.data
  },

  /** 画像模板停用（POST /dps-proxy/templates/{code}/deactivate，#16；写，幂等） */
  async deactivateTemplate(code: string): Promise<DpsPortraitTemplate> {
    const { data } = await http.post<ApiSuccess<DpsPortraitTemplate>>(`/dps-proxy/templates/${encodeURIComponent(code)}/deactivate`)
    return data.data
  },

  /** 标注模板列表（GET /dps-proxy/annotation-templates，#17；过滤 template_code／scenario） */
  async listAnnotationTemplates(params?: DpsAnnotationTemplateFilter): Promise<DpsPaged<DpsAnnotationTemplate>> {
    const { data } = await http.get<ApiSuccess<DpsPaged<DpsAnnotationTemplate>>>('/dps-proxy/annotation-templates', { params })
    return data.data
  },

  /** 标注模板详情（GET /dps-proxy/annotation-templates/{code}，#18；含 `field_schema`） */
  async getAnnotationTemplate(code: string): Promise<DpsAnnotationTemplate> {
    const { data } = await http.get<ApiSuccess<DpsAnnotationTemplate>>(`/dps-proxy/annotation-templates/${encodeURIComponent(code)}`)
    return data.data
  },

  /** 标注模板创建（POST /dps-proxy/annotation-templates，#19；`template_code` 必填且归属须 active） */
  async createAnnotationTemplate(body: Partial<DpsAnnotationTemplate> & { code: string; template_code: string }): Promise<DpsAnnotationTemplate> {
    const { data } = await http.post<ApiSuccess<DpsAnnotationTemplate>>('/dps-proxy/annotation-templates', body)
    return data.data
  },

  /** 标注模板更新／改挂（PUT /dps-proxy/annotation-templates/{code}，#20；含 `template_code` 即改挂；无解除归属） */
  async updateAnnotationTemplate(code: string, body: Record<string, unknown>): Promise<DpsAnnotationTemplate> {
    const { data } = await http.put<ApiSuccess<DpsAnnotationTemplate>>(`/dps-proxy/annotation-templates/${encodeURIComponent(code)}`, body)
    return data.data
  },

  /** 标注模板删除（DELETE /dps-proxy/annotation-templates/{code}，#21；409 时展示关联标注条数） */
  async deleteAnnotationTemplate(code: string): Promise<{ code?: string; deleted?: boolean }> {
    const { data } = await http.delete<ApiSuccess<{ code?: string; deleted?: boolean }>>(
      `/dps-proxy/annotation-templates/${encodeURIComponent(code)}`,
    )
    return data.data
  },

  /** 标签列表（GET /dps-proxy/labels?action=list，#22；`action` 仅此一种，其余 → 400） */
  async listLabels(): Promise<{ items: Record<string, unknown>[] }> {
    const { data } = await http.get<ApiSuccess<{ items: Record<string, unknown>[] }>>('/dps-proxy/labels', {
      params: { action: 'list' },
    })
    return data.data
  },

  /* ==================== v1.4.10｜跨上游协作（非 22 端点） ==================== */

  /** AI 复核辅助（经 llm_proxy → OpenLLM，A-1410-01；返回建议仅供参考，不自动改变候选状态） */
  async assistReview(payload: DpsReviewAssistRequest): Promise<DpsReviewAssistResult> {
    const body = withSessionId(payload as unknown as Record<string, unknown>)
    const { data } = await http.post<ApiSuccess<DpsReviewAssistResult>>('/llm-proxy/chat', {
      ...body,
      stream: false,
    })
    return data.data
  },

  /**
   * 复核提交（DPS 既有端点 POST /portrait/annotations/{id}/review）
   *
   * 契约对齐（OBS-02 深走查修复，2026-10-26）：DPS 端点读取 `status`/`action`，
   * 此前前端发送 `review_status` → 后端判定为「不支持的操作」→ 409，逐条复核实际未生效。
   * 此处统一映射为 DPS 原生字段，并显式带 `current_status`（默认 pending）。
   * 409 = 未复核候选不得进入标签/画像路径。
   */
  async submitReview(annotationId: string, body: DpsReviewSubmitRequest): Promise<Record<string, unknown>> {
    const { data } = await http.post<ApiSuccess<Record<string, unknown>>>(
      `/dps-proxy/annotations/${encodeURIComponent(annotationId)}/review`,
      {
        current_status: 'pending',
        status: body.review_status,
        comment: body.comment,
      },
    )
    return data.data
  },

  /** 标注队列（GET /portrait/annotations；只读分页，供待办与审核历史） */
  async listAnnotations(params: DpsAnnotationQuery = {}): Promise<DpsAnnotationQueue> {
    const { data } = await http.get<ApiSuccess<DpsAnnotationQueue>>('/dps-proxy/annotations', { params })
    return data.data
  },

  /** 标注队列聚合统计（A1；GET /dps-proxy/annotations/stats） */
  async getAnnotationStats(params: {
    group_by?: 'template' | 'status' | 'level' | 'reviewer'
    annotation_template?: string
    review_status?: string
    person_id?: string
  } = {}): Promise<DpsAnnotationStats> {
    const { data } = await http.get<ApiSuccess<DpsAnnotationStats>>('/dps-proxy/annotations/stats', { params })
    return data.data
  },

  /** 领取待审核标注（A2；POST /dps-proxy/annotations/{id}/claim，幂等） */
  async claimAnnotation(annotationId: string): Promise<DpsAnnotationClaimResult> {
    const { data } = await http.post<ApiSuccess<DpsAnnotationClaimResult>>(
      `/dps-proxy/annotations/${encodeURIComponent(annotationId)}/claim`,
      {},
    )
    return data.data
  },

  /**
   * 审核留痕（P4；GET /dps-proxy/annotations/{id}/review-log）
   *
   * 按级升序返回逐级审核记录；标注不存在返回 404，留痕表未迁移返回空列表。
   */
  async getAnnotationReviewLog(annotationId: string): Promise<DpsAnnotationReviewLog> {
    const { data } = await http.get<ApiSuccess<DpsAnnotationReviewLog>>(
      `/dps-proxy/annotations/${encodeURIComponent(annotationId)}/review-log`,
    )
    return data.data
  },

  /**
   * 标注详情（A4；GET /dps-proxy/annotations/{id}）
   *
   * 审核对照一次取全：结构化字段、证据来源、模板/主体归属、审核状态与级数、
   * 审核人/意见、时间戳。上游未升级（404）时调用方应回退队列摘要，不阻断审核。
   */
  async getAnnotationDetail(annotationId: string): Promise<DpsAnnotationDetail> {
    const { data } = await http.get<ApiSuccess<DpsAnnotationDetail>>(
      `/dps-proxy/annotations/${encodeURIComponent(annotationId)}`,
    )
    return data.data
  },

  /**
   * 结构化标注录入（POST /portrait/annotate）
   *
   * 需 `annotation_template` + `fields`，主体必须已有画像（profile）；
   * 归属门禁与字段 schema 校验由 DPS 裁决，失败返回 400 原文。
   */
  async createAnnotation(body: DpsAnnotationCreatePayload): Promise<Record<string, unknown>> {
    const { data } = await http.post<ApiSuccess<Record<string, unknown>>>('/dps-proxy/annotate', body)
    return data.data
  },

  /** 批量复核（DPS POST /portrait/annotations/batch-review，OBS-02-DEF-02） */
  async batchReviewAnnotations(items: DpsBatchReviewItem[]): Promise<DpsBatchReviewResult> {
    const { data } = await http.post<ApiSuccess<DpsBatchReviewResult>>(
      '/dps-proxy/annotations/batch-review',
      { items },
    )
    return data.data
  },

  /* ==================== v2.19.0｜波次 B：组织与引入任务 ==================== */

  /** 组织平铺列表（GET /dps-proxy/orgs） */
  async listOrgs(): Promise<DpsOrgNode[]> {
    const { data } = await http.get<ApiSuccess<DpsOrgNode[]>>('/dps-proxy/orgs')
    return data.data
  },

  /** 组织树（GET /dps-proxy/orgs/tree） */
  async getOrgTree(): Promise<DpsOrgNode[]> {
    const { data } = await http.get<ApiSuccess<DpsOrgNode[]>>('/dps-proxy/orgs/tree')
    return data.data
  },

  /** 组织成员（GET /dps-proxy/orgs/{code}/members） */
  async listOrgMembers(code: string, includeExpired = false): Promise<DpsOrgMember[]> {
    const { data } = await http.get<ApiSuccess<DpsOrgMember[]>>(
      `/dps-proxy/orgs/${encodeURIComponent(code)}/members`,
      { params: includeExpired ? { include_expired: true } : undefined },
    )
    return data.data
  },

  /** 维护组织成员（PUT /dps-proxy/orgs/{code}/members；一人多岗、主岗唯一） */
  async upsertOrgMembers(
    code: string,
    members: DpsOrgMember[],
  ): Promise<{ org_code: string; written: number; primary_cleared: number }> {
    const { data } = await http.put<ApiSuccess<{ org_code: string; written: number; primary_cleared: number }>>(
      `/dps-proxy/orgs/${encodeURIComponent(code)}/members`,
      { members },
    )
    return data.data
  },

  /** 引入预览（POST /dps-proxy/ingest/preview；脱敏，不写库） */
  async previewIngest(body: DpsIngestPreviewRequest): Promise<DpsIngestPreview> {
    const { data } = await http.post<ApiSuccess<DpsIngestPreview>>('/dps-proxy/ingest/preview', body)
    return data.data
  },

  /** 执行引入（POST /dps-proxy/ingest/execute） */
  async executeIngest(body: DpsIngestExecuteRequest): Promise<DpsIngestExecuteResult> {
    const { data } = await http.post<ApiSuccess<DpsIngestExecuteResult>>('/dps-proxy/ingest/execute', body)
    return data.data
  },

  /** 引入任务列表（GET /dps-proxy/ingest/tasks） */
  async listIngestTasks(params?: {
    status?: string
    page?: number
    page_size?: number
  }): Promise<{ total: number; page: number; page_size: number; items: DpsIngestTask[] }> {
    const { data } = await http.get<ApiSuccess<{ total: number; page: number; page_size: number; items: DpsIngestTask[] }>>(
      '/dps-proxy/ingest/tasks',
      { params },
    )
    return data.data
  },

  /** 引入任务详情（GET /dps-proxy/ingest/tasks/{task_id}） */
  async getIngestTask(taskId: string): Promise<DpsIngestTask> {
    const { data } = await http.get<ApiSuccess<DpsIngestTask>>(
      `/dps-proxy/ingest/tasks/${encodeURIComponent(taskId)}`,
    )
    return data.data
  },

  /** 重试引入任务（POST /dps-proxy/ingest/tasks/{task_id}/retry） */
  async retryIngestTask(taskId: string, body: DpsIngestExecuteRequest = {}): Promise<DpsIngestExecuteResult> {
    const { data } = await http.post<ApiSuccess<DpsIngestExecuteResult>>(
      `/dps-proxy/ingest/tasks/${encodeURIComponent(taskId)}/retry`,
      body,
    )
    return data.data
  },

  /** 引入错误行（GET /dps-proxy/ingest/tasks/{task_id}/errors；上游已脱敏） */
  async getIngestTaskErrors(taskId: string): Promise<DpsIngestError[]> {
    const { data } = await http.get<ApiSuccess<DpsIngestError[]>>(
      `/dps-proxy/ingest/tasks/${encodeURIComponent(taskId)}/errors`,
    )
    return data.data
  },

  /* ==================== v2.20.0｜波次 C：进度、调度与审计 ==================== */

  /** 计算进度快照（POST /dps-proxy/progress/calculate；同周期幂等） */
  async calculateProgress(body: DpsProgressCalculateRequest): Promise<DpsProgressSnapshot> {
    const { data } = await http.post<ApiSuccess<DpsProgressSnapshot>>(
      '/dps-proxy/progress/calculate',
      body,
    )
    return data.data
  },

  /** 进度趋势（GET /dps-proxy/progress/{person_id}；周期键倒序） */
  async getProgressTrend(
    personId: string,
    params: { period_type?: 'day' | 'week' | 'month'; limit?: number } = {},
  ): Promise<{ items: DpsProgressSnapshot[] }> {
    const { data } = await http.get<ApiSuccess<{ items: DpsProgressSnapshot[] }>>(
      `/dps-proxy/progress/${encodeURIComponent(personId)}`,
      { params },
    )
    return data.data
  },

  /** 进度事项（GET /dps-proxy/progress/{person_id}/items） */
  async listProgressItems(
    personId: string,
    params: { status?: string; limit?: number } = {},
  ): Promise<{ items: DpsBusinessItem[] }> {
    const { data } = await http.get<ApiSuccess<{ items: DpsBusinessItem[] }>>(
      `/dps-proxy/progress/${encodeURIComponent(personId)}/items`,
      { params },
    )
    return data.data
  },

  /** 逾期事项（GET /dps-proxy/progress/{person_id}/overdue） */
  async listProgressOverdue(personId: string): Promise<{ items: DpsBusinessItem[] }> {
    const { data } = await http.get<ApiSuccess<{ items: DpsBusinessItem[] }>>(
      `/dps-proxy/progress/${encodeURIComponent(personId)}/overdue`,
    )
    return data.data
  },

  /** 业务事项列表（GET /dps-proxy/business-items） */
  async listBusinessItems(
    params: { person_id?: string; status?: string; limit?: number } = {},
  ): Promise<{ items: DpsBusinessItem[] }> {
    const { data } = await http.get<ApiSuccess<{ items: DpsBusinessItem[] }>>(
      '/dps-proxy/business-items',
      { params },
    )
    return data.data
  },

  /** 写入业务事项（POST /dps-proxy/business-items；唯一键幂等） */
  async upsertBusinessItem(body: DpsBusinessItemInput): Promise<DpsBusinessItem> {
    const { data } = await http.post<ApiSuccess<DpsBusinessItem>>(
      '/dps-proxy/business-items',
      body,
    )
    return data.data
  },

  /** cron 表达式预览（GET /dps-proxy/schedules/preview；未来 5 次） */
  async previewCron(expr: string, count = 5): Promise<{ expr: string; next_runs: string[] }> {
    const { data } = await http.get<ApiSuccess<{ expr: string; next_runs: string[] }>>(
      '/dps-proxy/schedules/preview',
      { params: { expr, count } },
    )
    return data.data
  },

  /** 调度列表（GET /dps-proxy/schedules） */
  async listSchedules(): Promise<{ items: DpsSchedule[] }> {
    const { data } = await http.get<ApiSuccess<{ items: DpsSchedule[] }>>('/dps-proxy/schedules')
    return data.data
  },

  /** 创建调度（POST /dps-proxy/schedules） */
  async createSchedule(body: DpsScheduleInput): Promise<DpsSchedule> {
    const { data } = await http.post<ApiSuccess<DpsSchedule>>('/dps-proxy/schedules', body)
    return data.data
  },

  /** 更新调度（PUT /dps-proxy/schedules/{id}；启停/改表达式） */
  async updateSchedule(id: string, body: Partial<DpsScheduleInput>): Promise<DpsSchedule> {
    const { data } = await http.put<ApiSuccess<DpsSchedule>>(
      `/dps-proxy/schedules/${encodeURIComponent(id)}`,
      body,
    )
    return data.data
  },

  /** 既有调度未来触发预览（GET /dps-proxy/schedules/{id}/preview） */
  async previewSchedule(id: string, count = 5): Promise<{ id: string; next_runs: string[] }> {
    const { data } = await http.get<ApiSuccess<{ id: string; next_runs: string[] }>>(
      `/dps-proxy/schedules/${encodeURIComponent(id)}/preview`,
      { params: { count } },
    )
    return data.data
  },

  /** 立即执行调度（POST /dps-proxy/schedules/{id}/run） */
  async runSchedule(id: string): Promise<{ status: string }> {
    const { data } = await http.post<ApiSuccess<{ status: string }>>(
      `/dps-proxy/schedules/${encodeURIComponent(id)}/run`,
      {},
    )
    return data.data
  },
}

/** 组织树节点（v2.19.0） */
export interface DpsOrgNode {
  id?: string
  code: string
  name?: string
  status?: string
  parent_code?: string | null
  path?: string | null
  level?: number
  sort_order?: number
  children?: DpsOrgNode[]
  [key: string]: unknown
}

/** 组织成员（v2.19.0；一人多岗、主岗唯一） */
export interface DpsOrgMember {
  person_id: string
  org_code?: string
  position?: string | null
  is_primary?: boolean | number
  valid_from?: string | null
  valid_to?: string | null
  [key: string]: unknown
}

/** 引入错误行（v2.19.0；record 已脱敏） */
export interface DpsIngestError {
  row_number: number
  error: string
  record?: Record<string, unknown>
}

/** 引入任务（v2.19.0） */
export interface DpsIngestTask {
  id: string
  file_name?: string
  file_path?: string
  file_format?: string
  total_rows?: number
  success_rows?: number
  failed_rows?: number
  status?: string
  trigger_source?: string
  created_at?: string
  finished_at?: string | null
  errors?: DpsIngestError[]
  field_mapping?: Record<string, string>
  [key: string]: unknown
}

/** 引入预览结果（v2.19.0；rows 已按 attributes.* 脱敏） */
export interface DpsIngestPreview {
  rows: Record<string, unknown>[]
  total_sampled: number
  mapping: Record<string, string>
}

/** 引入预览请求 */
export interface DpsIngestPreviewRequest {
  file_path: string
  file_format?: string
  field_mapping?: Record<string, string>
  limit?: number
}

/** 引入执行请求（task_id 或文件信息二选一） */
export interface DpsIngestExecuteRequest {
  task_id?: string
  file_path?: string
  file_name?: string
  file_format?: string
  field_mapping?: Record<string, string>
  trigger_source?: string
  profile_template_code?: string
  annotation_template_code?: string
}

/** 引入执行结果 */
export interface DpsIngestExecuteResult {
  status: string
  task_id: string
  total_records?: number
  processed_records?: number
  error_records?: number
  annotations_created?: number
  idempotent?: boolean
  message?: string
}

/** 批量复核请求条目（逐条复用单条复核语义） */
export interface DpsBatchReviewItem {
  annotation_id: string
  status: 'approved' | 'rejected'
  current_status?: string
  comment?: string
}

/** 批量复核成功条目的审核进度（与单条复核 `review` 同口径） */
export interface DpsBatchReviewItemReview {
  level?: number
  required?: number
  finalized?: boolean
}

/** 批量复核单条结果（单条失败不影响其余条目） */
export interface DpsBatchReviewItemResult {
  annotation_id?: string | null
  ok: boolean
  status?: string | number
  error?: unknown
  review?: DpsBatchReviewItemReview
  [key: string]: unknown
}

/** 批量复核汇总结果 */
export interface DpsBatchReviewResult {
  total: number
  succeeded: number
  failed: number
  items: DpsBatchReviewItemResult[]
}

/* ==================== v2.20.0｜波次 C：进度、调度与审计 ==================== */

/** 业务事项（v2.20.0；唯一键 tenant+person+type+code+planned_at） */
export interface DpsBusinessItem {
  id?: string
  person_id: string
  item_type: string
  item_code?: string | null
  item_name?: string | null
  owner_id?: string | null
  planned_at?: string | null
  completed_at?: string | null
  status?: 'pending' | 'done' | 'cancelled' | string
  quality_score?: number | null
  workload_hours?: number | null
  source?: string
  org_id?: string | null
  tenant_id?: string | null
  [key: string]: unknown
}

/** 业务事项写入请求 */
export interface DpsBusinessItemInput {
  person_id: string
  item_type: string
  item_code?: string
  item_name?: string
  owner_id?: string
  planned_at?: string
  completed_at?: string
  status?: string
  quality_score?: number
  workload_hours?: number
  org_id?: string
  tenant_id?: string
}

/** 进度周期快照（v2.20.0） */
export interface DpsProgressSnapshot {
  id?: string
  person_id: string
  period_type: 'day' | 'week' | 'month' | string
  period_key: string
  template_code?: string | null
  total_items: number
  completed_items: number
  overdue_items: number
  on_time_rate: number
  quality_score: number
  workload_hours: number
  dimensions?: Record<string, { total: number; completed: number; overdue: number; hours: number }>
  computed_at?: string
  history_written?: boolean
  [key: string]: unknown
}

/** 进度计算请求 */
export interface DpsProgressCalculateRequest {
  person_id: string
  template_code?: string
  period_type?: 'day' | 'week' | 'month'
  period_key?: string
}

/** 数据源调度（v2.20.0） */
export interface DpsSchedule {
  id: string
  datasource_id?: string | null
  schedule_type: 'cron' | 'interval' | string
  cron_expr?: string | null
  interval_seconds?: number | null
  enabled?: boolean | number
  next_run_at?: string | null
  last_run_at?: string | null
  last_status?: string | null
  failure_count?: number
  max_failures?: number
  [key: string]: unknown
}

/** 调度创建/更新请求 */
export interface DpsScheduleInput {
  datasource_id?: string
  schedule_type?: 'cron' | 'interval'
  cron_expr?: string
  interval_seconds?: number
  enabled?: boolean
  max_failures?: number
}

/** 审计日志（v2.20.0；detail 不含 PII） */
export interface DpsAuditLog {
  id?: string | number
  timestamp?: string
  user_id?: string
  action?: string
  resource_type?: string
  resource_id?: string | null
  result?: string
  detail?: string | null
  org_id?: string
  tenant_id?: string
  request_id?: string | null
  [key: string]: unknown
}
