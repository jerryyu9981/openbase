<template>
  <PageContainer title="画像结果" description="计算结果：按画像模板重算生成的画像快照与版本；模板配置请进入「画像模板」" test-id="portrait-list-page">
    <ConceptNav current="portrait" />
    <el-result
      v-if="isForbidden"
      icon="error"
      :title="presentation?.title || ''"
      :sub-title="presentation?.detail || ''"
      data-test="isolation-forbidden"
    >
      <template #extra>
        <p v-if="presentation?.requestId" class="request-id" data-test="error-request-id">
          请求编号：{{ presentation.requestId }}
        </p>
        <el-button data-test="isolation-back" @click="$router.push('/dashboard')">返回仪表盘</el-button>
      </template>
    </el-result>

    <div v-else-if="isNotFound" data-test="isolation-not-found">
      <el-empty description="资源不存在或已被移除" />
    </div>

    <template v-else>
      <el-row :gutter="16" class="mb-16">
        <el-col :span="8">
          <el-card shadow="hover" data-test="dps-kpi">
            <div class="kpi-label">画像总数</div>
            <div class="kpi-value">{{ overview.total_profiles ?? overview.total ?? '-' }}</div>
            <div class="kpi-sub">报表概览（真实 DPS 数据）</div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover" data-test="dps-kpi">
            <div class="kpi-label">高风险画像</div>
            <div class="kpi-value">{{ overview.high_risk_count ?? overview.risk_high ?? '-' }}</div>
            <div class="kpi-sub">风险分 ≥ 70</div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover" data-test="dps-kpi">
            <div class="kpi-label">上游健康度</div>
            <div class="kpi-value">{{ health.status || '-' }}</div>
            <div class="kpi-sub">DPS v{{ health.version || '?' }}</div>
          </el-card>
        </el-col>
      </el-row>

      <div class="page-toolbar">
        <el-input v-model="keyword" placeholder="搜索画像（姓名/ID 模糊）" clearable style="width: 240px" data-test="dps-search" @keyup.enter="loadData" />
        <el-button type="primary" data-test="dps-create" @click="$router.push('/portrait/search')">高级检索</el-button>
        <el-button data-test="portrait-calculate-open" @click="openCalculate">计算画像</el-button>
        <el-button data-test="portrait-external-open" @click="openExternal">按外部 ID 查询</el-button>
        <el-popover placement="bottom-end" :width="200" trigger="click">
          <template #reference>
            <el-button data-test="portrait-columns">列设置</el-button>
          </template>
          <el-checkbox
            v-for="column in columns"
            :key="column.key"
            :model-value="column.visible"
            data-test="portrait-column-option"
            @change="toggleColumn(column.key)"
          >
            {{ column.label }}
          </el-checkbox>
        </el-popover>
        <el-button data-test="portrait-export" @click="exportCsv">导出 CSV</el-button>
        <el-checkbox v-model="staleOnly" data-test="portrait-stale-switch" @change="onStaleFilterChange">仅看过期</el-checkbox>
        <el-button :loading="loading" data-test="portrait-refresh" @click="loadData">刷新</el-button>
        <span class="muted sm">关键字支持服务端检索（姓名/person_id/外部 ID/标签名）</span>
      </div>

      <div v-if="selectedCount > 0" class="batch-bar" data-test="portrait-batch-bar">
        <span>已选 {{ selectedCount }} 条</span>
        <el-button size="small" type="primary" plain :loading="batchCalculating" data-test="portrait-batch-calc" @click="batchCalculate">
          批量计算
        </el-button>
        <el-button size="small" type="danger" plain :loading="batchDeleting" data-test="portrait-batch-delete" @click="batchDelete">
          批量删除
        </el-button>
        <el-button size="small" link data-test="portrait-batch-clear" @click="clearSelection">清空选择</el-button>
      </div>

      <el-alert
        v-if="showErrorBar"
        :title="errorMessage"
        type="error"
        show-icon
        closable
        class="mb-16"
        data-test="isolation-error-bar"
        @close="presentation = null"
      >
        <template #default>
          <el-button link type="primary" size="small" data-test="isolation-retry" @click="loadData">点击重试</el-button>
        </template>
      </el-alert>
      <div class="ob-table-scroll">
        <el-table
          ref="tableRef"
          v-loading="loading"
          :data="filtered"
          :row-key="rowKey"
          stripe
          data-test="portrait-table"
          @selection-change="onSelectionChange"
        >
          <el-table-column type="selection" width="44" reserve-selection />
          <el-table-column v-if="columnVisible('name')" prop="name" label="画像名称" min-width="160" />
          <el-table-column v-if="columnVisible('person_id')" prop="person_id" label="画像码（person_id）" min-width="180" show-overflow-tooltip />
          <el-table-column v-if="columnVisible('tags')" label="标签" min-width="180">
            <template #default="{ row }">
              <el-tag v-for="(tag, index) in (row.tags || [])" :key="`${index}-${tagLabel(tag)}`" size="small" class="tag-item" type="info">{{ tagLabel(tag) }}</el-tag>
              <span v-if="!(row.tags || []).length" class="text-muted">-</span>
            </template>
          </el-table-column>
          <el-table-column v-if="columnVisible('stale')" label="口径状态" width="120">
            <template #default="{ row }">
              <el-tag
                v-if="row.stale"
                type="warning"
                size="small"
                :title="staleReasonLabel(row.stale_reason)"
                data-test="portrait-stale-tag"
              >口径已过期</el-tag>
              <span v-else class="text-muted">一致</span>
            </template>
          </el-table-column>
          <el-table-column v-if="columnVisible('risk')" label="风险等级" width="110">
            <template #default="{ row }">
              <el-tag :type="riskType(row)" size="small">{{ riskLabel(row) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column v-if="columnVisible('updated_at')" prop="updated_at" label="更新时间" width="170">
            <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="$router.push(`/portrait/${row.person_id || row.id}`)">详情</el-button>
              <el-button link type="danger" data-test="portrait-delete" @click="removePortrait(row)">删除</el-button>
            </template>
          </el-table-column>
          <template #empty>
            <el-empty
              data-test="isolation-empty"
              :description="emptyDescription"
              :image-size="60"
            />
          </template>
        </el-table>
      </div>
      <div class="pager">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          background
          @current-change="loadData"
        />
      </div>

      <el-dialog v-model="calculateVisible" title="计算画像" width="460px" data-test="portrait-calculate-dialog">
        <el-form label-width="110px">
          <el-form-item label="画像主体 ID" required>
            <el-input v-model="calcForm.personId" placeholder="person_id" data-test="calc-person-id" />
          </el-form-item>
          <el-form-item label="画像模板">
            <el-select
              v-model="calcForm.templateCode"
              clearable
              placeholder="留空使用默认模板"
              style="width: 100%"
              data-test="calc-template-code"
            >
              <el-option
                v-for="item in templateOptions"
                :key="item.code"
                :label="item.name || item.code"
                :value="item.code"
              >
                <NameCodeLabel :name="item.name" :code="item.code" />
              </el-option>
            </el-select>
            <div class="form-hint">仅展示已激活模板；未激活模板不会参与计算。</div>
          </el-form-item>
        </el-form>
        <el-alert v-if="calcError" type="error" show-icon :closable="false" class="mt-8" data-test="calc-error">
          <template #title>{{ calcError }}</template>
          <el-button v-if="calcErrorNeedsActivation" link type="primary" size="small" @click="goActivateTemplate">
            去模板族管理激活
          </el-button>
        </el-alert>
        <template #footer>
          <el-button @click="calculateVisible = false">取消</el-button>
          <el-button type="primary" :loading="calculating" data-test="calc-submit" @click="submitCalculate">开始计算</el-button>
        </template>
      </el-dialog>

      <el-dialog v-model="externalVisible" title="按外部 ID 查询画像" width="460px" data-test="portrait-external-dialog">
        <el-form label-width="110px">
          <el-form-item label="外部身份标识" required>
            <el-input v-model="externalId" placeholder="external_id" data-test="external-id" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="externalVisible = false">取消</el-button>
          <el-button type="primary" :loading="externalLoading" data-test="external-submit" @click="submitExternalQuery">查询</el-button>
        </template>
      </el-dialog>
    </template>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import ConceptNav from '../components/ConceptNav.vue'
import NameCodeLabel from '@/components/common/NameCodeLabel.vue'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { dpsApi, type DpsPortrait, type DpsPortraitTemplate } from '@/core/api/dps'
import { describeDpsError, describeError, type ErrorPresentation } from '@/core/api/error'
import { useDpsListView } from '@/modules/portrait/composables/useDpsListView'
import {
  PORTRAIT_COLUMNS,
  buildPortraitCsv,
  filterPortraitRows,
  formatDateTime,
  riskLabelOf,
  tagLabelOf,
} from '@/modules/portrait/portrait/portraitTools'

const router = useRouter()
const portraits = ref<DpsPortrait[]>([])
const overview = ref<Record<string, unknown>>({})
const health = ref<{ status?: string; version?: string }>({})
const keyword = ref('')
const page = ref(1)
const pageSize = 20
const total = ref(0)
const loading = ref(false)
const presentation = ref<ErrorPresentation | null>(null)
const tableRef = ref<{ clearSelection?: () => void } | null>(null)
const selectedRows = ref<DpsPortrait[]>([])
const batchCalculating = ref(false)
const batchDeleting = ref(false)

const { columns, columnVisible, toggleColumn, setSelection, clearSelection } = useDpsListView({
  pageKey: 'portraits',
  columns: [
    ...PORTRAIT_COLUMNS.filter((column) => ['name', 'person_id', 'tags'].includes(column.key)).map(
      (column) => ({ key: column.key, label: column.label }),
    ),
    { key: 'stale', label: '口径状态' },
    ...PORTRAIT_COLUMNS.filter((column) => ['risk', 'updated_at'].includes(column.key)).map(
      (column) => ({ key: column.key, label: column.label }),
    ),
  ],
})

/** T-DM-02：stale 过滤需绑定模板口径，默认使用六维默认模板 */
const DEFAULT_PORTRAIT_TEMPLATE_CODE = 'dps-correction-v1'
const staleOnly = ref(false)

function staleReasonLabel(reason?: string | null): string {
  switch (reason) {
    case 'template_missing':
      return '画像模板已不存在，请重新选择口径并重算'
    case 'version_unknown':
      return '历史画像缺少模板版本记录，建议重算'
    case 'version_mismatch':
      return '画像模板已升级，当前画像基于旧版本口径'
    case 'result_missing':
      return '该画像尚无此模板的计算结果'
    default:
      return '画像口径已过期，建议重算'
  }
}

function onStaleFilterChange() {
  page.value = 1
  void loadData()
}

/** 计算画像对话框（批次 5：POST /portraits/calculate，默认异步任务） */
const calculateVisible = ref(false)
const calculating = ref(false)
const calcForm = ref({ personId: '', templateCode: '' })
const templateOptions = ref<DpsPortraitTemplate[]>([])
const calcError = ref('')
const calcErrorNeedsActivation = computed(() => calcError.value.includes('未激活'))
/** 按外部 ID 查询对话框（批次 5：GET /portraits/by-external/{id}） */
const externalVisible = ref(false)
const externalLoading = ref(false)
const externalId = ref('')

const isForbidden = computed(() => presentation.value?.pageLevel === true)
const isNotFound = computed(() => presentation.value?.kind === 'not-found')
const showErrorBar = computed(
  () => !!presentation.value && !presentation.value.pageLevel && presentation.value.kind !== 'not-found',
)
const errorMessage = computed(() =>
  showErrorBar.value ? `画像列表加载失败：${presentation.value?.detail || '网络错误'}` : '',
)
const emptyDescription = computed(() => {
  if (showErrorBar.value) return '加载失败，请点击上方提示条「点击重试」'
  return '当前租户暂无数据（如为权限问题请联系管理员）'
})
const selectedCount = computed(() => selectedRows.value.length)
const filtered = computed(() => filterPortraitRows(portraits.value, keyword.value))

function rowKey(row: DpsPortrait): string {
  return String(row.person_id || row.id || '')
}

function riskLabel(row: DpsPortrait): string {
  return riskLabelOf(row)
}

function riskType(row: DpsPortrait): 'success' | 'warning' | 'danger' | 'info' {
  const value = Number(row.risk_level ?? row.risk_score)
  if (!Number.isFinite(value)) return 'info'
  if (value >= 70) return 'danger'
  if (value >= 40) return 'warning'
  return 'success'
}

function formatTime(value?: string) {
  return formatDateTime(value)
}

function tagLabel(raw: Record<string, unknown> | string): string {
  return tagLabelOf(raw)
}

function onSelectionChange(rows: DpsPortrait[]) {
  selectedRows.value = rows
  setSelection(rows.map((row) => rowKey(row)).filter(Boolean))
}

function clearTableSelection() {
  selectedRows.value = []
  clearSelection()
  tableRef.value?.clearSelection?.()
}

function downloadText(content: string, filename: string, mime: string) {
  const blob = new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

async function exportCsv() {
  try {
    const result = await dpsApi.exportPortraitsCsv({ keyword: keyword.value || undefined })
    const url = URL.createObjectURL(result.blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = result.filename
    anchor.click()
    URL.revokeObjectURL(url)
    ElMessage.success(
      `已导出画像 CSV${result.truncated ? '（超过 10000 行，已截断）' : ''}`,
    )
    return
  } catch {
    // 服务端导出不可用（DPS 未升级/网络异常）→ 回退既有本地导出
  }
  if (!filtered.value.length) {
    ElMessage.warning('当前没有可导出的画像')
    return
  }
  const stamp = new Date().toISOString().slice(0, 10)
  downloadText(`\ufeff${buildPortraitCsv(filtered.value)}`, `portraits-${stamp}.csv`, 'text/csv;charset=utf-8')
  ElMessage.warning(`服务端导出不可用，已回退本地导出 ${filtered.value.length} 条画像`)
}

async function loadHealth() {
  try {
    health.value = await dpsApi.getDpsHealth()
  } catch {
    health.value = { status: '不可达' }
  }
}

async function loadOverview() {
  try {
    overview.value = await dpsApi.getReportsOverview()
  } catch {
    overview.value = {}
  }
}

function openCalculate() {
  calcForm.value = { personId: '', templateCode: '' }
  calcError.value = ''
  void loadTemplateOptions()
  calculateVisible.value = true
}

/** 仅加载已激活模板：未激活模板无法参与计算。 */
async function loadTemplateOptions() {
  try {
    const result = await dpsApi.listTemplates({ status: 'active' })
    templateOptions.value = result.items || []
    if (templateOptions.value.length === 1) {
      calcForm.value.templateCode = templateOptions.value[0].code
    }
  } catch {
    templateOptions.value = []
  }
}

function goActivateTemplate() {
  calculateVisible.value = false
  void router.push('/portrait/dps/templates')
}

/** 发起画像计算：返回 task_id 时轮询至终态，同步返回时直接刷新列表 */
async function submitCalculate() {
  const personId = calcForm.value.personId.trim()
  if (!personId) {
    ElMessage.warning('请输入画像主体 ID')
    return
  }
  calculating.value = true
  calcError.value = ''
  try {
    const payload: Record<string, unknown> = { person_id: personId }
    const templateCode = calcForm.value.templateCode.trim()
    if (templateCode) payload.template_code = templateCode
    const result = await dpsApi.calculatePortrait(payload)
    const taskId = String(result.task_id || '')
    if (taskId) {
      ElMessage.info('计算任务已提交，正在等待结果…')
      await dpsApi.waitPortraitTask(taskId)
    }
    ElMessage.success('画像计算完成')
    calculateVisible.value = false
    await loadData()
  } catch (err) {
    const described = describeDpsError(err)
    calcError.value = described.detail || described.title
    ElMessage.error(calcError.value)
  } finally {
    calculating.value = false
  }
}

/** 批量计算：逐条提交（异步任务逐个等待），逐条汇总成功/失败 */
async function batchCalculate() {
  const targets = selectedRows.value.map((row) => String(row.person_id || row.id || '')).filter(Boolean)
  if (!targets.length) {
    ElMessage.warning('请先勾选画像')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确认对已选 ${targets.length} 条画像按默认口径重新计算？异步任务将逐条提交，耗时取决于上游。`,
      '批量计算确认',
      { type: 'warning', confirmButtonText: '确认计算' },
    )
  } catch {
    return
  }
  batchCalculating.value = true
  let succeeded = 0
  const failures: string[] = []
  for (const personId of targets) {
    try {
      const result = await dpsApi.calculatePortrait({ person_id: personId })
      const taskId = String(result.task_id || '')
      if (taskId) await dpsApi.waitPortraitTask(taskId)
      succeeded += 1
    } catch (err) {
      const described = describeDpsError(err)
      failures.push(`${personId}：${described.detail || described.title}`)
    }
  }
  batchCalculating.value = false
  ElMessage.success(`批量计算完成：成功 ${succeeded} 条${failures.length ? `，失败 ${failures.length} 条` : ''}`)
  if (failures.length) ElMessage.warning(failures.slice(0, 3).join('；'))
  clearTableSelection()
  await loadData()
}

/** 批量删除：二次确认 → 逐条 DELETE（上游软删除）→ 汇总 → 刷新 */
async function batchDelete() {
  const targets = selectedRows.value.map((row) => String(row.person_id || row.id || '')).filter(Boolean)
  if (!targets.length) {
    ElMessage.warning('请先勾选画像')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确认删除已选 ${targets.length} 条画像？删除后将不再出现在列表与检索中（保留历史审计）。`,
      '批量删除确认',
      { type: 'warning', confirmButtonText: '确认删除' },
    )
  } catch {
    return
  }
  batchDeleting.value = true
  let succeeded = 0
  let failed = 0
  for (const personId of targets) {
    try {
      await dpsApi.deletePortrait(personId)
      succeeded += 1
    } catch {
      failed += 1
    }
  }
  batchDeleting.value = false
  ElMessage.success(`批量删除完成：成功 ${succeeded} 条${failed ? `，失败 ${failed} 条` : ''}`)
  clearTableSelection()
  await loadData()
}

function openExternal() {
  externalId.value = ''
  externalVisible.value = true
}

/** 按外部身份标识定位画像：命中后跳转详情，404 提示未找到 */
async function submitExternalQuery() {
  const external = externalId.value.trim()
  if (!external) {
    ElMessage.warning('请输入外部身份标识')
    return
  }
  externalLoading.value = true
  try {
    const portrait = await dpsApi.getPortraitByExternal(external)
    const personId = String(portrait.person_id || portrait.id || '')
    if (!personId) {
      ElMessage.warning('已命中画像，但响应缺少 person_id')
      return
    }
    externalVisible.value = false
    await router.push(`/portrait/${encodeURIComponent(personId)}`)
  } catch (err) {
    const status = (err as { response?: { status?: number } })?.response?.status
    ElMessage.error(status === 404 ? '未找到该外部标识对应的画像' : '查询失败，请稍后重试')
  } finally {
    externalLoading.value = false
  }
}

/** 删除画像：二次确认 → DELETE（上游软删除）→ 刷新列表 */
async function removePortrait(row: DpsPortrait) {
  const personId = String(row.person_id || row.id || '')
  if (!personId) return
  try {
    await ElMessageBox.confirm(
      `确认删除画像「${row.name || personId}」？删除后将不再出现在列表与检索中（保留历史审计）。`,
      '删除确认',
      { type: 'warning' },
    )
  } catch {
    return
  }
  try {
    await dpsApi.deletePortrait(personId)
    ElMessage.success('画像已删除')
    await loadData()
  } catch (err) {
    const status = (err as { response?: { status?: number } })?.response?.status
    ElMessage.error(status === 404 ? '画像不存在或已被删除' : '删除失败，请稍后重试')
  }
}

async function loadData() {
  loading.value = true
  presentation.value = null
  try {
    const result = await dpsApi.listPortraits({
      page: page.value,
      page_size: pageSize,
      keyword: keyword.value.trim() || undefined,
      template_code: staleOnly.value ? DEFAULT_PORTRAIT_TEMPLATE_CODE : undefined,
      stale: staleOnly.value ? true : undefined,
    })
    portraits.value = result.items || []
    total.value = result.total ?? 0
  } catch (err) {
    portraits.value = []
    total.value = 0
    presentation.value = describeError(err)
  } finally {
    loading.value = false
  }
  void loadHealth()
  void loadOverview()
}

onMounted(() => {
  void loadData()
})
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.kpi-label { font-size: 13px; color: #6b7280; }
.kpi-value { font-size: 24px; font-weight: 600; margin: 4px 0; }
.kpi-sub { font-size: 12px; color: #9ca3af; }
.tag-item { margin-right: 4px; }
.text-muted { color: #9ca3af; }
.muted { color: var(--ob-text-secondary); }
.sm { font-size: 12px; }
.pager { display: flex; justify-content: flex-end; margin-top: 12px; }
.request-id { color: #6b7280; font-size: 12px; margin-bottom: 8px; }
.form-hint { font-size: 12px; color: #9ca3af; line-height: 1.6; }
.mt-8 { margin-top: 8px; }
.batch-bar { display: flex; align-items: center; gap: 10px; padding: 8px 12px; margin-bottom: 12px; border: 1px solid var(--ob-border); border-radius: var(--ob-radius-md); background: var(--el-fill-color-light); }
</style>
