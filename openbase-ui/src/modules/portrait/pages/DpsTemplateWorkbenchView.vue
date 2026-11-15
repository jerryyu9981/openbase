<template>
  <PageContainer title="模板工作台" description="可视化配置模板项与规则引擎（P0）" test-id="dps-template-workbench-page">
    <div class="workbench-head">
      <div class="head-main">
        <div class="title-line">
          <span class="template-name">{{ draft.name || (isEdit ? draft.code : '新建画像模板') }}</span>
          <el-tag size="small" :type="statusTagType(draft.status)">{{ draft.status }}</el-tag>
          <el-tag size="small" type="info">{{ isEdit ? `v${serverVersion || 1}` : '未保存' }}</el-tag>
          <el-tag v-if="weightTotal !== 1" size="small" type="warning" data-test="workbench-weight-total">权重合计 {{ weightTotal.toFixed(2) }}</el-tag>
          <el-tag v-else size="small" type="success" data-test="workbench-weight-total">权重合计 1.00</el-tag>
          <el-tag v-if="errorCount" size="small" type="danger" data-test="workbench-error-count">{{ errorCount }} 项错误</el-tag>
          <el-tag v-if="warningCount" size="small" type="warning" data-test="workbench-warning-count">{{ warningCount }} 项提示</el-tag>
        </div>
        <div class="sub-line">
          code：{{ draft.code || '—' }} · 模板项 6 段 · 保存后版本自动递增并写入变更历史
        </div>
      </div>
      <div class="head-actions">
        <el-button size="small" :loading="validating" data-test="workbench-validate" @click="runServerValidate">校验</el-button>
        <el-button size="small" data-test="workbench-preview" @click="dryRunOpen = true">试运行</el-button>
        <el-button size="small" data-test="workbench-json" @click="jsonOpen = true">JSON 视图</el-button>
        <el-button size="small" data-test="workbench-raw" @click="openRawEditor">高级 JSON 编辑</el-button>
        <el-button type="primary" size="small" :loading="saving" :disabled="!!extendsIssue" data-test="workbench-save" @click="save">保存</el-button>
      </div>
    </div>

    <el-alert v-if="error" type="error" show-icon :closable="false" class="mb-12" data-test="dps-error">
      <template #title>{{ error.title }}</template>
      <div>{{ error.detail }}</div>
      <div v-if="error.hint" class="hint" data-test="dps-error-hint">{{ error.hint }}</div>
      <span v-if="error.requestId" class="request-id" data-test="dps-request-id">请求编号：{{ error.requestId }}</span>
    </el-alert>

    <el-card v-if="lastSavedCode" shadow="never" class="mb-12 next-steps" data-test="workbench-next-steps">
      <div class="next-head">
        <span>模板已保存（{{ lastSavedCode }}）· 下一步</span>
        <el-button link size="small" data-test="next-steps-close" @click="lastSavedCode = ''">关闭</el-button>
      </div>
      <div class="next-actions">
        <el-button
          v-if="draft.status !== 'active'"
          type="primary"
          size="small"
          :loading="activating"
          data-test="next-steps-activate"
          @click="activateSavedTemplate"
        >
          激活模板
        </el-button>
        <el-tag v-else type="success" size="small">已激活，可用于画像计算</el-tag>
        <el-button size="small" data-test="next-steps-annotation" @click="router.push('/portrait/dps/annotation-templates')">
          创建标注模板
        </el-button>
        <el-button size="small" data-test="next-steps-rules" @click="router.push('/portrait/rules')">查看规则口径</el-button>
        <el-button size="small" data-test="next-steps-calculate" @click="router.push('/portrait/list')">去计算画像</el-button>
      </div>
      <div class="muted sm mt-8">未激活的模板不会参与计算；标注模板必须归属已激活的画像模板。</div>
    </el-card>

    <div class="workbench-body">
      <nav class="section-nav" data-test="workbench-tabs">
        <button
          v-for="section in SECTION_ORDER"
          :key="section"
          type="button"
          class="nav-item"
          :class="{ active: activeSection === section }"
          :data-test="`workbench-nav-${section}`"
          @click="activeSection = section"
        >
          <span class="nav-label">{{ SECTION_LABELS[section] }}</span>
          <el-badge v-if="sectionCounts[section]" :value="sectionCounts[section]" type="danger" />
        </button>
      </nav>
      <div class="editor-pane">
        <!-- ① 基础信息 -->
        <el-card v-if="activeSection === 'basic'" shadow="never">
          <el-form label-width="150px">
            <el-form-item label="code *">
              <el-input v-model="draft.code" :disabled="isEdit" placeholder="cc-persona-v1" style="width: 320px" data-test="workbench-code" />
              <span class="muted sm">创建后不可修改；重复 → 409</span>
            </el-form-item>
            <el-form-item label="name *">
              <el-input v-model="draft.name" placeholder="社区矫正画像模板" style="width: 320px" data-test="workbench-name" />
            </el-form-item>
            <el-form-item label="profile_type">
              <el-select v-model="draft.profile_type" style="width: 200px" data-test="workbench-profile-type">
                <el-option v-for="item in PROFILE_TYPES" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>
            <el-form-item label="subject_type">
              <el-select v-model="draft.subject_type" style="width: 200px" data-test="workbench-subject-type">
                <el-option v-for="item in SUBJECT_TYPES" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>
            <el-form-item label="status">
              <el-select v-model="draft.status" style="width: 200px" data-test="workbench-status">
                <el-option label="active（激活）" value="active" />
                <el-option label="draft（草稿，不激活）" value="draft" />
                <el-option label="inactive（停用）" value="inactive" />
              </el-select>
            </el-form-item>
            <el-form-item label="extends（深度 ≤ 2）">
              <el-select v-model="draft.extends" clearable placeholder="选择父模板（可不选）" style="width: 300px" data-test="workbench-extends">
                <el-option v-for="item in extendsOptions" :key="item.code" :label="`${item.code}（${item.status || 'draft'}）`" :value="item.code" />
              </el-select>
            </el-form-item>
            <el-form-item label="description">
              <el-input v-model="draft.description" type="textarea" :rows="3" style="width: 480px" data-test="workbench-description" />
            </el-form-item>
          </el-form>
          <el-alert v-if="extendsIssue" type="error" show-icon :closable="false" data-test="workbench-extends-issue">
            <template #title>{{ extendsIssue }}</template>
            <div>约束：不得指向自身、不得成环、深度上限 2 层、父模板必须存在；最终以服务端 400 为准。</div>
          </el-alert>
          <div class="muted sm mt-8">继承口径：父维度先入 → 子覆盖同名 → 追加新维度；继承节点在画像视图中标注「继承」徽标。</div>
        </el-card>

        <!-- ② 维度与权重 -->
        <div v-else-if="activeSection === 'dimensions'">
          <el-card shadow="never" class="mb-12">
            <div class="dim-summary">
              <span>维度数：{{ draft.dimension_config.dimensions.length }}</span>
              <span>权重合计：<strong :class="{ bad: weightTotal !== 1 }">{{ weightTotal.toFixed(2) }}</strong>（应 = 1.00）</span>
              <el-progress :percentage="Math.min(100, Math.round(weightTotal * 100))" :status="weightTotal === 1 ? 'success' : 'warning'" :stroke-width="10" class="dim-progress" />
            </div>
          </el-card>
          <DimensionEditor
            v-for="(dimension, index) in draft.dimension_config.dimensions"
            :key="index"
            :model-value="dimension"
            :index="index"
            :fields="catalog"
            :invalid-paths="invalidPaths"
            @update:model-value="(value) => (draft.dimension_config.dimensions[index] = value)"
            @remove="removeDimension(index)"
            @duplicate="duplicateDimension(index)"
          />
          <el-button type="primary" plain size="small" data-test="workbench-add-dimension" @click="addDimension">＋新增维度</el-button>
        </div>

        <!-- ③ 属性字段 -->
        <AttributeFieldTable v-else-if="activeSection === 'attributes'" v-model="draft.attributes_schema" />

        <!-- ④ 标签绑定 -->
        <TagBindingTable
          v-else-if="activeSection === 'bindings'"
          v-model="draft.tag_bindings"
          :dimension-codes="dimensionCodes"
          :annotation-templates="annotationTemplateCodes"
        />

        <!-- ⑤ 证据策略 -->
        <EvidencePolicyForm v-else-if="activeSection === 'evidence'" v-model="draft.evidence_policy" />

        <!-- ⑥ 异常规则 -->
        <AnomalyRuleList v-else-if="activeSection === 'anomaly'" v-model="draft.anomaly_rules" />
      </div>

      <div class="issue-pane">
        <el-card shadow="never" header="问题清单（点击定位）" data-test="workbench-issues">
          <div v-if="!issues.length" class="ok-hint">未发现问题，可保存</div>
          <div
            v-for="issue in issues"
            :key="issue.id"
            class="issue-item"
            :class="issue.level"
            data-test="workbench-issue"
            @click="focusIssue(issue)"
          >
            <el-tag size="small" :type="issue.level === 'error' ? 'danger' : 'warning'">{{ issue.level === 'error' ? '错误' : '提示' }}</el-tag>
            <span class="issue-text">{{ issue.message }}</span>
            <span class="issue-section">{{ SECTION_LABELS[issue.section] }}</span>
          </div>
        </el-card>
        <el-card shadow="never" header="校验来源" class="mt-12">
          <div class="muted sm">前端即时校验 + 服务端 `/validate`（保存前自动执行）。服务端返回的字段 path 会映射到同一清单并可点击定位。</div>
        </el-card>
      </div>
    </div>

    <el-dialog v-model="jsonOpen" title="模板 JSON（当前草稿 · 只读）" width="720px" data-test="workbench-json-dialog">
      <pre class="json-view">{{ draftJson }}</pre>
    </el-dialog>

    <DryRunDrawer v-model="dryRunOpen" :template-code="draft.code" :template-payload="payload" />
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { dpsApi, type DpsPortraitTemplate, type DpsAnnotationTemplate } from '@/core/api/dps'
import { describeDpsError, type DpsErrorPresentation } from '@/core/api/error'
import AttributeFieldTable from '../templates/AttributeFieldTable.vue'
import AnomalyRuleList from '../templates/AnomalyRuleList.vue'
import DimensionEditor from '../templates/DimensionEditor.vue'
import DryRunDrawer from '../templates/DryRunDrawer.vue'
import EvidencePolicyForm from '../templates/EvidencePolicyForm.vue'
import TagBindingTable from '../templates/TagBindingTable.vue'
import {
  SECTION_LABELS,
  SECTION_ORDER,
  collectIssues,
  fieldCatalog,
  fromDraft,
  newDimension,
  sectionOfPath,
  toDraft,
  weightSum,
  type SectionKey,
  type TemplateDraft,
  type TemplateIssue,
} from '../templates/model'

