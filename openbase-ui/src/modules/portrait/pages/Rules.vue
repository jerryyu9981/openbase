<template>
  <PageContainer title="评分规则" description="按当前激活的画像模板只读展示维度权重与打分规则；编辑请进入画像模板工作台" test-id="rules-page">
    <el-alert
      title="规则以「画像模板」为单位生效：本页只读展示当前激活模板的维度、权重与打分规则，编辑请进入模板工作台。"
      type="info"
      show-icon
      :closable="false"
      class="mb-16"
      data-test="rules-scope-alert"
    />

    <el-alert
      v-if="presentation"
      :title="presentation.title"
      type="error"
      show-icon
      :closable="false"
      class="mb-16"
      data-test="rule-error"
    >
      <div>{{ presentation.detail }}</div>
      <span v-if="presentation.requestId" class="request-id">请求编号：{{ presentation.requestId }}</span>
    </el-alert>

    <el-card shadow="never" class="mb-16">
      <div class="toolbar">
        <span class="toolbar-label">激活模板</span>
        <el-select
          v-model="selectedCode"
          placeholder="选择要查看的激活模板"
          style="width: 280px"
          data-test="rules-template-select"
          @change="loadTemplate"
        >
          <el-option
            v-for="item in templates"
            :key="item.code"
            :label="item.name || item.code"
            :value="item.code"
          >
            <NameCodeLabel :name="item.name" :code="item.code" />
          </el-option>
        </el-select>
        <el-tag v-if="activeTemplate?.version" size="small" type="info">v{{ activeTemplate.version }}</el-tag>
        <el-tag v-if="activeTemplate?.extends" size="small" type="warning">
          继承 <NameCodeLabel :name="extendsName" :code="activeTemplate.extends" />
        </el-tag>
        <div class="toolbar-actions">
          <el-button size="small" :loading="loading" data-test="rules-refresh" @click="reload">刷新</el-button>
          <el-button
            size="small"
            type="primary"
            plain
            :disabled="!selectedCode"
            data-test="rules-open-workbench"
            @click="openWorkbench"
          >
            去工作台编排
          </el-button>
          <el-button size="small" data-test="rules-open-annotations" @click="openAnnotationTemplates">
            标注模板管理
          </el-button>
        </div>
      </div>

      <div v-if="activeTemplate" class="summary">
        <span>维度数：<strong>{{ dimensions.length }}</strong></span>
        <span>规则数：<strong>{{ ruleCount }}</strong></span>
        <span>
          权重合计：
          <strong :class="{ bad: weightTotal !== 1 }">{{ weightTotal.toFixed(2) }}</strong>
          <span class="muted">（应 = 1.00，否则总分口径被等比缩放）</span>
        </span>
      </div>
    </el-card>

    <div v-loading="loading">
      <el-empty
        v-if="!loading && !templates.length"
        description="当前没有已激活的画像模板，无法展示规则口径"
        data-test="rules-no-active"
      >
        <el-button type="primary" @click="openTemplateList">去创建并激活模板</el-button>
      </el-empty>

      <el-empty
        v-else-if="!loading && activeTemplate && !dimensions.length"
        description="该模板尚未配置维度，规则未生效"
        data-test="rules-no-dimension"
      >
        <el-button type="primary" @click="openWorkbench">去工作台配置维度</el-button>
      </el-empty>

      <el-row v-else :gutter="16">
        <el-col v-for="dimension in dimensions" :key="dimension.code" :xs="24" :lg="12">
          <el-card shadow="never" class="mb-16" data-test="rules-dimension">
            <template #header>
              <div class="card-head">
                <span class="dimension-name">{{ dimension.name || dimension.code }}</span>
                <div class="card-head-right">
                  <el-tag size="small" type="info">{{ dimension.code }}</el-tag>
                  <el-tag size="small">权重 {{ dimension.weight.toFixed(2) }}</el-tag>
                </div>
              </div>
            </template>
            <div class="weight-bar">
              <el-progress :percentage="Math.min(100, Math.round(dimension.weight * 100))" :stroke-width="8" />
            </div>
            <el-table :data="dimension.rules" size="small" data-test="rules-rule-table">
              <el-table-column prop="key" label="标签键" min-width="150" show-overflow-tooltip />
              <el-table-column label="打分类型" width="140">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.legacy ? 'info' : 'primary'">{{ row.type }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="规则权重" width="100">
                <template #default="{ row }">{{ row.weight.toFixed(2) }}</template>
              </el-table-column>
              <template #empty>
                <span class="muted sm">该维度暂无规则（不参与打分）</span>
              </template>
            </el-table>
            <div class="dimension-foot">
              <span class="muted sm">{{ describeRuleTypes(dimension.rules) }}</span>
              <el-button link type="primary" size="small" @click="openWorkbench">编辑该维度</el-button>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <el-card shadow="never" header="口径说明" class="mt-8">
      <ul class="notes">
        <li>维度分 = 该维度下各标签得分按规则权重加权；总分 = 各维度分按维度权重加权。</li>
        <li>标签缺值时按 <strong>50 分</strong> 计入；`when` 条件不成立的规则会被跳过（不计权重）。</li>
        <li>未激活模板不参与计算；修改配置后需保存并激活才对新计算生效。</li>
      </ul>
    </el-card>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import NameCodeLabel from '@/components/common/NameCodeLabel.vue'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { dpsApi, type DpsPortraitTemplate } from '@/core/api/dps'
