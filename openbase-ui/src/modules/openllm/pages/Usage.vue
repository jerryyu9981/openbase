<template>
  <div>
    <div class="page-toolbar">
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        value-format="YYYY-MM-DD"
        :shortcuts="rangeShortcuts"
        data-test="usage-range"
      />
      <el-button type="primary" :loading="loading" data-test="usage-query" @click="loadUsage">查询</el-button>
      <el-button :disabled="filteredRows.length === 0" data-test="usage-export" @click="exportCsv">导出 CSV</el-button>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="usage-error"
      @close="errorMessage = ''"
    />

    <el-card header="用量趋势" class="mb-16" data-test="usage-chart-card">
      <div v-loading="loading">
        <el-empty v-if="trendEmpty" description="该时间范围内暂无趋势数据" :image-size="80" data-test="usage-chart-empty" />
        <div v-else ref="chartRef" class="chart" />
      </div>
    </el-card>

    <el-card header="用量明细" data-test="usage-table-card">
      <div class="table-toolbar">
        <el-select v-model="modelFilter" placeholder="模型筛选" clearable style="width: 180px" data-test="usage-model-filter">
          <el-option v-for="model in mockModels" :key="model" :label="model" :value="model" />
        </el-select>
        <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width: 130px" data-test="usage-status-filter">
          <el-option label="计费" value="billing" />
          <el-option label="免费" value="free" />
          <el-option label="异常" value="error" />
        </el-select>
      </div>
      <div class="ob-table-scroll">
        <el-table :data="pagedRows" stripe empty-text="暂无明细数据" data-test="usage-table">
          <el-table-column prop="date" label="日期" width="120" />
          <el-table-column prop="model" label="模型" min-width="150" />
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="requests" label="调用次数" width="100" />
          <el-table-column prop="input_tokens" label="输入 Tokens" width="120" />
          <el-table-column prop="output_tokens" label="输出 Tokens" width="120" />
          <el-table-column label="费用($)" width="100">
            <template #default="{ row }">{{ row.cost.toFixed(4) }}</template>
          </el-table-column>
        </el-table>
      </div>
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="filteredRows.length"
        :page-sizes="[5, 10, 20]"
        layout="total, sizes, prev, pager, next, jumper"
        class="usage-pagination"
        data-test="usage-pagination"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'

interface UsageRow {
  date: string
  model: string
  status: 'billing' | 'free' | 'error'
  requests: number
  input_tokens: number
  output_tokens: number
  cost: number
}

/** 契约 mock：可查询区间为最近 30 天（不调用真实 API） */
const MIN_QUERY_DAYS = 30

function formatDate(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}
function daysAgo(days: number): string {
  const date = new Date()
  date.setDate(date.getDate() - days)
  return formatDate(date)
}
function today(): string {
  return formatDate(new Date())
}

const rangeShortcuts = [
  { text: '最近 7 天', value: () => [new Date(Date.now() - 6 * 86400000), new Date()] },
  { text: '最近 30 天', value: () => [new Date(Date.now() - 29 * 86400000), new Date()] },
]

const dateRange = ref<[string, string]>([daysAgo(29), today()])
const loading = ref(true)
const errorMessage = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const modelFilter = ref('')
const statusFilter = ref('')

const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

const mockModels = ['gpt-4o', 'gpt-4o-mini', 'qwen2.5-7b', 'bge-m3', 'claude-3-5-sonnet']
const mockStatuses = ['billing', 'free', 'error'] as const

const allRows = ref<UsageRow[]>([])

/** 契约 mock：生成本地最近 30 天明细数据 */
function buildMockRows(): UsageRow[] {
  const rows: UsageRow[] = []
  const start = new Date()
  start.setDate(start.getDate() - (MIN_QUERY_DAYS - 1))
  for (let index = 0; index < MIN_QUERY_DAYS; index += 1) {
    const date = new Date(start)
    date.setDate(start.getDate() + index)
    mockModels.forEach((model, modelIndex) => {
      rows.push({
        date: formatDate(date),
        model,
        status: mockStatuses[(index + modelIndex) % mockStatuses.length],
        requests: Math.floor(80 + Math.random() * 1800),
        input_tokens: Math.floor(20000 + Math.random() * 700000),
        output_tokens: Math.floor(10000 + Math.random() * 350000),
        cost: Number((Math.random() * 8).toFixed(4)),
      })
    })
  }
  return rows
}