const PROFILE_TYPES = ['persona', 'risk', 'business', 'topic']
const SUBJECT_TYPES = ['person', 'unit', 'object']

const route = useRoute()
const router = useRouter()
const editingCode = computed(() => String(route.params.code || ''))
const isEdit = computed(() => !!editingCode.value)

const draft = reactive<TemplateDraft>(toDraft(null))
const templates = ref<DpsPortraitTemplate[]>([])
const annotationTemplates = ref<DpsAnnotationTemplate[]>([])
const serverVersion = ref(0)
const activeSection = ref<SectionKey>('basic')
const serverIssues = ref<TemplateIssue[]>([])
const error = ref<DpsErrorPresentation | null>(null)
const saving = ref(false)
const validating = ref(false)
/** 最近一次保存成功的模板 code（用于展示「下一步」引导） */
const lastSavedCode = ref('')
const activating = ref(false)
const jsonOpen = ref(false)
const dryRunOpen = ref(false)
const dirty = ref(false)
const baselineJson = ref('')
/** 首次水合完成前不展示校验计数，避免「空草稿」错误徽标闪现 */
const hydrated = ref(false)

const payload = computed(() => fromDraft(draft))
watch(payload, (value) => {
  dirty.value = JSON.stringify(value) !== baselineJson.value
})

