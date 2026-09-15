<template>
  <div class="logs-page">
    <!-- 数据源切换（四仓统一检索；切源即重置分页与 facets） -->
    <div class="page-toolbar logs-toolbar">
      <el-radio-group v-model="source" size="default" data-test="logs-source" @change="onChangeSource">
        <el-radio-button v-for="s in LOG_SOURCE_OPTIONS" :key="s" :value="s" data-test="logs-source-option">
          {{ LOG_SOURCE_LABELS[s] }}
        </el-radio-button>
      </el-radio-group>
      <span class="mode-hint">统一检索：L1 文件 / 审计库 / 测试记录 / 四仓日志</span>
    </div>

    <!-- 筛选条件栏 -->
    <el-card class="mt-8 logs-filter" data-test="logs-filter-card">
      <el-form :inline="true" class="logs-filter-form">
        <el-form-item label="关键字">
          <el-input
            v-model="filters.q"
            placeholder="搜索 request_id / path / 摘要…"
            clearable
            style="width: 240px"
            data-test="logs-q"
            @keyup.enter="applyFilters"
            @clear="applyFilters"
          />
        </el-form-item>
        <el-form-item label="模块">
          <el-select
            v-model="filters.module"
            multiple
            collapse-tags
            placeholder="全部模块"
            style="width: 190px"
            data-test="logs-module"
          >
            <el-option v-for="m in MODULE_OPTIONS" :key="m" :label="MODULE_LABELS[m]" :value="m" />
          </el-select>
        </el-form-item>
        <el-form-item label="操作">
          <el-select
            v-model="filters.operation"
            multiple
            collapse-tags
            placeholder="全部操作"
            style="width: 170px"
            data-test="logs-operation"
          >
            <el-option v-for="o in OPERATION_OPTIONS" :key="o" :label="OPERATION_LABELS[o]" :value="o" />
          </el-select>
        </el-form-item>
        <el-form-item label="结果">
          <el-select
            v-model="filters.result"
            multiple
            collapse-tags
            placeholder="全部结果"
            style="width: 150px"
            data-test="logs-result"
          >
            <el-option v-for="r in RESULT_OPTIONS" :key="r" :label="RESULT_LABELS[r]" :value="r" />
          </el-select>
        </el-form-item>
        <el-form-item label="时间">
          <el-date-picker
            v-model="timeRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            value-format="YYYY-MM-DDTHH:mm:ss.sssZ"
            style="width: 340px"
            data-test="logs-time"
            @change="applyFilters"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" data-test="logs-search" @click="applyFilters">检索</el-button>
          <el-button data-test="logs-reset" @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 高级筛选（case_id/run_id/step_id） -->
      <el-collapse v-model="advancedOpen">
        <el-collapse-item name="advanced" title="高级筛选（case_id / run_id / step_id）">
          <el-form :inline="true">
            <el-form-item label="用例编号">
              <el-input v-model="filters.case_id" placeholder="case_id" clearable style="width: 200px" data-test="logs-case" @keyup.enter="applyFilters" @clear="applyFilters" />
            </el-form-item>
            <el-form-item label="轮次">
              <el-input v-model="filters.run_id" placeholder="run_id" clearable style="width: 200px" data-test="logs-run" @keyup.enter="applyFilters" @clear="applyFilters" />
            </el-form-item>
            <el-form-item label="步骤">
              <el-input v-model.number="filters.step_id" placeholder="step_id" clearable style="width: 140px" data-test="logs-step" @keyup.enter="applyFilters" @clear="applyFilters" />
            </el-form-item>
          </el-form>
        </el-collapse-item>
      </el-collapse>
    </el-card>

    <!-- Facets 维度提示（点击标签作为过滤提示） -->
    <el-card v-if="Object.keys(facets.module).length" class="mt-8 logs-facets" data-test="logs-facets">
      <div class="facets-row">
        <span class="facets-label">模块</span>
        <el-tag v-for="(count, key) in facets.module" :key="key" class="facet-tag" size="small" @click="toggleFacet('module', key)">
          {{ MODULE_LABELS[key as LogModule] ?? key }} ×{{ count }}
        </el-tag>
      </div>
      <div class="facets-row">
        <span class="facets-label">操作</span>
        <el-tag v-for="(count, key) in facets.operation" :key="key" class="facet-tag" size="small" type="info" @click="toggleFacet('operation', key)">
          {{ OPERATION_LABELS[key as LogOperation] ?? key }} ×{{ count }}
        </el-tag>
      </div>
      <div class="facets-row">
        <span class="facets-label">结果</span>
        <el-tag v-for="(count, key) in facets.result" :key="key" class="facet-tag" size="small" :type="resultTag(key as LogResult)" @click="toggleFacet('result', key)">
          {{ RESULT_LABELS[key as LogResult] ?? key }} ×{{ count }}
        </el-tag>
      </div>
    </el-card>

    <!-- 错误状态 -->
    <el-alert
      v-if="error"
      type="error"
      :title="error"
      show-icon
      class="mt-8"
      data-test="logs-error"
      :closable="false"
    >
      <template #default>
        <el-button size="small" data-test="logs-retry" @click="load">重试</el-button>
      </template>
    </el-alert>

    <!-- 截断提示：结果超过适配器扫描上限 -->
    <el-alert
      v-if="!error && truncated"
      type="warning"
      title="检索结果已截断：当前数据源扫描达到上限，仅展示部分匹配记录（对筛选条件外偏序字段不影响）"
      show-icon
      class="mt-8"
      data-test="logs-truncated"
      :closable="false"
    />

    <!-- 结果列表 -->
    <el-card class="mt-8" header="检索结果" data-test="logs-result-card">
      <div class="result-toolbar">
        <span class="result-count" data-test="logs-count">共 {{ total }} 条</span>
        <div>
          <el-dropdown trigger="click" @command="(fmt: string) => doExport(fmt as 'csv' | 'json')">
            <el-button type="primary" plain :disabled="total === 0" data-test="logs-export">
              导出<el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="csv" data-test="logs-export-csv">导出 CSV</el-dropdown-item>
                <el-dropdown-item command="json" data-test="logs-export-json">导出 JSON</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>

      <div class="ob-table-scroll">
        <el-table
          v-loading="loading"
          :data="rows"
          stripe
          class="logs-table"
          empty-text="暂无匹配日志"
          data-test="logs-table"
          @row-click="openDetail"
        >
          <el-table-column label="时间" width="170">
            <template #default="{ row }">
              <span class="mono">{{ formatTs(row.ts) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="模块" width="96">
            <template #default="{ row }">{{ MODULE_LABELS[row.module as LogModule] ?? row.module }}</template>
          </el-table-column>
          <el-table-column label="操作" width="96">
            <template #default="{ row }">{{ OPERATION_LABELS[row.operation as LogOperation] ?? row.operation }}</template>
          </el-table-column>
          <el-table-column label="结果" width="88">
            <template #default="{ row }">
              <el-tag :type="resultTag(row.result as LogResult)" size="small">{{ RESULT_LABELS[row.result as LogResult] ?? row.result }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="请求" width="120">
            <template #default="{ row }">
              <span v-if="row.status_code" class="mono" :class="statusClass(row.status_code)">{{ row.status_code }}</span>
              <span v-else class="muted">—</span>
              <span class="muted"> / </span>
              <span class="mono">{{ row.method ?? '—' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="path" label="路径" min-width="180" show-overflow-tooltip data-test="logs-path-col">
            <template #default="{ row }"><span class="mono path-text" @click.stop>{{ row.path ?? '—' }}</span></template>
          </el-table-column>
          <el-table-column prop="request_id" label="request_id" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">
              <span v-if="row.request_id" class="mono" :data-test="`request-id-${row.request_id}`">{{ row.request_id }}</span>
              <span v-else class="muted">—</span>
            </template>
          </el-table-column>
          <el-table-column label="操作者" width="120">
            <template #default="{ row }"><span class="mono">{{ row.operator_id ?? '—' }}</span></template>
          </el-table-column>
          <el-table-column label="耗时" width="90">
            <template #default="{ row }">
              <span v-if="row.duration_ms != null" :class="durationClass(row.duration_ms)">{{ row.duration_ms }}ms</span>
              <span v-else class="muted">—</span>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="pagination-bar">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          background
          data-test="logs-pagination"
          @current-change="load"
          @size-change="onPageSizeChange"
        />
      </div>
    </el-card>

    <!-- 明细抽屉 -->
    <el-drawer
      v-model="detailOpen"
      size="520px"
      :title="`日志明细`"
      destroy-on-close
      data-test="logs-detail"
    >
      <template v-if="detail">
        <el-descriptions :column="1" border class="detail-desc">
          <el-descriptions-item label="时间">{{ formatTs(detail.ts) }}</el-descriptions-item>
          <el-descriptions-item label="数据源">{{ LOG_SOURCE_LABELS[detail.source] }}</el-descriptions-item>
          <el-descriptions-item label="模块">{{ MODULE_LABELS[detail.module] ?? detail.module }}</el-descriptions-item>
          <el-descriptions-item label="操作">{{ OPERATION_LABELS[detail.operation] ?? detail.operation }}</el-descriptions-item>
          <el-descriptions-item label="结果">
            <el-tag :type="resultTag(detail.result)" size="small">{{ RESULT_LABELS[detail.result] ?? detail.result }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="request_id"><span class="mono">{{ detail.request_id ?? '—' }}</span></el-descriptions-item>
          <el-descriptions-item label="HTTP">{{ detail.method }} {{ detail.status_code ?? '' }}</el-descriptions-item>
          <el-descriptions-item label="路径"><span class="mono">{{ detail.path ?? '—' }}</span></el-descriptions-item>
          <el-descriptions-item label="耗时"><span :class="durationClass(detail.duration_ms)">{{ detail.duration_ms }}ms</span></el-descriptions-item>
          <el-descriptions-item label="操作者"><span class="mono">{{ detail.operator_id ?? '—' }}</span></el-descriptions-item>
          <el-descriptions-item label="租户"><span class="mono">{{ detail.tenant_id ?? '—' }}</span></el-descriptions-item>
          <el-descriptions-item label="IP">{{ detail.ip_address ?? '—' }}</el-descriptions-item>
          <el-descriptions-item v-if="detail.case_id" label="用例"><span class="mono">{{ detail.case_id }}</span></el-descriptions-item>
          <el-descriptions-item v-if="detail.step_id != null" label="步骤"><span class="mono">{{ detail.step_id }}</span></el-descriptions-item>
          <el-descriptions-item v-if="detail.run_id" label="轮次"><span class="mono">{{ detail.run_id }}</span></el-descriptions-item>
          <el-descriptions-item v-if="detail.action" label="动作">{{ detail.action }}</el-descriptions-item>
        </el-descriptions>

        <div v-if="detail.summary" class="detail-summary">
          <div class="detail-section-title">摘要 / 结构化信息</div>
          <pre class="summary-json mono" data-test="logs-detail-summary">{{ prettyJson(detail.summary) }}</pre>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowDown } from '@element-plus/icons-vue'
import {
  logsApi,
  LOG_SOURCE_LABELS,
  LOG_SOURCE_OPTIONS,
  type LogEntry,
  type LogModule,
  type LogOperation,
  type LogQuery,
  type LogResult,
  type LogSource,
} from '@/core/api/logs'

/** 枚举标签（与后端 schema 枚举一致；契约唯一事实源为后端返回分类字段） */
const MODULE_LABELS: Record<LogModule, string> = {
  identity: '身份',
  dps: '数据处理',
  rag: '检索',
  memory: '记忆',
  llm: '大模型',
  gateway: '网关',
  testing: '测试',
  other: '其他',
}
const MODULE_OPTIONS = Object.keys(MODULE_LABELS) as LogModule[]

const OPERATION_LABELS: Record<LogOperation, string> = {
  auth_login: '登录',
  read: '读取',
  write: '写入',
  delete: '删除',
  config: '配置',
  proxy: '代理',
}
const OPERATION_OPTIONS = Object.keys(OPERATION_LABELS) as LogOperation[]

const RESULT_LABELS: Record<LogResult, string> = {
  success: '成功',
  client_error: '客户端错误',
  server_error: '服务端错误',
  unknown: '未知',
}
const RESULT_OPTIONS = Object.keys(RESULT_LABELS) as LogResult[]

function resultTag(r: LogResult): 'success' | 'warning' | 'danger' | 'info' {
  switch (r) {
    case 'success':
      return 'success'
    case 'client_error':
      return 'warning'
    case 'server_error':
      return 'danger'
    default:
      return 'info'
  }
}

const MODULE_OPTIONS_SET = new Set(MODULE_OPTIONS)
const OPERATION_OPTIONS_SET = new Set(OPERATION_OPTIONS)
const RESULT_OPTIONS_SET = new Set(RESULT_OPTIONS)

/** 筛选状态（多值以数组承载，匹配后端 OR 语义） */
const source = ref<LogSource>('l1_file')
const filters = ref<LogQuery>({ source: 'l1_file' })
const timeRange = ref<[string, string] | null>(null)
const advancedOpen = ref<string[]>([])

const rows = ref<LogEntry[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const error = ref('')
const truncated = ref(false)
const facets = ref<{ module: Record<string, number>; operation: Record<string, number>; result: Record<string, number> }>({ module: {}, operation: {}, result: {} })

const detailOpen = ref(false)
const detail = ref<LogEntry | null>(null)

/** 关键字变更做输入防抖自动检索（避免每次击键打接口） */
let debounceTimer: ReturnType<typeof setTimeout> | null = null
watch(
  () => filters.value.q,
  () => {
    if (debounceTimer) clearTimeout(debounceTimer)
    debounceTimer = setTimeout(() => load(), 400)
  },
)

/** 当前生效的查询对象（源切换时重置） */
function effectiveQuery(): LogQuery {
  const q: LogQuery = { source: source.value }
  if (filters.value.module?.length) q.module = [...filters.value.module]
  if (filters.value.operation?.length) q.operation = [...filters.value.operation]
  if (filters.value.result?.length) q.result = [...filters.value.result]
  if (filters.value.q) q.q = filters.value.q
  if (timeRange.value) {
    q.from = timeRange.value[0]
    q.to = timeRange.value[1]
  }
  if (filters.value.case_id) q.case_id = filters.value.case_id
  if (filters.value.run_id) q.run_id = filters.value.run_id
  if (filters.value.step_id !== undefined) q.step_id = filters.value.step_id
  return q
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const query = effectiveQuery()
    const [searchRes] = await Promise.all([logsApi.search(query, page.value, pageSize.value)])
    rows.value = searchRes.items
    total.value = searchRes.total
    truncated.value = searchRes.truncated
    page.value = searchRes.page
    await loadFacets(query)
  } catch (e) {
    rows.value = []
    total.value = 0
    truncated.value = false
    error.value = extractError(e)
  } finally {
    loading.value = false
  }
}

async function loadFacets(query: LogQuery): Promise<void> {
  try {
    const res = await logsApi.facets(query)
    facets.value = { module: res.module, operation: res.operation, result: res.result }
  } catch {
    facets.value = { module: {}, operation: {}, result: {} }
  }
}

function applyFilters(): void {
  page.value = 1
  void load()
}

function resetFilters(): void {
  filters.value = { source: source.value }
  timeRange.value = null
  page.value = 1
  void load()
}

function onChangeSource(): void {
  // 切源重置分页、错误态；保留关键字/时间等语义性过滤条件
  page.value = 1
  filters.value = { source: source.value, q: filters.value.q }
  void load()
}

function onPageSizeChange(): void {
  page.value = 1
  void load()
}

/** facets 标签点击 → 加入/移出对应筛选（即时检索） */
function toggleFacet(dimension: 'module' | 'operation' | 'result', key: string): void {
  const target = filters.value
  if (dimension === 'module' && MODULE_OPTIONS_SET.has(key as LogModule)) {
    target.module = toggleValue(target.module, key as LogModule)
  } else if (dimension === 'operation' && OPERATION_OPTIONS_SET.has(key as LogOperation)) {
    target.operation = toggleValue(target.operation, key as LogOperation)
  } else if (dimension === 'result' && RESULT_OPTIONS_SET.has(key as LogResult)) {
    target.result = toggleValue(target.result, key as LogResult)
  } else {
    return
  }
  page.value = 1
  void load()
}

function toggleValue<T extends string>(list: T[] | undefined, value: T): T[] {
  const current = list ?? []
  return current.includes(value) ? current.filter((item) => item !== value) : [...current, value]
}

async function doExport(format: 'csv' | 'json'): Promise<void> {
  try {
    const blob = await logsApi.export(effectiveQuery(), format)
    triggerDownload(blob, `logs-${format}-${source.value}.${format}`)
  } catch (e) {
    ElMessage.error(`导出失败：${extractError(e)}`)
  }
}

function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

function openDetail(row: LogEntry): void {
  detail.value = row
  detailOpen.value = true
}

function formatTs(ts: string): string {
  return ts.length > 19 ? ts.slice(0, 19).replace('T', ' ') : ts.replace('T', ' ')
}

function statusClass(code: number): string {
  if (code < 400) return 'status-ok'
  if (code < 500) return 'status-warn'
  return 'status-err'
}

function durationClass(ms: number | null): string {
  if (ms == null) return 'muted'
  if (ms < 1000) return 'duration-fast'
  if (ms < 5000) return 'duration-mid'
  return 'duration-slow'
}

function prettyJson(value: Record<string, unknown>): string {
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

function extractError(e: unknown): string {
  if (e instanceof Error) return e.message
  return String(e)
}

onMounted(() => void load())
</script>

<style scoped>
.logs-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.logs-filter-form :deep(.el-form-item) {
  margin-bottom: 0;
  margin-right: 16px;
}
.logs-facets .facets-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  padding: 2px 0;
}
.facets-label {
  width: 40px;
  font-size: 13px;
  color: #606266;
  font-weight: 600;
}
.facet-tag {
  cursor: pointer;
}
.result-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.result-count {
  color: #606266;
  font-size: 13px;
}
.logs-table :deep(.el-table__row) {
  cursor: pointer;
}
.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
.path-text {
  color: #303133;
}
.mono {
  font-family: 'JetBrains Mono', 'Consolas', monospace;
  font-size: 12px;
}
.muted {
  color: #a8abb2;
}
.status-ok {
  color: #67c23a;
}
.status-warn {
  color: #e6a23c;
}
.status-err {
  color: #f56c6c;
}
.duration-fast {
  color: #67c23a;
}
.duration-mid {
  color: #e6a23c;
}
.duration-slow {
  color: #f56c6c;
}
.detail-section-title {
  margin: 16px 0 8px;
  font-weight: 600;
  font-size: 14px;
}
.summary-json {
  background: #f5f7fa;
  border-radius: 4px;
  padding: 12px;
  max-height: 320px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>