const inRangeRows = computed(() => {
  const [start, end] = dateRange.value
  return allRows.value.filter((row) => row.date >= start && row.date <= end)
})

const filteredRows = computed(() => {
  const model = modelFilter.value
  const status = statusFilter.value
  return inRangeRows.value.filter(
    (row) => (!model || row.model === model) && (!status || row.status === status),
  )
})

const pagedRows = computed(() => {
  const offset = (currentPage.value - 1) * pageSize.value
  return filteredRows.value.slice(offset, offset + pageSize.value)
})

const trendData = computed(() => {
  const buckets = new Map<string, { requests: number; tokens: number }>()
  for (const row of inRangeRows.value) {
    const bucket = buckets.get(row.date) ?? { requests: 0, tokens: 0 }
    bucket.requests += row.requests
    bucket.tokens += row.input_tokens + row.output_tokens
    buckets.set(row.date, bucket)
  }
  const dates = [...buckets.keys()].sort()
  return {
    dates,
    requests: dates.map((date) => buckets.get(date)!.requests),
    tokens: dates.map((date) => Math.round(buckets.get(date)!.tokens / 10000)),
  }
})

const trendEmpty = computed(() => trendData.value.dates.length === 0)

function statusType(status: string) {
  return { billing: 'success', free: 'info', error: 'danger' }[status] || 'info'
}
function statusLabel(status: string) {
  return { billing: '计费', free: '免费', error: '异常' }[status] || status
}

function renderChart() {
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['调用次数', 'Token 消耗(万)'] },
    grid: { left: 48, right: 16, top: 40, bottom: 28 },
    xAxis: { type: 'category', boundaryGap: false, data: trendData.value.dates },
    yAxis: { type: 'value' },
    series: [
      { name: '调用次数', type: 'line', smooth: true, data: trendData.value.requests, areaStyle: { opacity: 0.12 } },
      { name: 'Token 消耗(万)', type: 'line', smooth: true, data: trendData.value.tokens, areaStyle: { opacity: 0.12 } },
    ],
  })
}

function handleResize() {
  chart?.resize()
}

async function loadUsage() {
  errorMessage.value = ''
  const [start, end] = dateRange.value
  if (start > end) {
    errorMessage.value = '时间范围无效：开始日期不能晚于结束日期'
    return
  }
  if (start < daysAgo(MIN_QUERY_DAYS)) {
    errorMessage.value = '所选时间范围超出统计数据可查询区间（最近 30 天）'
    return
  }
  loading.value = true
  try {
    await mockDelay(600) // 契约 mock：模拟请求统计接口
    currentPage.value = 1
    await nextTick()
    renderChart()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '用量统计加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

function exportCsv() {
  if (filteredRows.value.length === 0) {
    ElMessage.warning('当前筛选结果为空，无可导出的数据')
    return
  }
  const header = ['日期', '模型', '状态', '调用次数', '输入Tokens', '输出Tokens', '费用($)']
  const lines = filteredRows.value.map((row) =>
    [row.date, row.model, statusLabel(row.status), row.requests, row.input_tokens, row.output_tokens, row.cost.toFixed(4)].join(','),
  )
  const csv = '\uFEFF' + [header.join(','), ...lines].join('\n')
  const [start, end] = dateRange.value
  const filename = `usage-${start}_${end}.csv`
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  ElMessage.success(`已导出 ${filteredRows.value.length} 条记录：${filename}`)
}

function mockDelay(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms))
}

onMounted(() => {
  allRows.value = buildMockRows()
  window.addEventListener('resize', handleResize)
  void loadUsage()
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.page-toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  align-items: center;
}
.mb-16 {
  margin-bottom: 16px;
}
.table-toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.chart {
  height: 320px;
}
.usage-pagination {
  margin-top: 12px;
  justify-content: flex-end;
}
</style>
