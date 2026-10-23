<template>
  <PageContainer title="用量统计" description="调用量与 Token 统计（OpenLLM 用量服务）" test-id="usage-page">
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

    <el-row :gutter="16">
      <el-col v-for="card in statCards" :key="card.label" :xs="12" :lg="6">
        <el-card class="stat-card" data-test="usage-stat">
          <div class="stat-label">{{ card.label }}</div>
          <div class="stat-value">{{ card.value }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card header="用量趋势" class="mt-16" data-test="usage-chart-card">
      <div v-loading="loading">
        <el-empty v-if="trendEmpty" description="该时间范围内暂无趋势数据" :image-size="80" data-test="usage-chart-empty" />
        <div v-else ref="chartRef" class="chart" data-test="usage-chart" />
      </div>
    </el-card>

    <el-card header="用量明细" class="mt-16" data-test="usage-table-card">
      <div class="table-toolbar">
        <el-input
          v-model="keyword"
          placeholder="按模型/请求 ID 筛选"
          clearable
          style="width: 220px"
          data-test="usage-keyword-filter"
        />
        <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width: 130px" data-test="usage-status-filter">
          <el-option label="成功" value="success" />
          <el-option label="失败" value="error" />
        </el-select>
        <span class="text-muted">已加载 {{ records.length }} 条（上限 200）</span>
      </div>
      <div class="ob-table-scroll">
        <el-table :data="pagedRows" stripe data-test="usage-table">
          <template #empty>
            <el-empty description="暂无明细数据" :image-size="60" data-test="usage-empty" />
          </template>
          <el-table-column label="时间" width="170">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column prop="request_id" label="请求 ID" min-width="180" show-overflow-tooltip />
          <el-table-column prop="model_id" label="模型 ID" min-width="160" show-overflow-tooltip />
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="tokens_input" label="输入 Tokens" width="120" />
          <el-table-column prop="tokens_output" label="输出 Tokens" width="120" />
          <el-table-column label="延迟(ms)" width="100">
            <template #default="{ row }">{{ row.latency_ms ?? '-' }}</template>
          </el-table-column>
          <el-table-column label="费用($)" width="110">
            <template #default="{ row }">{{ Number(row.cost ?? 0).toFixed(6) }}</template>
          </el-table-column>
        </el-table>
      </div>
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="filteredRows.length"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        class="pagination"
        data-test="usage-pagination"
      />
    </el-card>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { usageApi, type LlmUsageRecord, type LlmUsageSummary, type LlmUsageTrendPoint } from '@/core/api/governance'

/**
 * 用量统计（v1.9.4 R4 真实化）：总览 `/usage/summary`、趋势 `/usage/trends`、明细 `/usage/detail`。
 * 明细服务端单次上限 1000，本页取最近 200 条并在页内筛选/分页；导出为当前筛选结果（CSV）。
 */
const DETAIL_LIMIT = 200

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

const rangeShortcuts = [
  { text: '最近 7 天', value: () => [new Date(Date.now() - 6 * 86400000), new Date()] },
  { text: '最近 30 天', value: () => [new Date(Date.now() - 29 * 86400000), new Date()] },
]

const dateRange = ref<[string, string]>([daysAgo(29), formatDate(new Date())])
const loading = ref(false)
const errorMessage = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const keyword = ref('')
const statusFilter = ref('')

const summary = ref<LlmUsageSummary | null>(null)
const trendSeries = ref<LlmUsageTrendPoint[]>([])
const records = ref<LlmUsageRecord[]>([])

const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

const statCards = computed(() => [
  { label: '调用次数', value: String(summary.value?.total_requests ?? 0) },
  { label: 'Token 总量', value: String(summary.value?.total_tokens ?? 0) },
  { label: '总费用($)', value: Number(summary.value?.total_cost ?? 0).toFixed(4) },
  { label: '平均延迟', value: `${Number(summary.value?.avg_latency_ms ?? 0).toFixed(0)} ms` },
])

const filteredRows = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  return records.value.filter((row) => {
    const matchesStatus = !statusFilter.value || row.status === statusFilter.value
    const matchesKeyword =
      !text ||
      (row.model_id ?? '').toLowerCase().includes(text) ||
      (row.request_id ?? '').toLowerCase().includes(text)
    return matchesStatus && matchesKeyword
  })
})