const localIssues = computed(() => collectIssues(draft))
const issues = computed<TemplateIssue[]>(() => {
  if (!hydrated.value) return []
  const seen = new Set<string>()
  return [...localIssues.value, ...serverIssues.value].filter((issue) => {
    const signature = `${issue.path}|${issue.message}`
    if (seen.has(signature)) return false
    seen.add(signature)
    return true
  })
})
const errorCount = computed(() => issues.value.filter((issue) => issue.level === 'error').length)
const warningCount = computed(() => issues.value.filter((issue) => issue.level === 'warning').length)
const invalidPaths = computed(() => new Set(issues.value.filter((issue) => issue.level === 'error').map((issue) => issue.path)))
const sectionCounts = computed<Record<string, number>>(() => {
  const counts: Record<string, number> = {}
  issues.value.forEach((issue) => {
    counts[issue.section] = (counts[issue.section] || 0) + 1
  })
  return counts
})

const weightTotal = computed(() => weightSum(draft))
const catalog = computed(() => fieldCatalog(draft))
const draftJson = computed(() => JSON.stringify(payload.value, null, 2))
const dimensionCodes = computed(() =>
  draft.dimension_config.dimensions.map((dimension) => String(dimension.code || '')).filter(Boolean),
)
const annotationTemplateCodes = computed(() => annotationTemplates.value.map((item) => item.code))
const templateMap = computed(() => {
  const map: Record<string, DpsPortraitTemplate> = {}
  templates.value.forEach((item) => {
    map[item.code] = item
  })
  return map
})
const extendsOptions = computed(() => templates.value.filter((item) => item.code !== draft.code))

