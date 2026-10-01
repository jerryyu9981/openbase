<template>
  <div class="dps-annotation-field">
    <el-card header="归属（强归属 · 不可置空）" class="mb-16">
      <el-form label-width="120px">
        <el-form-item label="当前归属">
          <el-tag type="success">{{ currentOwner || '-' }}</el-tag>
          <span class="muted sm">status=active</span>
        </el-form-item>
        <el-form-item label="改挂为">
          <el-select v-model="reassignTo" placeholder="仅列 active 画像模板" clearable style="width: 280px" data-test="field-reassign">
            <el-option v-for="item in activeTemplates" :key="item.code" :label="`${item.code}（active）`" :value="item.code" />
          </el-select>
          <el-button type="primary" size="small" :disabled="!reassignTo" data-test="field-reassign-confirm" @click="confirmReassign">确认改挂</el-button>
        </el-form-item>
      </el-form>
      <el-alert type="warning" show-icon :closable="false" data-test="field-owner-warning">
        <template #title>改挂说明</template>
        <div>
          改挂候选项仅列 <strong>active</strong> 的画像模板；改挂后新标注将按新归属校验。
          系统不提供「解除归属」——归属字段不可置空，只能改挂或删除本标注模板。
        </div>
      </el-alert>
      <div class="muted sm mt-12">归属约束三处生效：①创建 ②改挂 ③标注提交（归属不匹配 → 400，消息含期望/实际 template_code）。</div>
    </el-card>

    <el-alert v-if="error" type="error" show-icon :closable="false" class="mb-16" data-test="dps-error">
      <template #title>{{ error.title }}</template>
      <div>{{ error.detail }}</div>
      <div v-if="error.hint" class="hint" data-test="dps-error-hint">{{ error.hint }}</div>
      <span v-if="error.requestId" class="request-id" data-test="dps-request-id">请求编号：{{ error.requestId }}</span>
    </el-alert>

    <el-card header="字段体系 field_schema（5 类字段 · key 唯一）">
      <div class="page-toolbar">
        <el-button size="small" data-test="field-add" @click="addField">新增字段</el-button>
        <el-button size="small" :loading="loading" data-test="field-validate" @click="load">校验 schema（重新加载）</el-button>
        <span class="muted sm">type 仅 string／enum／number／date／list</span>
      </div>

      <div class="ob-table-scroll">
        <el-table :data="rows" stripe empty-text="暂无字段" data-test="field-table">
          <el-table-column label="key" width="170">
            <template #default="{ row }">
              <el-input v-model="row.key" size="small" :class="{ 'is-invalid': duplicateKeys.includes(row.key) }" data-test="field-key" />
            </template>
          </el-table-column>
          <el-table-column label="type" width="130">
            <template #default="{ row }">
              <el-select v-model="row.type" size="small" data-test="field-type">
                <el-option v-for="item in FIELD_TYPES" :key="item" :label="item" :value="item" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="required" width="100">
            <template #default="{ row }">
              <el-switch v-model="row.required" size="small" data-test="field-required" />
            </template>
          </el-table-column>
          <el-table-column label="options（enum 必填）" min-width="220">
            <template #default="{ row }">
              <el-input
                v-model="row.optionsText"
                size="small"
                :disabled="row.type !== 'enum'"
                :class="{ 'is-invalid': row.type === 'enum' && !row.optionsText.trim() }"
                placeholder="逗号分隔，如 线上,门店,电话"
                data-test="field-options"
              />
            </template>
          </el-table-column>
          <el-table-column label="range（number）" width="170">
            <template #default="{ row }">
              <el-input v-model="row.rangeText" size="small" :disabled="row.type !== 'number'" placeholder="0,100" data-test="field-range" />
            </template>
          </el-table-column>
          <el-table-column label="target_dimension" width="180">
            <template #default="{ row }">
              <el-input v-model="row.target_dimension" size="small" placeholder="留空=不参与联动" data-test="field-target-dimension" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="80">
            <template #default="{ $index }">
              <el-button link type="danger" size="small" data-test="field-remove" @click="removeField($index)">删除</el-button>
            </template>
          </el-table-column>
          <template #empty>
            <el-empty description="暂无字段" :image-size="60" data-test="field-empty" />
          </template>
        </el-table>
      </div>

      <el-alert v-if="issues.length" type="error" show-icon :closable="false" class="mt-12" data-test="field-issues">
        <template #title>校验失败（{{ issues.length }} 项）</template>
        <ul class="issue-list">
          <li v-for="item in issues" :key="item">{{ item }}</li>
        </ul>
      </el-alert>

      <div class="muted sm mt-12">
        联动口径：仅含 target_dimension 的字段参与标签联动，生成 tag_code =「{dimension}:{key}」；评分 enum 逆序（首项 100／末项 0）、
        number 裁剪 0~100、其他默认 80；人工标注优先。
      </div>

      <div class="page-toolbar mt-16">
        <el-button type="primary" :loading="saving" :disabled="issues.length > 0" data-test="field-save" @click="save">保存</el-button>
        <el-button data-test="field-cancel" @click="router.push('/dps/annotation-templates')">取消</el-button>
        <span v-if="issues.length" class="muted sm">校验未通过，保存按钮置灰</span>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { dpsApi, type DpsAnnotationField, type DpsPortraitTemplate } from '@/core/api/dps'