const pagedRows = computed(() => {
  const offset = (currentPage.value - 1) * pageSize.value
  return filteredRows.value.slice(offset, offset + pageSize.value)
})

const trendEmpty = computed(() => trendSeries.value.length === 0)

watch([keyword, statusFilter], () => {
  currentPage.value = 1
})

function statusType(status: string) {
  return { success: 'success', error: 'danger' }[status] || 'info'
}
function statusLabel(status: string) {
  return { success: '成功', error: '失败' }[status] || status
}
function formatTime(value: string | null) {
  if (!value) return '-'
  return value.replace('T', ' ').slice(0, 19)
}

function renderChart() {
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['调用次数', 'Token 消耗(万)'] },
    grid: { left: 48, right: 16, top: 40, bottom: 28 },
    xAxis: { type: 'category', boundaryGap: false, data: trendSeries.value.map((point) => point.date) },
    yAxis: { type: 'value' },
    series: [
      {
        name: '调用次数',
        type: 'line',
        smooth: true,
        data: trendSeries.value.map((point) => point.requests),
        areaStyle: { opacity: 0.12 },
      },
      {
        name: 'Token 消耗(万)',
        type: 'line',
        smooth: true,
        data: trendSeries.value.map((point) => Math.round(point.total_tokens / 10000)),
        areaStyle: { opacity: 0.12 },
      },
    ],
  })
}

function handleResize() {
  chart?.resize()
}

async function loadUsage() {
  errorMessage.value = ''
  const [start, end] = dateRange.value ?? []
  if (!start || !end) {
    errorMessage.value = '请选择统计时间范围'
    return
  }
  if (start > end) {
    errorMessage.value = '时间范围无效：开始日期不能晚于结束日期'
    return
  }
  loading.value = true
  try {
    const [summaryData, trendData, detailData] = await Promise.all([
      usageApi.summary({ period: 'daily', group_by: 'day', start_date: start, end_date: end }),
      usageApi.trends({ dimension: 'time', period: 'day', start_date: start, end_date: end }),
      usageApi.detail({ start_date: start, end_date: end, skip: 0, limit: DETAIL_LIMIT }),
    ])
    summary.value = summaryData
    trendSeries.value = trendData.series ?? []
    records.value = detailData.records ?? []
    currentPage.value = 1
    await nextTick()
    renderChart()
  } catch (error) {
    errorMessage.value = `用量统计加载失败：${error instanceof Error ? error.message : '未知错误'}`
  } finally {
    loading.value = false
  }
}

function exportCsv() {
  if (filteredRows.value.length === 0) {
    ElMessage.warning('当前筛选结果为空，无可导出的数据')
    return
  }
  const header = ['时间', '请求ID', '模型ID', '状态', '输入Tokens', '输出Tokens', '延迟(ms)', '费用($)']
  const lines = filteredRows.value.map((row) =>
    [
      formatTime(row.created_at),
      row.request_id,
      row.model_id,
      statusLabel(row.status),
      row.tokens_input,
      row.tokens_output,
      row.latency_ms ?? '',
      Number(row.cost ?? 0).toFixed(6),
    ].join(','),
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

onMounted(() => {
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
.mb-16 {
  margin-bottom: 16px;
}
.mt-16 {
  margin-top: 16px;
}
.table-toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
  align-items: center;
}
.chart {
  height: 320px;
}
.pagination {
  margin-top: 12px;
  justify-content: flex-end;
}
.stat-card {
  text-align: center;
}
.stat-label {
  color: var(--ob-text-secondary);
  font-size: 13px;
}
.stat-value {
  font-size: 20px;
  font-weight: 600;
  margin-top: 6px;
}
.text-muted {
  color: var(--ob-text-secondary);
  font-size: 12px;
}
</style>