function chainDepth(startCode: string): number {
  let depth = 0
  let cursor: string | undefined = startCode
  const seen = new Set<string>()
  while (cursor) {
    if (seen.has(cursor)) return 99
    seen.add(cursor)
    const parent: DpsPortraitTemplate | undefined = templateMap.value[cursor]
    if (!parent?.extends) break
    cursor = parent.extends
    depth += 1
  }
  return depth
}

const extendsIssue = computed(() => {
  if (!draft.extends) return ''
  if (draft.extends === draft.code) return 'extends 不得指向自身'
  if (!templateMap.value[draft.extends]) return 'extends 指定的父模板不存在'
  if (1 + chainDepth(draft.extends) > 2) return 'extends 继承深度超过 2 层'
  return ''
})

function statusTagType(status: string): 'success' | 'info' | 'warning' {
  if (status === 'active') return 'success'
  if (status === 'inactive') return 'info'
  return 'warning'
}

async function load() {
  const list = await dpsApi.listTemplates().catch(() => ({ items: [] as DpsPortraitTemplate[] }))
  templates.value = list.items || []
  const annotations = await dpsApi.listAnnotationTemplates().catch(() => ({ items: [] as DpsAnnotationTemplate[] }))
  annotationTemplates.value = annotations.items || []
  if (!isEdit.value) {
    Object.assign(draft, toDraft(null))
    markClean()
    hydrated.value = true
    return
  }
  try {
    const template = await dpsApi.getTemplate(editingCode.value)
    Object.assign(draft, toDraft(template))
    serverVersion.value = Number(template.version || 0)
    markClean()
  } catch (caught) {
    error.value = describeDpsError(caught)
  } finally {
    hydrated.value = true
  }
}

/** 以当前草稿为基线，重置「未保存」标记 */
function markClean() {
  baselineJson.value = JSON.stringify(fromDraft(draft))
  dirty.value = false
}

function addDimension() {
  draft.dimension_config.dimensions.push(newDimension())
}

function removeDimension(index: number) {
  draft.dimension_config.dimensions.splice(index, 1)
}

function duplicateDimension(index: number) {
  const clone = JSON.parse(JSON.stringify(draft.dimension_config.dimensions[index]))
  clone.code = `${clone.code || 'dim'}_copy`
  clone.name = `${clone.name || '维度'}（副本）`
  draft.dimension_config.dimensions.splice(index + 1, 0, clone)
}

function focusIssue(issue: TemplateIssue) {
  activeSection.value = issue.section || sectionOfPath(issue.path)
}

function mapServerIssues(items: Array<Record<string, unknown>>): TemplateIssue[] {
  return (items || []).map((item, index) => ({
    id: `server-${index}`,
    level: String(item.severity || 'error') === 'warning' ? 'warning' : 'error',
    section: sectionOfPath(String(item.path || '')),
    path: String(item.path || ''),
    message: String(item.message || ''),
  }))
}

async function runServerValidate(): Promise<boolean> {
  validating.value = true
  error.value = null
  try {
    const report = await dpsApi.validateTemplate(draft.code || editingCode.value || 'draft', payload.value)
    serverIssues.value = mapServerIssues((report.errors || []) as Array<Record<string, unknown>>)
    if (report.valid) ElMessage.success(`服务端校验通过（权重合计 ${Number(report.weight_sum).toFixed(2)}）`)
    else ElMessage.warning(`服务端校验未通过：${serverIssues.value.filter((item) => item.level === 'error').length} 项错误`)
    return !!report.valid
  } catch (caught) {
    // 新建模板尚未落库时，`/validate` 走模板兜底会导致 404：视为仅本地校验
    const status = (caught as { response?: { status?: number } })?.response?.status
    if (!isEdit.value && status === 404) {
      serverIssues.value = []
      ElMessage.info('新模板尚未保存，已执行本地校验')
      return localIssues.value.every((issue) => issue.level !== 'error')
    }
    error.value = describeDpsError(caught)
    return false
  } finally {
    validating.value = false
  }
}

