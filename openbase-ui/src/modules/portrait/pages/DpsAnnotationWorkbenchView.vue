<template>
  <PageContainer title="标注录入与审核" description="按标注模板录入事实 → 待办队列 → 审核后联动标签" test-id="dps-annotation-workbench">
    <el-alert
      title="结构化标注必须归属一个已激活的画像模板；字段中配置了「目标维度」的项才会在审核通过后生成标签并影响画像。"
      type="info"
      show-icon
      :closable="false"
      class="mb-16"
      data-test="annotation-scope-alert"
    />

    <el-alert
      v-if="pageError"
      :title="pageError"
      type="error"
      show-icon
      :closable="false"
      class="mb-16"
      data-test="annotation-page-error"
    />

    <el-row :gutter="16">
      <el-col :xs="24" :lg="10">
        <el-card shadow="never" header="录入标注" class="mb-16" data-test="annotation-entry-card">
          <el-form label-width="110px">
            <el-form-item label="标注模板" required>
              <el-select
                v-model="selectedTemplate"
                filterable
                placeholder="选择已启用的标注模板"
                style="width: 100%"
                data-test="annotation-template-select"
                @change="onTemplateChange"
              >
                <el-option
                  v-for="item in templates"
                  :key="item.code"
                  :label="`${item.name || item.code}（${item.code}）`"
                  :value="item.code"
                />
              </el-select>
              <div v-if="currentTemplate" class="hint">
                归属画像模板：{{ currentTemplate.template_code || '-' }} · 场景：{{ currentTemplate.scenario || 'general' }}
              </div>
              <div v-if="mappingLoading" class="hint">字段映射加载中…</div>
              <el-alert
                v-else-if="fieldMapping && !fieldMapping.scoring_available"
                type="warning"
                show-icon
                :closable="false"
                class="mt-8"
                data-test="annotation-mapping-unavailable"
                title="归属画像模板当前无运行时评分口径（未激活），字段仅写入标签"
              />
            </el-form-item>

            <el-form-item label="主体 person_id" required>
              <el-input v-model="personId" placeholder="如 P-2026-0001（须已存在画像）" data-test="annotation-person-id" />
              <div class="hint">结构化标注要求主体已有画像，否则后端返回「画像不存在」。</div>
            </el-form-item>

            <el-form-item label="证据来源（文书编号）" :required="evidenceRequired">
              <el-input
                v-model="evidenceSource"
                maxlength="200"
                show-word-limit
                placeholder="如 WS-2026-001"
                data-test="annotation-evidence-source"
              />
              <div class="hint">
                {{ evidenceRequired ? '该画像模板要求证据来源，缺失将无法审核通过' : '可选：填写后可追溯标注依据' }}
              </div>
            </el-form-item>

            <el-form-item v-for="field in schema" :key="field.key" :label="fieldLabel(field)" :required="!!field.required">
              <el-select
                v-if="field.type === 'enum'"
                :model-value="stringValue(field.key)"
                clearable
                placeholder="请选择"
                style="width: 100%"
                @update:model-value="(value: string) => setValue(field.key, value)"
              >
                <el-option v-for="option in field.options || []" :key="option" :label="option" :value="option" />
              </el-select>
              <el-select
                v-else-if="field.type === 'list'"
                :model-value="listValue(field.key)"
                multiple
                filterable
                allow-create
                default-first-option
                placeholder="可多选，回车新增"
                style="width: 100%"
                @update:model-value="(value: string[]) => setValue(field.key, value)"
              >
                <el-option v-for="option in field.options || []" :key="option" :label="option" :value="option" />
              </el-select>
              <el-input
                v-else
                :model-value="stringValue(field.key)"
                :placeholder="fieldPlaceholder(field)"
                @update:model-value="(value: string) => setValue(field.key, value)"
              />
              <div v-if="fieldHint(field)" class="hint field-mapping" data-test="annotation-field-mapping">
                {{ fieldHint(field) }}
              </div>
            </el-form-item>

            <el-empty
              v-if="!schema.length"
              description="请选择一个标注模板以渲染字段"
              :image-size="50"
            />

            <el-alert v-if="submitError" type="error" show-icon :closable="false" class="mb-12" data-test="annotation-submit-error">
              <template #title>{{ submitError }}</template>
            </el-alert>
          </el-form>

          <div class="card-actions">
            <el-button type="primary" :loading="submitting" :disabled="!canSubmit" data-test="annotation-submit" @click="submit">
              提交标注
            </el-button>
            <el-button data-test="annotation-reset" @click="resetForm">重置</el-button>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="14">
        <el-card shadow="never" data-test="annotation-queue-card">
          <template #header>
            <div class="card-head">
              <span>标注队列</span>
              <span class="muted sm">共 {{ total }} 条</span>
            </div>
          </template>

          <div class="filters">
            <el-select v-model="statusFilter" style="width: 130px" data-test="annotation-status-filter" @change="reloadQueue">
              <el-option label="待审核" value="pending" />
              <el-option label="已通过" value="approved" />
              <el-option label="已驳回" value="rejected" />
              <el-option label="全部" value="" />
            </el-select>
            <el-select
              v-model="templateFilter"
              clearable
              placeholder="全部标注模板"
              style="width: 220px"
              data-test="annotation-queue-template-filter"
              @change="reloadQueue"
            >
              <el-option v-for="item in templates" :key="item.code" :label="item.name || item.code" :value="item.code" />
            </el-select>
            <el-button size="small" :loading="loadingQueue" data-test="annotation-queue-refresh" @click="reloadQueue">刷新</el-button>
          </div>

          <el-table v-loading="loadingQueue" :data="rows" size="small" data-test="annotation-queue-table">
            <el-table-column label="时间" width="150">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column prop="person_id" label="主体" width="130" show-overflow-tooltip />
            <el-table-column label="标注模板" min-width="140" show-overflow-tooltip>
              <template #default="{ row }">{{ row.annotation_template_name || row.annotation_template || '-' }}</template>
            </el-table-column>
            <el-table-column label="字段摘要" min-width="180">
              <template #default="{ row }">
                <span class="muted sm">{{ summarize(row.fields) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag size="small" :type="statusType(row.review_status)">{{ statusLabel(row.review_status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="审核进度" width="110" data-test="annotation-review-progress">
              <template #default="{ row }">
                <span class="muted sm" data-test="annotation-review-progress-text">{{ progressLabel(row) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="190" fixed="right">
              <template #default="{ row }">
                <template v-if="row.review_status === 'pending'">
                  <el-button link type="primary" size="small" data-test="annotation-approve" @click="approve(row)">
                    {{ approveLabel(row) }}
                  </el-button>
                  <el-button link type="danger" size="small" data-test="annotation-reject" @click="reject(row)">驳回</el-button>
                </template>
                <span v-else class="muted sm">已处理</span>
                <el-button link type="info" size="small" data-test="annotation-review-log" @click="openReviewLog(row)">
                  记录
                </el-button>
              </template>
            </el-table-column>
            <template #empty>
              <el-empty description="队列为空" :image-size="60" />
            </template>
          </el-table>

          <div class="pager">
            <el-pagination
              layout="total, prev, pager, next"
              :total="total"
              :page-size="pageSize"
              :current-page="page"
              @current-change="onPageChange"
            />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog
      v-model="reviewLogVisible"
      title="审核记录"
      width="620px"
      data-test="annotation-review-log-dialog"
    >
      <el-table
        v-loading="reviewLogLoading"
        :data="reviewLogs"
        size="small"
        data-test="annotation-review-log-table"
      >
        <el-table-column label="级数" width="80">
          <template #default="{ row }">第 {{ row.review_level }} 级</template>
        </el-table-column>
        <el-table-column label="动作" width="90">
          <template #default="{ row }">{{ actionLabel(row.action) }}</template>
        </el-table-column>
        <el-table-column prop="reviewer" label="审核人" width="120" show-overflow-tooltip />
        <el-table-column label="意见" min-width="140">
          <template #default="{ row }">{{ row.comment || '-' }}</template>
        </el-table-column>
        <el-table-column label="时间" width="160">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无审核记录" :image-size="50" />
        </template>
      </el-table>
    </el-dialog>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  dpsApi,
  type DpsAnnotationField,
  type DpsAnnotationFieldMapping,
  type DpsAnnotationFieldMappingEntry,
  type DpsAnnotationReviewLogItem,
  type DpsAnnotationReviewProgress,
  type DpsAnnotationRow,
  type DpsAnnotationTemplate,
  type DpsEvidencePolicy,
} from '@/core/api/dps'
import { describeDpsError } from '@/core/api/error'

const templates = ref<DpsAnnotationTemplate[]>([])
const selectedTemplate = ref('')
const personId = ref('')
const values = reactive<Record<string, unknown>>({})
const submitting = ref(false)
const submitError = ref('')
const pageError = ref('')
/** P2：字段 → 标签 → 评分项映射（按当前标注模板拉取） */
const fieldMapping = ref<DpsAnnotationFieldMapping | null>(null)
const mappingLoading = ref(false)
/** P3：证据来源与归属模板证据策略 */
const evidenceSource = ref('')
const evidencePolicy = ref<DpsEvidencePolicy | null>(null)
const evidenceRequired = computed(() => !!evidencePolicy.value?.require_source)

const rows = ref<DpsAnnotationRow[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const statusFilter = ref('pending')
const templateFilter = ref('')
const loadingQueue = ref(false)
/** P4：审核留痕弹窗 */
const reviewLogVisible = ref(false)
const reviewLogLoading = ref(false)
const reviewLogs = ref<DpsAnnotationReviewLogItem[]>([])

const currentTemplate = computed(() => templates.value.find((item) => item.code === selectedTemplate.value) || null)

/** `field_schema` 可能是数组或 JSON 串，统一解析为字段列表。 */
const schema = computed<DpsAnnotationField[]>(() => {
  const raw = currentTemplate.value?.field_schema
  const parsed = typeof raw === 'string' ? safeParse(raw) : raw
  return Array.isArray(parsed) ? (parsed as DpsAnnotationField[]) : []
})

const canSubmit = computed(() => !!selectedTemplate.value && !!personId.value.trim() && schema.value.length > 0)

/** 字段 key → 映射项（未拉取到映射时为空，回退为原维度提示） */
const mappingByField = computed<Record<string, DpsAnnotationFieldMappingEntry>>(() => {
  const map: Record<string, DpsAnnotationFieldMappingEntry> = {}
  ;(fieldMapping.value?.fields || []).forEach((item) => {
    map[item.key] = item
  })
  return map
})

/** P2 字段提示：写入哪个标签、如何计分、影响哪个评分项。 */
function fieldHint(field: DpsAnnotationField): string {
  const entry = mappingByField.value[field.key]
  if (!entry) {
    return field.target_dimension ? `→ 通过后计入维度 ${field.target_dimension}` : ''
  }
  if (entry.scoring_status === 'no_tag') return '不生成标签（未配置目标维度）'
  const tagPart = `→ 写入 ${entry.tag_code}`
  const scorePart = entry.score_rule ? ` · 计分：${entry.score_rule.summary}` : ''
  if (entry.scoring_status === 'affects' && entry.affects_scoring.length) {
    const hits = entry.affects_scoring
      .map((hit) => `${hit.rule_key}（权重 ${hit.weight}）`)
      .join('、')
    return `${tagPart}${scorePart} · 影响评分项 ${hits}`
  }
  return `${tagPart}${scorePart} · 仅生成标签，当前模板无同名评分项`
}

async function loadFieldMapping() {
  if (!selectedTemplate.value) {
    fieldMapping.value = null
    evidencePolicy.value = null
    return
  }
  mappingLoading.value = true
  const templateCode = currentTemplate.value?.template_code
  const [mappingResult, templateResult] = await Promise.allSettled([
    dpsApi.getAnnotationFieldMapping(selectedTemplate.value),
    templateCode ? dpsApi.getTemplate(templateCode) : Promise.resolve(null),
  ])
  // 映射/策略仅用于解释与必填提示，失败时降级，不阻断录入
  fieldMapping.value = mappingResult.status === 'fulfilled' ? mappingResult.value : null
  evidencePolicy.value =
    templateResult.status === 'fulfilled' ? templateResult.value?.evidence_policy || null : null
  mappingLoading.value = false
}

function safeParse(text: string): unknown {
  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

function fieldLabel(field: DpsAnnotationField): string {
  return field.key
}

function fieldPlaceholder(field: DpsAnnotationField): string {
  if (field.type === 'number') return field.range ? `数值（${(field.range as number[]).join(' ~ ')}）` : '数值'
  if (field.type === 'date') return 'YYYY-MM-DD'
  return '请输入'
}

function stringValue(key: string): string {
  const raw = values[key]
  return raw === null || raw === undefined ? '' : String(raw)
}

function listValue(key: string): string[] {
  const raw = values[key]
  return Array.isArray(raw) ? (raw as string[]) : []
}

function setValue(key: string, value: unknown) {
  values[key] = value
}

function resetForm() {
  Object.keys(values).forEach((key) => delete values[key])
  submitError.value = ''
  personId.value = ''
  evidenceSource.value = ''
  applyDefaults()
}

/** 枚举/列表字段默认取首项，减少录入操作。 */
function applyDefaults() {
  schema.value.forEach((field) => {
    if (field.type === 'enum' && field.options?.length) values[field.key] = field.options[0]
  })
}

async function onTemplateChange() {
  Object.keys(values).forEach((key) => delete values[key])
  submitError.value = ''
  evidenceSource.value = ''
  applyDefaults()
  await loadFieldMapping()
}

async function loadTemplates() {
  try {
    const result = await dpsApi.listAnnotationTemplates({ page: 1, page_size: 100 })
    templates.value = (result.items || []).filter((item) => item.status !== 'inactive')
    if (!selectedTemplate.value && templates.value.length) {
      selectedTemplate.value = templates.value[0].code
      applyDefaults()
      void loadFieldMapping()
    }
  } catch (err) {
    pageError.value = `标注模板加载失败：${describeDpsError(err).detail}`
  }
}

/** 必填项为空即在前端拦截，避免无谓的后端 400。 */
function missingRequired(): string[] {
  return schema.value
    .filter((field) => field.required)
    .filter((field) => {
      const raw = values[field.key]
      if (Array.isArray(raw)) return raw.length === 0
      return raw === undefined || raw === null || String(raw).trim() === ''
    })
    .map((field) => field.key)
}

async function submit() {
  submitError.value = ''
  const missing = missingRequired()
  if (missing.length) {
    submitError.value = `请填写必填字段：${missing.join('、')}`
    return
  }
  if (evidenceRequired.value && !evidenceSource.value.trim()) {
    submitError.value = '该画像模板要求证据来源（文书编号），请补充后提交'
    return
  }

  const fields: Record<string, unknown> = {}
  schema.value.forEach((field) => {
    const raw = values[field.key]
    if (raw === undefined || raw === null || raw === '') return
    if (Array.isArray(raw) && raw.length === 0) return
    fields[field.key] = field.type === 'number' ? Number(raw) : raw
  })

  submitting.value = true
  try {
    await dpsApi.createAnnotation({
      action: 'create',
      person_id: personId.value.trim(),
      annotation_template: selectedTemplate.value,
      template_code: currentTemplate.value?.template_code,
      fields,
      created_by: 'operator',
      evidence_source: evidenceSource.value.trim() || undefined,
    })
    ElMessage.success('标注已提交，进入待审核队列')
    const template = selectedTemplate.value
    resetForm()
    selectedTemplate.value = template
    applyDefaults()
    statusFilter.value = 'pending'
    page.value = 1
    await loadQueue()
  } catch (err) {
    const described = describeDpsError(err)
    submitError.value = described.detail || described.title
  } finally {
    submitting.value = false
  }
}

async function loadQueue() {
  loadingQueue.value = true
  try {
    const result = await dpsApi.listAnnotations({
      annotation_template: templateFilter.value || undefined,
      review_status: statusFilter.value || undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    rows.value = result.items || []
    total.value = Number(result.total || 0)
  } catch (err) {
    pageError.value = `标注队列加载失败：${describeDpsError(err).detail}`
    rows.value = []
    total.value = 0
  } finally {
    loadingQueue.value = false
  }
}

function reloadQueue() {
  page.value = 1
  void loadQueue()
}

function onPageChange(next: number) {
  page.value = next
  void loadQueue()
}

/** 审核通过：联动入参由服务端按标注记录补全，无需前端回传 fields。 */
async function approve(row: DpsAnnotationRow) {
  const required = reviewRequired(row)
  const nextLevel = Math.min(reviewLevel(row) + 1, required)
  const finalStep = nextLevel >= required
  const scope = required > 1 ? `第 ${nextLevel}/${required} 级` : '单级'
  try {
    await ElMessageBox.confirm(
      `确认通过主体「${row.person_id || '-'}」的标注（${scope}）？${
        finalStep ? '终审通过后将按字段目标维度联动标签。' : '非末级通过不会联动标签。'
      }`,
      finalStep ? '终审确认' : '本级通过确认',
      { type: 'info' },
    )
  } catch {
    return
  }
  await doReview(row, 'approved', '')
}

async function reject(row: DpsAnnotationRow) {
  let comment = ''
  try {
    const result = await ElMessageBox.prompt('请填写驳回原因（可留空）', '驳回标注', {
      inputPlaceholder: '如：材料不足/字段与事实不符',
      inputValidator: () => true,
    })
    comment = result.value || ''
  } catch {
    return
  }
  await doReview(row, 'rejected', comment)
}

async function doReview(row: DpsAnnotationRow, status: 'approved' | 'rejected', comment: string) {
  try {
    const result = await dpsApi.submitReview(row.id, { review_status: status, comment })
    if (status === 'rejected') {
      ElMessage.success('已驳回')
    } else {
      const review = result.review as DpsAnnotationReviewProgress | undefined
      if (review && !review.finalized) {
        ElMessage.success(`已通过第 ${review.level} 级，待第 ${review.level + 1} 级审核`)
      } else {
        ElMessage.success('终审通过，标签联动已执行')
      }
    }
    await loadQueue()
  } catch (err) {
    pageError.value = `复核失败：${describeDpsError(err).detail}`
  }
}

/** 应审级数（缺省 1，兼容存量单级数据） */
function reviewRequired(row: DpsAnnotationRow): number {
  return Math.max(1, Number(row.review_levels_required || 1))
}

/** 已通过级数（缺省 0） */
function reviewLevel(row: DpsAnnotationRow): number {
  return Math.max(0, Number(row.review_level || 0))
}

function progressLabel(row: DpsAnnotationRow): string {
  if (row.review_status === 'approved') return '已完成'
  const required = reviewRequired(row)
  return `第 ${Math.min(reviewLevel(row), required)}/${required} 级`
}

function approveLabel(row: DpsAnnotationRow): string {
  const required = reviewRequired(row)
  if (required <= 1) return '通过'
  const nextLevel = reviewLevel(row) + 1
  return nextLevel < required ? `通过本级（${nextLevel}/${required}）` : '终审通过'
}

function actionLabel(action?: string): string {
  return { approved: '通过', rejected: '驳回', modified: '修改' }[action || ''] || action || '-'
}

async function openReviewLog(row: DpsAnnotationRow) {
  reviewLogVisible.value = true
  reviewLogLoading.value = true
  reviewLogs.value = []
  try {
    const payload = await dpsApi.getAnnotationReviewLog(row.id)
    reviewLogs.value = payload.items || []
  } catch (err) {
    pageError.value = `审核记录加载失败：${describeDpsError(err).detail}`
  } finally {
    reviewLogLoading.value = false
  }
}

function statusLabel(status?: string): string {
  return { pending: '待审核', approved: '已通过', rejected: '已驳回', modified: '已修改' }[status || ''] || status || '-'
}

function statusType(status?: string): 'success' | 'warning' | 'danger' | 'info' {
  if (status === 'approved') return 'success'
  if (status === 'rejected') return 'danger'
  if (status === 'pending') return 'warning'
  return 'info'
}

function summarize(fields?: Record<string, unknown>): string {
  if (!fields || !Object.keys(fields).length) return '-'
  return Object.entries(fields)
    .slice(0, 3)
    .map(([key, value]) => `${key}=${Array.isArray(value) ? value.join('/') : String(value)}`)
    .join('，')
}

function formatTime(value?: string): string {
  if (!value) return '-'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false })
}

onMounted(() => {
  void loadTemplates()
  void loadQueue()
})
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.mb-12 { margin-bottom: 12px; }
.card-head { display: flex; justify-content: space-between; align-items: center; }
.card-actions { display: flex; gap: 8px; justify-content: flex-end; }
.filters { display: flex; gap: 8px; align-items: center; margin-bottom: 12px; flex-wrap: wrap; }
.hint { font-size: 12px; color: #9ca3af; line-height: 1.6; margin-top: 4px; }
.field-mapping { color: #6b7280; }
.mt-8 { margin-top: 8px; }
.muted { color: #9ca3af; }
.sm { font-size: 12px; }
.pager { display: flex; justify-content: flex-end; margin-top: 12px; }
</style>
