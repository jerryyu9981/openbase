<template>
  <PageContainer title="标注模板字段设计" description="字段配置、标签映射与实时表单预览" test-id="dps-annotation-field-view-page">
    <el-card header="归属（强归属 · 不可置空）" class="mb-16">
      <el-form label-width="120px">
        <el-form-item label="当前归属">
          <el-tag type="success">
            <NameCodeLabel :name="ownerTemplate?.name" :code="currentOwner" />
          </el-tag>
          <span class="muted sm">status=active · 已有标注 {{ annotationTotal === null ? '—' : annotationTotal }} 条</span>
        </el-form-item>
        <el-form-item label="改挂为">
          <el-select v-model="reassignTo" placeholder="仅列 active 画像模板" clearable style="width: 280px" data-test="field-reassign">
            <el-option
              v-for="item in activeTemplates"
              :key="item.code"
              :label="item.name || item.code"
              :value="item.code"
            >
              <NameCodeLabel :name="item.name" :code="item.code" />
            </el-option>
          </el-select>
          <el-button type="primary" size="small" :disabled="!reassignTo" data-test="field-reassign-confirm" @click="confirmReassign">
            确认改挂
          </el-button>
        </el-form-item>
      </el-form>
      <el-alert type="warning" show-icon :closable="false" data-test="field-owner-warning">
        <template #title>改挂说明</template>
        <div>
          改挂候选项仅列 <strong>active</strong> 的画像模板；改挂前会展示已有标注数等影响面。
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

    <div class="designer-layout">
      <section class="designer-main">
        <el-card v-loading="loading">
          <template #header>
            <div class="card-head">
              <span>字段体系 field_schema（{{ rows.length }} 个字段 · key 唯一）</span>
              <div>
                <el-button size="small" data-test="field-add" @click="addField">＋新增字段</el-button>
                <el-button size="small" :loading="loading" data-test="field-validate" @click="load">重新加载</el-button>
              </div>
            </div>
          </template>

          <el-empty v-if="!rows.length" description="暂无字段，请先新增" :image-size="60" data-test="field-empty" />
          <div
            v-for="(row, index) in rows"
            :key="row.uid"
            class="field-row"
            :class="{ dragging: dragIndex === index }"
            data-test="field-row"
            @dragover.prevent
            @drop="dropField(index)"
          >
            <span class="drag-handle" draggable="true" title="拖拽排序" @dragstart="dragStart(index)" @dragend="dragIndex = -1">
              ⋮⋮
            </span>
            <div class="field-grid">
              <el-input v-model="row.key" size="small" placeholder="key（如 channel）" class="cell-key" data-test="field-key" />
              <el-select v-model="row.type" size="small" class="cell-type" data-test="field-type">
                <el-option v-for="item in ANNOTATION_FIELD_TYPES" :key="item" :label="item" :value="item" />
              </el-select>
              <el-switch v-model="row.required" size="small" active-text="必填" class="cell-required" data-test="field-required" />
              <el-input
                v-if="row.type === 'enum'"
                v-model="row.optionsText"
                size="small"
                class="cell-options"
                placeholder="枚举值，逗号分隔：线上,门店"
                :class="{ 'is-invalid': row.type === 'enum' && !row.optionsText.trim() }"
                data-test="field-options"
              />
              <el-input
                v-else-if="row.type === 'number'"
                v-model="row.rangeText"
                size="small"
                class="cell-options"
                placeholder="区间（可选）：0,100"
                data-test="field-range"
              />
              <span v-else class="cell-options placeholder">—</span>
              <el-select
                v-model="row.target_dimension"
                size="small"
                clearable
                filterable
                class="cell-dimension"
                placeholder="目标维度（留空=不进画像）"
                data-test="field-target-dimension"
              >
                <el-option v-for="item in dimensionOptions" :key="item.code" :label="item.label" :value="item.code" />
              </el-select>
              <span class="field-hint" data-test="field-tag-hint">{{ hintFor(row) }}</span>
            </div>
            <div class="field-actions">
              <el-button link size="small" :disabled="index === 0" data-test="field-up" @click="moveField(index, index - 1)">↑</el-button>
              <el-button
                link
                size="small"
                :disabled="index === rows.length - 1"
                data-test="field-down"
                @click="moveField(index, index + 1)"
              >
                ↓
              </el-button>
              <el-button link type="danger" size="small" data-test="field-remove" @click="removeField(index)">删除</el-button>
            </div>
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
            <el-button data-test="field-cancel" @click="router.push('/portrait/dps/annotation-templates')">取消</el-button>
            <span v-if="issues.length" class="muted sm">校验未通过，保存按钮置灰</span>
          </div>
        </el-card>
      </section>

      <aside class="preview-pane">
        <el-card header="表单预览（与标注作业台同源）" data-test="field-preview">
          <el-form label-position="top">
            <el-form-item
              v-for="row in rows"
              :key="`preview-${row.uid}`"
              :label="row.key || '（未命名字段）'"
              :required="row.required"
            >
              <el-select v-if="row.type === 'enum'" disabled placeholder="单选（options）" style="width: 100%">
                <el-option v-for="option in row.optionsText.split(',').filter(Boolean)" :key="option" :label="option" :value="option" />
              </el-select>
              <el-select v-else-if="row.type === 'list'" multiple disabled placeholder="多选（options）" style="width: 100%">
                <el-option v-for="option in row.optionsText.split(',').filter(Boolean)" :key="option" :label="option" :value="option" />
              </el-select>
              <el-input v-else-if="row.type === 'date'" disabled placeholder="YYYY-MM-DD" />
              <el-input v-else-if="row.type === 'number'" disabled :placeholder="row.rangeText ? `数值（${row.rangeText}）` : '数值'" />
              <el-input v-else disabled placeholder="文本" />
              <div class="preview-hint">{{ hintFor(row) }}</div>
            </el-form-item>
            <el-empty v-if="!rows.length" description="添加字段后在此预览" :image-size="48" />
          </el-form>
        </el-card>
        <div class="muted sm mt-8">预览仅展示控件形态与映射提示，提交校验以标注作业台为准。</div>
      </aside>
    </div>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import NameCodeLabel from '@/components/common/NameCodeLabel.vue'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { dpsApi, type DpsPortraitTemplate } from '@/core/api/dps'