async function save() {
  error.value = null
  if (localIssues.value.some((issue) => issue.level === 'error')) {
    ElMessage.warning('存在未修复的错误，请先按问题清单处理')
    return
  }
  if (!draft.code.trim() || !draft.name.trim()) {
    ElMessage.warning('code 与 name 为必填项')
    return
  }
  const valid = await runServerValidate()
  if (!valid) return

  saving.value = true
  try {
    if (isEdit.value) {
      const updated = await dpsApi.updateTemplate(editingCode.value, payload.value)
      serverVersion.value = Number(updated.version || 0)
      lastSavedCode.value = editingCode.value
      ElMessage.success(`已保存，版本递增至 v${updated.version ?? '-'}`)
    } else {
      const created = await dpsApi.createTemplate(payload.value as Partial<DpsPortraitTemplate> & { code: string })
      lastSavedCode.value = created.code
      ElMessage.success(`创建成功（v${created.version ?? 1}）`)
      await router.replace(`/portrait/dps/templates/${created.code}/edit`)
    }
    Object.assign(draft, toDraft(await dpsApi.getTemplate(draft.code)))
    markClean()
  } catch (caught) {
    error.value = describeDpsError(caught)
  } finally {
    saving.value = false
  }
}

function openRawEditor() {
  if (!isEdit.value) {
    ElMessage.info('请先保存模板后再使用高级 JSON 编辑')
    return
  }
  void router.push(`/portrait/dps/templates/${editingCode.value}/raw`)
}

/** 保存后的下一步：激活当前模板（未激活模板不参与计算）。 */
async function activateSavedTemplate() {
  if (!lastSavedCode.value) return
  activating.value = true
  try {
    const updated = await dpsApi.activateTemplate(lastSavedCode.value)
    draft.status = String(updated.status || 'active')
    ElMessage.success('模板已激活，可用于画像计算')
  } catch (caught) {
    error.value = describeDpsError(caught)
  } finally {
    activating.value = false
  }
}

onBeforeRouteLeave(async () => {
  if (!dirty.value) return true
  try {
    await ElMessageBox.confirm('存在未保存的修改，确认离开？', '未保存提示', { type: 'warning' })
    return true
  } catch {
    return false
  }
})

onMounted(() => {
  dirty.value = false
  void load()
})
</script>

<style scoped>
.workbench-head { display: flex; gap: 12px; align-items: flex-start; justify-content: space-between; margin-bottom: 12px; flex-wrap: wrap; }
.title-line { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.template-name { font-size: 16px; font-weight: 600; }
.sub-line { font-size: 12px; color: var(--ob-text-secondary); margin-top: 4px; }
.head-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.workbench-body { display: flex; gap: 14px; align-items: flex-start; }
.editor-pane { flex: 1 1 auto; min-width: 0; }
.issue-pane { flex: 0 0 300px; }
.section-nav { flex: 0 0 150px; display: flex; flex-direction: column; gap: 4px; position: sticky; top: 12px; }
.nav-item { display: flex; align-items: center; justify-content: space-between; gap: 6px; padding: 8px 10px; border: 1px solid transparent; border-radius: 6px; background: transparent; color: var(--ob-text-primary); cursor: pointer; font-size: 13px; text-align: left; }
.nav-item:hover { background: var(--ob-bg-hover, rgba(0, 0, 0, 0.04)); }
.nav-item.active { background: var(--ob-bg-active, rgba(64, 128, 255, 0.12)); border-color: var(--ob-primary); color: var(--ob-primary); font-weight: 600; }
.nav-label { flex: 1 1 auto; }
.dim-summary { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; font-size: 13px; }
.dim-progress { width: 220px; }
.bad { color: var(--ob-danger); }
.issue-item { display: flex; align-items: flex-start; gap: 6px; padding: 6px; border-radius: 4px; cursor: pointer; }
.issue-item:hover { background: var(--ob-bg-hover, rgba(0, 0, 0, 0.04)); }
.issue-item.error .issue-text { color: var(--ob-danger); }
.issue-item.warning .issue-text { color: var(--ob-warning); }
.issue-text { flex: 1 1 auto; font-size: 12px; }
.issue-section { font-size: 11px; color: var(--ob-text-disabled); }
.ok-hint { color: var(--ob-success); font-size: 13px; }
.json-view { margin: 0; font-size: 12px; max-height: 60vh; overflow: auto; }
.mb-12 { margin-bottom: 12px; }
.mt-12 { margin-top: 12px; }
.mt-8 { margin-top: 8px; }
.muted { color: var(--ob-text-secondary); }
.sm { font-size: 12px; margin-left: 6px; }
.hint { color: var(--ob-text-secondary); font-size: 12px; margin-top: 4px; }
.request-id { color: var(--ob-text-disabled); font-size: 12px; margin-left: 8px; }
.next-steps { border: 1px solid var(--ob-primary-light, #bfdbfe); background: var(--ob-primary-lighter, #f8fbff); }
.next-head { display: flex; justify-content: space-between; align-items: center; font-size: 13px; font-weight: 600; }
.next-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 10px; }
</style>
