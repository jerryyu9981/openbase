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
        <el-button size="small" data-test="workbench-save-draft" @click="saveDraftLocal">保存草稿</el-button>
        <el-button type="primary" plain size="small" data-test="workbench-publish" @click="openPublishWizard">发布向导</el-button>
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
        <el-button
          size="small"
          data-test="next-steps-preflight"
          @click="router.push(`/portrait/dps/templates/${lastSavedCode}/preflight`)"
        >
          评分口径体检
        </el-button>
        <el-button size="small" data-test="next-steps-rules" @click="router.push('/portrait/rules')">查看规则口径</el-button>
        <el-button size="small" data-test="next-steps-calculate" @click="router.push('/portrait/list')">去计算画像</el-button>
      </div>
      <div class="muted sm mt-8">未激活的模板不会参与计算；标注模板必须归属已激活的画像模板。</div>
    </el-card>

    <div class="workbench-body">
      <nav class="section-nav" data-test="workbench-tabs">
        <div class="step-progress">
          <el-progress :percentage="completionPercent" :stroke-width="8" :show-text="false" :status="completionPercent === 100 ? 'success' : undefined" />
          <span class="muted step-progress-text">完成度 {{ completionPercent }}%</span>
        </div>
        <button
          v-for="section in SECTION_ORDER"
          :key="section"
          type="button"
          class="nav-item"
          :class="{ active: activeSection === section, done: sectionComplete(section) }"
          :data-test="`workbench-nav-${section}`"
          @click="activeSection = section"
        >
          <span class="nav-label">{{ SECTION_LABELS[section] }}</span>
          <el-tag v-if="sectionErrorCount(section)" size="small" type="danger">{{ sectionErrorCount(section) }}</el-tag>
          <el-tag v-else-if="sectionWarningCount(section)" size="small" type="warning">{{ sectionWarningCount(section) }}</el-tag>
          <span v-else-if="sectionComplete(section)" class="step-done" data-test="workbench-step-done">✓</span>
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
                <el-option
                  v-for="item in extendsOptions"
                  :key="item.code"
                  :label="item.name || item.code"
                  :value="item.code"
                >
                  <NameCodeLabel :name="item.name" :code="item.code" />
                  <span class="muted sm">{{ item.status || 'draft' }}</span>
                </el-option>
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
          :annotation-templates="annotationTemplates"
        />

        <!-- ⑤ 证据策略 -->
        <EvidencePolicyForm v-else-if="activeSection === 'evidence'" v-model="draft.evidence_policy" />

        <!-- ⑥ 异常规则 -->
        <AnomalyRuleList v-else-if="activeSection === 'anomaly'" v-model="draft.anomaly_rules" />
      </div>

      <div class="issue-pane">
        <el-card shadow="never" data-test="workbench-issues">
          <template #header>
            <div class="issue-head">
              <span>问题清单（点击定位）</span>
              <el-button link type="primary" size="small" :disabled="!issues.length" data-test="workbench-next-issue" @click="focusNextIssue">
                下一处问题
              </el-button>
            </div>
          </template>
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
      <div class="json-diff" data-test="workbench-json-diff">
        <span class="muted sm">相对最近一次保存的变更：</span>
        <el-tag v-if="jsonDiff.added.length" size="small" type="success">新增 {{ jsonDiff.added.join('、') }}</el-tag>
        <el-tag v-if="jsonDiff.changed.length" size="small" type="warning">修改 {{ jsonDiff.changed.join('、') }}</el-tag>
        <el-tag v-if="jsonDiff.removed.length" size="small" type="danger">移除 {{ jsonDiff.removed.join('、') }}</el-tag>
        <span v-if="!jsonDiff.added.length && !jsonDiff.changed.length && !jsonDiff.removed.length" class="muted sm">无变更</span>
      </div>
      <pre class="json-view">{{ draftJson }}</pre>
    </el-dialog>

    <!-- 发布向导：校验 → 口径一致性 → 影响面 → 激活 -->
    <el-drawer v-model="publishOpen" title="发布向导" size="680px" data-test="workbench-publish-wizard">
      <el-steps :active="publishStep" align-center finish-status="success" class="mb-16">
        <el-step title="校验" />
        <el-step title="口径一致性" />
        <el-step title="影响面" />
        <el-step title="激活" />
      </el-steps>

      <div v-loading="publishLoading">
        <template v-if="publishStep === 0">
          <el-alert
            v-if="publishValidation && !publishValidation.valid"
            type="error"
            show-icon
            :closable="false"
            title="存在校验错误，请先修复问题清单"
            data-test="publish-validate-failed"
          />
          <el-alert
            v-else-if="publishValidation"
            type="success"
            show-icon
            :closable="false"
            title="校验通过，可继续检查口径一致性"
            data-test="publish-validate-passed"
          />
          <div v-if="publishErrors.length" class="publish-issues" data-test="publish-errors">
            <div v-for="(item, index) in publishErrors" :key="index" class="publish-issue">
              <span class="muted sm">{{ item.path || '—' }}</span>
              <span>{{ item.message }}</span>
            </div>
          </div>
        </template>

        <template v-else-if="publishStep === 1">
          <el-alert
            v-if="!publishSaved"
            type="warning"
            show-icon
            :closable="false"
            title="新模板尚未保存，无法执行口径一致性预检"
            data-test="publish-unsaved"
          >
            <div>请先返回工作台保存模板，再重新打开发布向导。</div>
          </el-alert>
          <template v-else>
            <div class="publish-metrics">
              <div class="publish-metric">
                <strong class="danger">{{ publishBlock }}</strong>
                <span>阻断（BLOCK）</span>
              </div>
              <div class="publish-metric">
                <strong>{{ publishWarn }}</strong>
                <span>告警（WARN）</span>
              </div>
            </div>
            <el-alert
              v-if="publishBlock"
              type="error"
              show-icon
              :closable="false"
              title="存在 BLOCK，激活将被阻断"
              data-test="publish-block-alert"
            >
              <div class="mb-8">请前往口径体检定位问题模板与字段，修复后重新预检。</div>
              <el-button link type="primary" size="small" @click="goScoringConsistency">去口径体检</el-button>
            </el-alert>
            <el-table :data="publishConsistencyIssues" size="small" empty-text="评分口径一致" data-test="publish-consistency-issues">
              <el-table-column label="级别" width="80">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.severity === 'BLOCK' ? 'danger' : 'warning'">{{ row.severity }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="code" label="问题码" min-width="170" show-overflow-tooltip />
              <el-table-column prop="tag_code" label="标签" min-width="140" show-overflow-tooltip />
              <el-table-column prop="message" label="说明" min-width="200" show-overflow-tooltip />
            </el-table>
          </template>
        </template>

        <template v-else-if="publishStep === 2">
          <div class="ob-metrics">
            <div class="metric">
              <div class="metric-num">{{ publishImpact.annotation_template_count ?? '—' }}</div>
              <div class="metric-label">受影响标注模板</div>
            </div>
            <div class="metric">
              <div class="metric-num">{{ publishImpact.annotation_count ?? '—' }}</div>
              <div class="metric-label">受影响标注数</div>
            </div>
            <div class="metric">
              <div class="metric-num">{{ publishImpact.tag_count ?? '—' }}</div>
              <div class="metric-label">受影响标签数</div>
            </div>
          </div>
          <div class="muted sm mt-8">影响面基于已保存版本计算；本次草稿的修改在激活前不会生效。</div>
        </template>

        <template v-else>
          <el-alert v-if="draft.status === 'active'" type="success" show-icon :closable="false" title="该模板已处于激活状态" />
          <template v-else>
            <div class="publish-confirm">
              确认激活模板 <strong>{{ publishCode }}</strong>？
              激活后将参与画像计算，且标注模板必须归属已激活模板。
            </div>
            <el-alert
              v-if="publishBlock"
              type="error"
              show-icon
              :closable="false"
              class="mt-12"
              title="存在 BLOCK，无法激活"
              data-test="publish-activate-blocked"
            />
            <el-alert
              v-else-if="!publishValidation?.valid"
              type="warning"
              show-icon
              :closable="false"
              class="mt-12"
              title="校验未通过，无法激活"
            />
          </template>
        </template>
      </div>

      <el-alert v-if="publishError" type="error" show-icon :closable="false" class="mt-12" data-test="publish-error">
        <template #title>{{ publishError.title }}</template>
        <div>{{ publishError.detail }}</div>
        <div v-if="publishError.hint" class="hint">{{ publishError.hint }}</div>
      </el-alert>

      <template #footer>
        <el-button :disabled="publishStep === 0" @click="publishStep = Math.max(0, publishStep - 1)">上一步</el-button>
        <el-button v-if="publishStep < 3" type="primary" :disabled="publishStep === 0 && !publishValidation?.valid" @click="publishStep += 1">
          下一步
        </el-button>
        <el-button
          v-else
          type="primary"
          :loading="publishActivating"
          :disabled="draft.status === 'active' || !publishCanActivate"
          data-test="publish-activate"
          @click="confirmPublish"
        >
          确认激活
        </el-button>
        <el-button @click="refreshPublishData">重新检查</el-button>
      </template>
    </el-drawer>

    <DryRunDrawer v-model="dryRunOpen" :template-code="draft.code" :template-payload="payload" />
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import NameCodeLabel from '@/components/common/NameCodeLabel.vue'
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  dpsApi,
  type DpsPortraitTemplate,
  type DpsAnnotationTemplate,
  type DpsPreflightResult,
  type DpsScoringIssue,
  type DpsTemplateValidationResult,
} from '@/core/api/dps'
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
/** 最近一次保存的载荷（用于 JSON 视图展示变更） */
const baselinePayload = ref<Record<string, unknown>>({})
/** 首次水合完成前不展示校验计数，避免「空草稿」错误徽标闪现 */
const hydrated = ref(false)
const publishOpen = ref(false)
const publishStep = ref(0)
const publishLoading = ref(false)
const publishActivating = ref(false)
const publishValidation = ref<DpsTemplateValidationResult | null>(null)
const publishPreflight = ref<DpsPreflightResult | null>(null)
const publishError = ref<DpsErrorPresentation | null>(null)