import { describeDpsError, type DpsErrorPresentation } from '@/core/api/error'
import {
  ANNOTATION_FIELD_TYPES,
  buildFieldTagHint,
  dimensionOptionsFromTemplate,
  fromFieldRows,
  scoringTagCodesFromTemplate,
  toFieldRows,
  validateFieldRows,
  type AnnotationFieldRow,
} from '../annotation/fieldSchema'

interface DesignerRow extends AnnotationFieldRow {
  uid: string
}

let uidSeed = 0

function makeRow(row: AnnotationFieldRow): DesignerRow {
  uidSeed += 1
  return { ...row, uid: `field-${uidSeed}` }
}

const route = useRoute()
const router = useRouter()
const templateCode = ref(String(route.params.code || ''))
const currentOwner = ref('')
const reassignTo = ref('')
const rows = ref<DesignerRow[]>([])
const activeTemplates = ref<DpsPortraitTemplate[]>([])
const ownerTemplate = ref<DpsPortraitTemplate | null>(null)
const annotationTotal = ref<number | null>(null)
const loading = ref(false)
const saving = ref(false)
const dragIndex = ref(-1)
const error = ref<DpsErrorPresentation | null>(null)

const dimensionOptions = computed(() => dimensionOptionsFromTemplate(ownerTemplate.value))
const scoringTags = computed(() => scoringTagCodesFromTemplate(ownerTemplate.value))
const issues = computed(() => validateFieldRows(rows.value))

function hintFor(row: AnnotationFieldRow): string {
  return buildFieldTagHint(row, scoringTags.value)
}

async function loadOwnerTemplate(ownerCode: string) {
  if (!ownerCode) {
    ownerTemplate.value = null
    return
  }
  ownerTemplate.value = await dpsApi.getTemplate(ownerCode).catch(() => null)
}

async function loadImpact() {
  if (!templateCode.value) return
  annotationTotal.value = await dpsApi
    .listAnnotations({ annotation_template: templateCode.value, page_size: 1 })
    .then((result) => result.total)
    .catch(() => null)
}