import { describeDpsError, type DpsErrorPresentation } from '@/core/api/error'

interface RuleView {
  key: string
  type: string
  weight: number
  legacy: boolean
}

interface DimensionView {
  code: string
  name: string
  weight: number
  rules: RuleView[]
}

const router = useRouter()
const templates = ref<DpsPortraitTemplate[]>([])
const selectedCode = ref('')
const activeTemplate = ref<DpsPortraitTemplate | null>(null)
const loading = ref(false)
const presentation = ref<DpsErrorPresentation | null>(null)

const dimensions = computed<DimensionView[]>(() => parseDimensions(activeTemplate.value?.dimension_config))
/** 父模板中文名称（继承标签中与 code 分开展示）。 */
const extendsName = computed(() => {
  const code = activeTemplate.value?.extends
  if (!code) return ''
  return templates.value.find((item) => item.code === code)?.name || ''
})
const weightTotal = computed(() => dimensions.value.reduce((sum, item) => sum + item.weight, 0))
const ruleCount = computed(() => dimensions.value.reduce((sum, item) => sum + item.rules.length, 0))

/** 模板配置块可能是对象或 JSON 串，统一解析为维度视图模型。 */
function parseDimensions(raw: unknown): DimensionView[] {
  const config = typeof raw === 'string' ? safeParse(raw) : raw
  const list = (config as { dimensions?: unknown } | null)?.dimensions
  if (!Array.isArray(list)) return []
  return list.map((item) => {
    const record = (item || {}) as Record<string, unknown>
    const rules = Array.isArray(record.rules) ? record.rules : []
    return {
      code: String(record.code || '-'),
      name: String(record.name || record.code || '-'),
      weight: Number(record.weight) || 0,
      rules: rules.map((rule) => {
        const row = (rule || {}) as Record<string, unknown>
        return {
          key: String(row.key || row.tag_code || '-'),
          type: String(row.type || 'legacy_map'),
          weight: Number(row.weight) || 0,
          legacy: !row.type,
        }
      }),
    }
  })
}

function safeParse(text: string): unknown {
  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

function describeRuleTypes(rules: RuleView[]): string {
  if (!rules.length) return ''
  const legacyCount = rules.filter((rule) => rule.legacy).length
  return legacyCount ? `其中 ${legacyCount} 条为历史兼容映射（legacy_map）` : '全部规则使用显式打分类型'
}

function openWorkbench() {
  if (!selectedCode.value) return
  void router.push(`/portrait/dps/templates/${selectedCode.value}/edit`)
}

function openTemplateList() {
  void router.push('/portrait/dps/templates')
}

function openAnnotationTemplates() {
  void router.push('/portrait/dps/annotation-templates')
}

async function loadActiveTemplates() {
  const result = await dpsApi.listTemplates({ status: 'active' })
  templates.value = result.items || []
  if (!templates.value.length) {
    selectedCode.value = ''
    activeTemplate.value = null
    return
  }
  const stillExists = templates.value.some((item) => item.code === selectedCode.value)
  if (!stillExists) selectedCode.value = templates.value[0].code
  await loadTemplate()
}

async function loadTemplate() {
  if (!selectedCode.value) {
    activeTemplate.value = null
    return
  }
  try {
    activeTemplate.value = await dpsApi.getTemplate(selectedCode.value)
  } catch (err) {
    activeTemplate.value = null
    presentation.value = describeDpsError(err)
  }
}

async function reload() {
  loading.value = true
  presentation.value = null
  try {
    await loadActiveTemplates()
  } catch (err) {
    presentation.value = describeDpsError(err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void reload()
})
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.mt-8 { margin-top: 8px; }
.toolbar { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.toolbar-label { font-size: 13px; color: #4b5563; }
.toolbar-actions { margin-left: auto; display: flex; gap: 8px; }
.summary { display: flex; gap: 24px; flex-wrap: wrap; margin-top: 14px; font-size: 13px; color: #374151; }
.summary .bad { color: #d97706; }
.muted { color: #9ca3af; }
.sm { font-size: 12px; }
.card-head { display: flex; justify-content: space-between; align-items: center; }
.card-head-right { display: flex; gap: 6px; }
.dimension-name { font-weight: 600; }
.weight-bar { margin-bottom: 10px; }
.dimension-foot { display: flex; justify-content: space-between; align-items: center; margin-top: 8px; }
.notes { margin: 0; padding-left: 18px; font-size: 13px; color: #4b5563; line-height: 1.9; }
.request-id { color: #6b7280; font-size: 12px; }
</style>