const payload = computed(() => fromDraft(draft))
watch(
  payload,
  (value) => {
    dirty.value = JSON.stringify(value) !== baselineJson.value
    scheduleDraftPersist()
  },
  { deep: true },
)

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

/** 步骤条：各段错误/提示数与完成状态（AC-TE-1） */
function sectionErrorCount(section: SectionKey): number {
  return issues.value.filter((issue) => issue.section === section && issue.level === 'error').length
}

function sectionWarningCount(section: SectionKey): number {
  return issues.value.filter((issue) => issue.section === section && issue.level === 'warning').length
}

function sectionComplete(section: SectionKey): boolean {
  if (!hydrated.value || sectionErrorCount(section)) return false
  if (section === 'basic') return !!draft.code.trim() && !!draft.name.trim()
  if (section === 'dimensions') return draft.dimension_config.dimensions.length > 0
  return true
}

const completionPercent = computed(() => {
  if (!hydrated.value) return 0
  const done = SECTION_ORDER.filter((section) => sectionComplete(section)).length
  return Math.round((done / SECTION_ORDER.length) * 100)
})

const jsonDiff = computed(() => {
  const before = baselinePayload.value || {}
  const after = payload.value
  const added: string[] = []
  const removed: string[] = []
  const changed: string[] = []
  const keys = new Set([...Object.keys(before), ...Object.keys(after)])
  keys.forEach((key) => {
    const inBefore = Object.prototype.hasOwnProperty.call(before, key)
    const inAfter = Object.prototype.hasOwnProperty.call(after, key)
    if (!inBefore) added.push(key)
    else if (!inAfter) removed.push(key)
    else if (JSON.stringify(before[key]) !== JSON.stringify(after[key])) changed.push(key)
  })
  return { added, removed, changed }
})