async function load() {
  if (!templateCode.value) return
  loading.value = true
  error.value = null
  reassignTo.value = ''
  try {
    const template = await dpsApi.getAnnotationTemplate(templateCode.value)
    currentOwner.value = String(template.template_code || '')
    rows.value = toFieldRows(template.field_schema).map(makeRow)
    const owners = await dpsApi.listTemplates({ status: 'active' }).catch(() => ({ items: [] as DpsPortraitTemplate[] }))
    activeTemplates.value = owners.items || []
    await Promise.all([loadOwnerTemplate(currentOwner.value), loadImpact()])
  } catch (caught) {
    error.value = describeDpsError(caught)
  } finally {
    loading.value = false
  }
}

function addField() {
  rows.value.push(makeRow({ key: '', type: 'string', required: false, optionsText: '', rangeText: '', target_dimension: '' }))
}

function removeField(index: number) {
  rows.value.splice(index, 1)
}

function moveField(from: number, to: number) {
  if (to < 0 || to >= rows.value.length) return
  const [moved] = rows.value.splice(from, 1)
  rows.value.splice(to, 0, moved)
}

function dragStart(index: number) {
  dragIndex.value = index
}

function dropField(target: number) {
  if (dragIndex.value < 0 || dragIndex.value === target) return
  moveField(dragIndex.value, target)
  dragIndex.value = -1
}

async function confirmReassign() {
  if (!reassignTo.value) return
  const target = reassignTo.value
  const impact =
    annotationTotal.value === null
      ? '无法读取已有标注数，请谨慎改挂。'
      : `该标注模板已有 ${annotationTotal.value} 条标注，历史标注保留原归属。`
  try {
    await ElMessageBox.confirm(
      `${impact}改挂后新标注将按 ${target} 校验。确认改挂？`,
      '确认改挂',
      { type: 'warning', confirmButtonText: '确认改挂', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  saving.value = true
  error.value = null
  try {
    const updated = await dpsApi.updateAnnotationTemplate(templateCode.value, { template_code: target })
    currentOwner.value = String(updated.template_code || target)
    await Promise.all([loadOwnerTemplate(currentOwner.value), loadImpact()])
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
    const updated = await dpsApi.updateAnnotationTemplate(templateCode.value, { field_schema: fromFieldRows(rows.value) })
    ElMessage.success(`已保存，版本递增至 v${updated.version ?? '-'}`)
    rows.value = toFieldRows(updated.field_schema).map(makeRow)
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
.designer-layout { display: flex; gap: 16px; align-items: flex-start; }
.designer-main { flex: 1 1 auto; min-width: 0; }
.preview-pane { flex: 0 0 320px; position: sticky; top: 12px; }
.card-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; flex-wrap: wrap; }
.field-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 8px;
  border: 1px solid var(--ob-border);
  border-radius: var(--ob-radius-md);
  margin-bottom: 8px;
  background: var(--ob-bg-container, #fff);
}
.field-row.dragging { border-color: var(--ob-primary); box-shadow: 0 0 0 1px var(--ob-primary) inset; }
.drag-handle { cursor: grab; color: var(--ob-text-secondary); font-size: 12px; letter-spacing: -1px; padding-top: 4px; user-select: none; }
.field-grid { flex: 1 1 auto; display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.cell-key { width: 150px; }
.cell-type { width: 110px; }
.cell-required { margin-right: 4px; }
.cell-options { width: 210px; }
.cell-dimension { width: 220px; }
.placeholder { color: var(--ob-text-disabled); font-size: 12px; }
.field-hint { flex: 1 1 100%; font-size: 12px; color: var(--ob-text-secondary); }
.field-actions { display: flex; align-items: center; gap: 2px; }
.preview-hint { font-size: 11px; color: var(--ob-text-secondary); line-height: 1.5; }
.mb-16 { margin-bottom: 16px; }
.mt-12 { margin-top: 12px; }
.mt-16 { margin-top: 16px; }
.mt-8 { margin-top: 8px; }
.muted { color: var(--ob-text-secondary); }
.sm { font-size: 12px; margin-left: 6px; }
.hint { color: var(--ob-text-secondary); font-size: 12px; margin-top: 4px; }
.request-id { color: var(--ob-text-disabled); font-size: 12px; margin-left: 8px; }
.issue-list { margin: 0 0 0 18px; padding: 0; }
.is-invalid :deep(.el-input__wrapper) { box-shadow: 0 0 0 1px var(--ob-danger) inset; }
</style>
