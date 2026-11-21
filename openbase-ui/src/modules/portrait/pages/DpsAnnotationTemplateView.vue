<template>
  <PageContainer title="标注模板" description="采集契约：定义字段与标签产出，必须归属一个画像模板" test-id="dps-annotation-template-view-page">
    <ConceptNav current="annotation-template" />
    <div class="page-toolbar">
      <el-input v-model="keyword" placeholder="搜索 code / 名称 / scenario" clearable style="width: 240px" data-test="annotation-template-filter" />
      <el-select v-model="scenarioFilter" placeholder="scenario：全部" clearable style="width: 170px" data-test="annotation-scenario-filter">
        <el-option v-for="item in SCENARIOS" :key="item" :label="item" :value="item" />
      </el-select>
      <el-button type="primary" data-test="annotation-query" @click="load">查询</el-button>
      <span class="result-count" data-test="annotation-count">共 {{ filteredItems.length }} 条</span>
      <el-button data-test="annotation-reset" @click="resetFilters">重置</el-button>
      <el-button type="primary" plain data-test="annotation-new" @click="openCreate">新建标注模板</el-button>
    </div>

    <!-- 删除被拒（409 且显示关联条数） -->
    <el-alert v-if="deleteRejected" type="error" show-icon :closable="true" class="mb-16" data-test="annotation-delete-rejected" @close="deleteRejected = ''">
      <template #title>删除被拒（409）</template>
      <div>{{ deleteRejected }}</div>
    </el-alert>

    <el-alert v-if="error" type="error" show-icon :closable="false" class="mb-16" data-test="dps-error">
      <template #title>{{ error.title }}</template>
      <div>{{ error.detail }}</div>
      <div v-if="error.hint" class="hint" data-test="dps-error-hint">{{ error.hint }}</div>
      <el-button v-if="error.retryable" link type="primary" size="small" data-test="dps-retry" @click="load">点击重试</el-button>
      <span v-if="error.requestId" class="request-id" data-test="dps-request-id">请求编号：{{ error.requestId }}</span>
    </el-alert>

    <el-card header="标注模板">
      <div class="ob-table-scroll">
        <el-table v-loading="loading" :data="filteredItems" stripe :empty-text="keyword ? '无匹配标注模板' : '暂无标注模板'" data-test="annotation-table">
          <el-table-column label="标注模板" min-width="220">
            <template #default="{ row }">
              <NameCodeLabel :name="row.name" :code="row.code" layout="stack" />
            </template>
          </el-table-column>
          <el-table-column label="归属画像模板" min-width="200">
            <template #default="{ row }">
              <el-button link type="primary" size="small" data-test="annotation-owner" @click="router.push(`/portrait/dps/templates/${row.template_code}/edit`)">
                <NameCodeLabel :name="templateNames[row.template_code || '']" :code="row.template_code" />
              </el-button>
            </template>
          </el-table-column>
          <el-table-column prop="scenario" label="scenario" width="110" />
          <el-table-column label="字段数" width="80">
            <template #default="{ row }">{{ (row.field_schema || []).length }}</template>
          </el-table-column>
          <el-table-column label="已映射维度" width="110" data-test="annotation-mapped-dimensions">
            <template #default="{ row }">{{ mappedDimensionCount(row) }}</template>
          </el-table-column>
          <el-table-column label="归属状态" width="100">
            <template #default="{ row }">
              <el-tag size="small" :type="ownerStatusType(row.template_code)" data-test="annotation-owner-status">
                {{ ownerStatusMap[String(row.template_code || '')] || '未加载' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="被使用次数" width="110">
            <template #default="{ row }">
              <span data-test="annotation-usage">{{ usageMap[row.code] ?? '—' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="版本" width="80">
            <template #default="{ row }">{{ formatVersion(row.version) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="250" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" data-test="annotation-detail" @click="openDetail(row.code)">详情</el-button>
              <el-button link type="primary" size="small" data-test="annotation-fields" @click="router.push(`/portrait/dps/annotation-templates/${row.code}/fields`)">字段设计</el-button>
              <el-popconfirm title="确认删除该标注模板？" @confirm="remove(row.code)">
                <template #reference>
                  <el-button link type="danger" size="small" data-test="annotation-delete">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
          <template #empty>
            <el-empty description="暂无标注模板" :image-size="60" data-test="annotation-empty">
              <el-button type="primary" size="small" @click="openCreate">新建标注模板</el-button>
            </el-empty>
          </template>
        </el-table>
      </div>
    </el-card>

    <el-card header="标注范围预检（v2.12.0）" class="mb-16" data-test="annotation-scope-card">
      <div class="page-toolbar">
        <el-radio-group v-model="scopeType" data-test="annotation-scope-type" @change="resetScope">
          <el-radio-button value="template">单模板</el-radio-button>
          <el-radio-button value="category">模板类</el-radio-button>
        </el-radio-group>
        <el-select
          v-model="scopeCode"
          filterable
          placeholder="选择模板或分类"
          style="width: 300px"
          data-test="annotation-scope-code"
        >
          <el-option v-for="item in scopeOptions" :key="item.code" :label="item.name || item.code" :value="item.code">
            <NameCodeLabel :name="item.name" :code="item.code" />
          </el-option>
        </el-select>
        <el-checkbox v-if="scopeType === 'category'" v-model="scopeOnlyMounted" data-test="annotation-scope-mounted">
          仅已挂载子模板
        </el-checkbox>
        <el-button type="primary" :loading="scopeLoading" :disabled="!scopeCode" data-test="annotation-scope-resolve" @click="resolveScope">
          预检
        </el-button>
      </div>
      <el-alert
        v-if="scopeResult"
        :type="scopeResult.requires_confirmation ? 'warning' : 'success'"
        show-icon
        :closable="false"
        data-test="annotation-scope-result"
      >
        <template #title>
          命中模板 {{ scopeResult.template_count }} 个 / 标注模板 {{ scopeResult.annotation_template_count }} 个 / 字段 {{ scopeResult.field_count }} 个
        </template>
        <div v-if="scopeResult.requires_confirmation" class="mt-8">
          超出预检阈值（模板 50 / 字段 500），执行前需二次确认；建议缩小到单模板或第 3 层分类。
        </div>
        <div class="muted sm mt-8">命中：{{ scopeResult.templates.map((item) => item.name || item.code).join('、') || '无' }}</div>
      </el-alert>
      <p class="muted sm mt-8">单模板 = 当前模板；模板类 = 该分类及全部子分类下的模板，可只保留已被挂载的子模板。</p>
    </el-card>
    <el-drawer v-model="detailOpen" title="标注模板详情" size="480px" data-test="annotation-detail-drawer">
      <el-descriptions :column="1" border size="small">
        <el-descriptions-item label="模板名称">{{ detail?.name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="标注模板码">{{ detail?.code || '-' }}</el-descriptions-item>
        <el-descriptions-item label="归属（强归属）">
          <NameCodeLabel :name="templateNames[detail?.template_code || '']" :code="detail?.template_code" />
          <span class="muted sm">（不可置空；改挂见「字段与归属」）</span>
        </el-descriptions-item>
        <el-descriptions-item label="scenario">{{ detail?.scenario || '-' }}</el-descriptions-item>
        <el-descriptions-item label="version">{{ formatVersion(detail?.version) }}</el-descriptions-item>
        <el-descriptions-item label="status">{{ detail?.status || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-drawer>

    <!-- 新建 -->
    <el-dialog v-model="createOpen" title="新建标注模板" width="560px" data-test="annotation-create-dialog">
      <el-form label-width="130px">
        <el-form-item label="code *">
          <el-input v-model="createForm.code" data-test="annotation-create-code" />
        </el-form-item>
        <el-form-item label="name">
          <el-input v-model="createForm.name" data-test="annotation-create-name" />
        </el-form-item>
        <el-form-item label="归属画像模板 *">
          <el-select v-model="createForm.template_code" placeholder="仅可选 active 画像模板" style="width: 260px" data-test="annotation-create-owner">
            <el-option
              v-for="item in activeTemplates"
              :key="item.code"
              :label="item.name || item.code"
              :value="item.code"
            >
              <NameCodeLabel :name="item.name" :code="item.code" />
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="scenario">
          <el-select v-model="createForm.scenario" style="width: 200px" data-test="annotation-create-scenario">
            <el-option v-for="item in SCENARIOS" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="description">
          <el-input v-model="createForm.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" data-test="annotation-create-save" @click="create">保存</el-button>
      </template>
    </el-dialog>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import ConceptNav from '../components/ConceptNav.vue'
import NameCodeLabel from '@/components/common/NameCodeLabel.vue'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { dpsApi, type DpsAnnotationScopeResult, type DpsAnnotationTemplate, type DpsPortraitTemplate, type DpsTemplateCategory } from '@/core/api/dps'
import { describeDpsError } from '@/core/api/error'
import { useAsyncState } from '@/core/composables/useAsyncState'
import { formatVersion } from '@/modules/portrait/version'

const SCENARIOS = ['intake', 'assess', 'check', 'general']

const router = useRouter()
const keyword = ref('')
const scenarioFilter = ref('')
const detailOpen = ref(false)
const detail = ref<DpsAnnotationTemplate | null>(null)
const createOpen = ref(false)
const saving = ref(false)
const deleteRejected = ref('')
const activeTemplates = ref<DpsPortraitTemplate[]>([])
/** 画像模板 code → 中文名称（归属列主显名称）。 */
const templateNames = ref<Record<string, string>>({})
/** 归属模板状态（列表「归属状态」列）。 */
const ownerStatusMap = ref<Record<string, string>>({})
/** 标注模板被使用次数（标注记录数；读取失败显示 —）。 */
const usageMap = ref<Record<string, number | null>>({})
const createForm = reactive({ code: '', name: '', template_code: '', scenario: 'general', description: '' })

// ── v2.12.0 标注范围预检（单模板 / 模板类）─────────────────
const scopeType = ref<'template' | 'category'>('category')
const scopeCode = ref('')
const scopeOnlyMounted = ref(false)
const scopeLoading = ref(false)
const scopeResult = ref<DpsAnnotationScopeResult | null>(null)
const scopeTemplates = ref<DpsPortraitTemplate[]>([])
const scopeCategories = ref<DpsTemplateCategory[]>([])

const scopeOptions = computed(() => (
  scopeType.value === 'template'
    ? scopeTemplates.value.map((item) => ({ code: item.code, name: item.name }))
    : scopeCategories.value.map((item) => ({ code: item.code, name: item.name }))
))

const { data, loading, error, run } = useAsyncState<{ items: DpsAnnotationTemplate[]; total?: number }>()
const items = computed(() => data.value?.items || [])
// 关键词在已加载列表内本地过滤（code / 名称 / scenario），支持中文与前缀；
// 服务端 template_code 为精确等值匹配，无法满足检索诉求。
const filteredItems = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return items.value
  return items.value.filter((item) =>
    [item.code, item.name, item.template_code, item.scenario]
      .filter(Boolean)
      .some((field) => String(field).toLowerCase().includes(kw)),
  )
})

async function load() {
  await Promise.all([
    run(() =>
      dpsApi.listAnnotationTemplates({
        scenario: scenarioFilter.value || undefined,
      }),
    ),
    loadTemplateNames(),
    loadScopeCategories(),
  ])
  await loadUsage()
}

/** 已映射目标维度的去重数量（P-06 列表列）。 */
function mappedDimensionCount(row: DpsAnnotationTemplate): number {
  const dimensions = new Set(
    (row.field_schema || []).map((field) => String(field.target_dimension || '').trim()).filter(Boolean),
  )
  return dimensions.size
}

function ownerStatusType(code?: string): 'success' | 'info' | 'warning' {
  const status = ownerStatusMap.value[String(code || '')]
  if (status === 'active') return 'success'
  if (status === 'inactive') return 'info'
  return 'warning'
}

/** 逐模板读取标注记录数（小批量并发，失败显示 —，不阻断列表）。 */
async function loadUsage() {
  const targets = items.value.slice(0, 30)
  for (let index = 0; index < targets.length; index += 5) {
    await Promise.all(
      targets.slice(index, index + 5).map(async (item) => {
        const total = await dpsApi
          .listAnnotations({ annotation_template: item.code, page_size: 1 })
          .then((result) => result.total)
          .catch(() => null)
        usageMap.value = { ...usageMap.value, [item.code]: total }
      }),
    )
  }
}

/** 加载模板分类（模板类范围预检的可选项）。 */
async function loadScopeCategories() {
  scopeCategories.value = await dpsApi.listTemplateCategories().catch(() => [])
}

function resetScope() {
  scopeCode.value = ''
  scopeResult.value = null
}

async function resolveScope() {
  if (!scopeCode.value) return
  scopeLoading.value = true
  try {
    scopeResult.value = await dpsApi.resolveAnnotationScope({
      type: scopeType.value,
      code: scopeCode.value,
      only_mounted: scopeType.value === 'category' ? scopeOnlyMounted.value : undefined,
    })
  } catch (caught) {
    scopeResult.value = null
    ElMessage.error(describeDpsError(caught).title)
  } finally {
    scopeLoading.value = false
  }
}

/** 加载全部画像模板名称映射（不按状态过滤，保证历史归属也能显示名称）。 */
async function loadTemplateNames() {
  const result = await dpsApi.listTemplates().catch(() => ({ items: [] as DpsPortraitTemplate[] }))
  scopeTemplates.value = result.items || []
  const map: Record<string, string> = {}
  const statusMap: Record<string, string> = {}
  for (const item of result.items || []) {
    if (item.code && item.name) map[item.code] = item.name
    if (item.code) statusMap[item.code] = String(item.status || 'draft')
  }
  templateNames.value = map
  ownerStatusMap.value = statusMap
}

function resetFilters() {
  keyword.value = ''
  scenarioFilter.value = ''
  void load()
}

async function openDetail(code: string) {
  detailOpen.value = true
  detail.value = null
  try {
    detail.value = await dpsApi.getAnnotationTemplate(code)
  } catch (caught) {
    error.value = describeDpsError(caught)
  }
}

async function openCreate() {
  createOpen.value = true
  deleteRejected.value = ''
  const result = await dpsApi.listTemplates({ status: 'active' }).catch(() => ({ items: [] as DpsPortraitTemplate[] }))
  activeTemplates.value = result.items || []
}

async function create() {
  if (!createForm.code || !createForm.template_code) {
    ElMessage.warning('code 与归属画像模板必填')
    return
  }
  saving.value = true
  try {
    const created = await dpsApi.createAnnotationTemplate({
      code: createForm.code,
      name: createForm.name,
      template_code: createForm.template_code,
      scenario: createForm.scenario,
      description: createForm.description,
    })
    ElMessage.success('标注模板已创建，进入字段设计')
    createOpen.value = false
    await router.push(`/portrait/dps/annotation-templates/${created.code}/fields`)
  } catch (caught) {
    const presentation = describeDpsError(caught)
    createOpen.value = false
    deleteRejected.value = presentation.kind === 'conflict' ? `code 已存在：${presentation.detail}` : ''
    if (!deleteRejected.value) ElMessage.error(presentation.hint || presentation.title)
  } finally {
    saving.value = false
  }
}

async function remove(code: string) {
  deleteRejected.value = ''
  try {
    await dpsApi.deleteAnnotationTemplate(code)
    ElMessage.success('标注模板已删除')
    await load()
  } catch (caught) {
    const presentation = describeDpsError(caught)
    if (presentation.kind === 'conflict') {
      deleteRejected.value = presentation.detail || '存在关联标注数据，禁止删除'
    } else {
      ElMessage.error(presentation.hint || presentation.title)
    }
  }
}

onMounted(() => {
  void load()
})
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.result-count { color: var(--ob-text-secondary); font-size: 13px; margin-left: 4px; }
.hint { color: var(--ob-text-secondary); font-size: 12px; margin-top: 4px; }
.request-id { color: var(--ob-text-disabled); font-size: 12px; margin-left: 8px; }
</style>