const publishSaved = computed(() => isEdit.value || !!lastSavedCode.value)
const publishCode = computed(() => editingCode.value || lastSavedCode.value || draft.code)
const publishErrors = computed(() => (publishValidation.value?.errors || []).filter((item) => item.severity !== 'warning'))
const publishConsistencyIssues = computed<DpsScoringIssue[]>(() => publishPreflight.value?.scoring_consistency?.issues || [])
const publishBlock = computed(() => Number(publishPreflight.value?.scoring_consistency?.block || 0))
const publishWarn = computed(() => Number(publishPreflight.value?.scoring_consistency?.warn || 0))
const publishImpact = computed(() => publishPreflight.value?.impact || {})
const publishCanActivate = computed(
  () => publishSaved.value && !!publishValidation.value?.valid && publishBlock.value === 0,
)

const weightTotal = computed(() => weightSum(draft))
const catalog = computed(() => fieldCatalog(draft))
const draftJson = computed(() => JSON.stringify(payload.value, null, 2))
const dimensionCodes = computed(() =>
  draft.dimension_config.dimensions.map((dimension) => String(dimension.code || '')).filter(Boolean),
)
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
    restoreDraft()
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
  restoreDraft()
}

/** 以当前草稿为基线，重置「未保存」标记 */
function markClean() {
  baselineJson.value = JSON.stringify(fromDraft(draft))
  baselinePayload.value = JSON.parse(baselineJson.value) as Record<string, unknown>
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

/** 「下一处问题」：按步骤顺序向后定位，末尾回到第一条 */
function focusNextIssue() {
  if (!issues.value.length) return
  const currentIndex = SECTION_ORDER.indexOf(activeSection.value)
  const next =
    issues.value.find((issue) => SECTION_ORDER.indexOf(issue.section) > currentIndex) || issues.value[0]
  focusIssue(next)
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
    clearDraft()
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

// ── 草稿本地暂存（AC-TE-4）────────────────────────────────
const draftStorageKey = computed(() => `dps.workbench.draft.${editingCode.value || 'new'}`)
let draftTimer: ReturnType<typeof setTimeout> | undefined

function scheduleDraftPersist() {
  if (!hydrated.value || !dirty.value) return
  if (draftTimer) clearTimeout(draftTimer)
  draftTimer = setTimeout(writeDraft, 800)
}

function writeDraft() {
  try {
    localStorage.setItem(draftStorageKey.value, JSON.stringify({ saved_at: Date.now(), payload: payload.value }))
  } catch {
    // 存储不可用（隐私模式/配额）时静默降级，不阻断保存主流程
  }
}

function saveDraftLocal() {
  writeDraft()
  ElMessage.success('草稿已暂存到本地（Ctrl+S）')
}

function clearDraft() {
  if (draftTimer) {
    clearTimeout(draftTimer)
    draftTimer = undefined
  }
  try {
    localStorage.removeItem(draftStorageKey.value)
    if (editingCode.value) localStorage.removeItem('dps.workbench.draft.new')
  } catch {
    // 忽略存储异常
  }
}

function restoreDraft() {
  let raw = ''
  try {
    raw = localStorage.getItem(draftStorageKey.value) || ''
  } catch {
    return
  }
  if (!raw) return
  try {
    const stored = JSON.parse(raw) as { saved_at?: number; payload?: Record<string, unknown> }
    if (!stored.payload) {
      clearDraft()
      return
    }
    if (JSON.stringify(stored.payload) === baselineJson.value) {
      clearDraft()
      return
    }
    const savedAt = stored.saved_at ? new Date(stored.saved_at).toLocaleString() : '未知时间'
    ElMessageBox.confirm(`检测到 ${savedAt} 的本地草稿，是否恢复？`, '恢复草稿', {
      confirmButtonText: '恢复草稿',
      cancelButtonText: '丢弃',
      type: 'info',
    })
      .then(() => {
        Object.assign(draft, toDraft(stored.payload))
        ElMessage.success('已恢复本地草稿')
      })
      .catch(() => clearDraft())
  } catch {
    clearDraft()
  }
}

// ── 发布向导（AC-TE-2/3）────────────────────────────────
async function openPublishWizard() {
  publishOpen.value = true
  publishStep.value = 0
  publishError.value = null
  await refreshPublishData()
}

async function refreshPublishData() {
  publishLoading.value = true
  publishError.value = null
  try {
    if (isEdit.value) {
      publishValidation.value = await dpsApi.validateTemplate(draft.code || editingCode.value, payload.value)
      const code = publishCode.value
      publishPreflight.value = code ? await dpsApi.preflightTemplate(code).catch(() => null) : null
    } else {
      const errors = localIssues.value.filter((issue) => issue.level === 'error')
      publishValidation.value = {
        valid: errors.length === 0,
        errors: errors.map((issue) => ({ path: issue.path, message: issue.message, severity: 'error' })),
      }
      publishPreflight.value = null
    }
  } catch (caught) {
    publishError.value = describeDpsError(caught)
  } finally {
    publishLoading.value = false
  }
}

async function confirmPublish() {
  if (!publishCanActivate.value) return
  publishActivating.value = true
  publishError.value = null
  try {
    const updated = await dpsApi.activateTemplate(publishCode.value)
    draft.status = String(updated.status || 'active')
    lastSavedCode.value = publishCode.value
    ElMessage.success('模板已激活，可用于画像计算')
    publishOpen.value = false
    await load()
  } catch (caught) {
    publishError.value = describeDpsError(caught)
  } finally {
    publishActivating.value = false
  }
}

function goScoringConsistency() {
  void router.push(`/portrait/dps/scoring-consistency?template=${encodeURIComponent(publishCode.value)}`)
}

/** 快捷键（§8.2）：Ctrl/Cmd+S 暂存草稿、Ctrl/Cmd+Enter 保存 */
function handleShortcut(event: KeyboardEvent) {
  if (!(event.ctrlKey || event.metaKey)) return
  if (event.key.toLowerCase() === 's') {
    event.preventDefault()
    saveDraftLocal()
  } else if (event.key === 'Enter') {
    event.preventDefault()
    void save()
  }
}

onBeforeRouteLeave(async () => {
  if (!dirty.value) return true
  try {
    await ElMessageBox.confirm('存在未保存的修改，确认离开？本地草稿已自动暂存。', '未保存提示', { type: 'warning' })
    return true
  } catch {
    return false
  }
})

onMounted(() => {
  dirty.value = false
  window.addEventListener('keydown', handleShortcut)
  void load()
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleShortcut)
  if (draftTimer) clearTimeout(draftTimer)
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