import { describeDpsError, type DpsErrorPresentation } from '@/core/api/error'

const FIELD_TYPES = ['string', 'enum', 'number', 'date', 'list'] as const
type FieldType = (typeof FIELD_TYPES)[number]

interface FieldRow {
  key: string
  type: FieldType
  required: boolean
  optionsText: string
  rangeText: string
  target_dimension: string
}

const route = useRoute()
const router = useRouter()
const templateCode = ref(String(route.params.code || ''))
const currentOwner = ref('')
const reassignTo = ref('')
const rows = ref<FieldRow[]>([])
const activeTemplates = ref<DpsPortraitTemplate[]>([])
const loading = ref(false)
const saving = ref(false)
const error = ref<DpsErrorPresentation | null>(null)

const duplicateKeys = computed(() => {
  const counts = new Map<string, number>()
  rows.value.forEach((row) => counts.set(row.key, (counts.get(row.key) || 0) + 1))
  return [...counts.entries()].filter(([, count]) => count > 1).map(([key]) => key)
})

const issues = computed(() => {
  const list: string[] = []
  duplicateKeys.value.forEach((key) => list.push(`字段 key 重复：${key}`))
  rows.value.forEach((row) => {
    if (!row.key.trim()) list.push('存在未填写 key 的字段')
    if (row.type === 'enum' && !row.optionsText.trim()) list.push(`字段 ${row.key || '(未命名)'} 为 enum 时必须提供 options`)
  })
  return list
})

function toRows(schema?: DpsAnnotationField[]): FieldRow[] {
  return (schema || []).map((field) => ({
    key: String(field.key || ''),
    type: (field.type || 'string') as FieldType,
    required: Boolean(field.required),
    optionsText: Array.isArray(field.options) ? field.options.join(',') : '',
    rangeText: Array.isArray(field.range) ? field.range.join(',') : '',
    target_dimension: String(field.target_dimension || ''),
  }))
}

function toSchema(): DpsAnnotationField[] {
  return rows.value.map((row) => {
    const field: DpsAnnotationField = { key: row.key, type: row.type, required: row.required }
    if (row.type === 'enum' && row.optionsText.trim()) field.options = row.optionsText.split(',').map((item) => item.trim()).filter(Boolean)
    if (row.type === 'number' && row.rangeText.trim()) {
      const parts = row.rangeText.split(',').map((item) => Number(item.trim()))
      if (parts.length === 2 && parts.every((n) => Number.isFinite(n))) field.range = [parts[0], parts[1]]
    }
    if (row.target_dimension.trim()) field.target_dimension = row.target_dimension.trim()
    return field
  })
}

async function load() {
  if (!templateCode.value) return
  loading.value = true
  error.value = null
  reassignTo.value = ''
  try {
    const template = await dpsApi.getAnnotationTemplate(templateCode.value)
    currentOwner.value = String(template.template_code || '')
    rows.value = toRows(template.field_schema)
    const owners = await dpsApi.listTemplates({ status: 'active' }).catch(() => ({ items: [] as DpsPortraitTemplate[] }))
    activeTemplates.value = owners.items || []
  } catch (caught) {
    error.value = describeDpsError(caught)
  } finally {
    loading.value = false
  }
}

function addField() {
  rows.value.push({ key: '', type: 'string', required: false, optionsText: '', rangeText: '', target_dimension: '' })
}

function removeField(index: number) {
  rows.value.splice(index, 1)
}

async function confirmReassign() {
  if (!reassignTo.value) return
  saving.value = true
  error.value = null
  try {
    const updated = await dpsApi.updateAnnotationTemplate(templateCode.value, { template_code: reassignTo.value })
    currentOwner.value = String(updated.template_code || reassignTo.value)
    ElMessage.success('归属已改挂；变更后新标注将按新归属校验')
    reassignTo.value = ''
  } catch (caught) {
    error.value = describeDpsError(caught)
  } finally {
    saving.value = false
  }
}

async function save() {
  if (issues.value.length) return
  saving.value = true
  error.value = null
  try {
    const updated = await dpsApi.updateAnnotationTemplate(templateCode.value, { field_schema: toSchema() })
    ElMessage.success(`已保存，版本递增至 v${updated.version ?? '-'}`)
    rows.value = toRows(updated.field_schema)
  } catch (caught) {
    error.value = describeDpsError(caught)
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  void load()
})
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; align-items: center; flex-wrap: wrap; }
.mb-16 { margin-bottom: 16px; }
.mt-12 { margin-top: 12px; }
.mt-16 { margin-top: 16px; }
.muted { color: var(--ob-text-secondary); }
.sm { font-size: 12px; margin-left: 6px; }
.hint { color: var(--ob-text-secondary); font-size: 12px; margin-top: 4px; }
.request-id { color: var(--ob-text-disabled); font-size: 12px; margin-left: 8px; }
.issue-list { margin: 0 0 0 18px; padding: 0; }
.is-invalid :deep(.el-input__wrapper) { box-shadow: 0 0 0 1px var(--ob-danger) inset; }
</style>
