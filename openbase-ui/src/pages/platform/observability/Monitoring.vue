<template>
  <PageContainer title="统一监控" description="服务指标与最新告警（OpenLLM Monitoring Dashboard）" test-id="monitoring-page">
    <template #actions>
      <el-radio-group v-model="timeRange" data-test="time-range" @change="loadDashboard">
        <el-radio-button value="1h">1 小时</el-radio-button>
        <el-radio-button value="6h">6 小时</el-radio-button>
        <el-radio-button value="24h">24 小时</el-radio-button>
        <el-radio-button value="7d">7 天</el-radio-button>
        <el-radio-button value="30d">30 天</el-radio-button>
      </el-radio-group>
    </template>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="monitoring-error"
      @close="errorMessage = ''"
    />

    <el-row :gutter="16" v-loading="loading">
      <el-col v-for="card in metricCards" :key="card.label" :xs="12" :lg="6">
        <el-card class="metric-card" data-test="monitoring-metric">
          <div class="metric-label">{{ card.label }}</div>
          <div class="metric-value" :style="card.danger ? 'color: var(--el-color-danger)' : ''">{{ card.value }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="mt-16" header="请求量与延迟趋势" data-test="monitoring-chart">
      <el-empty v-if="timeSeries.length === 0" description="该时间范围内暂无指标数据" :image-size="70" data-test="monitoring-chart-empty" />
      <div v-else ref="chartRef" class="chart" />
    </el-card>

    <el-card class="mt-16" header="最新告警" data-test="alert-list">
      <el-table :data="alerts" size="small" data-test="monitoring-alert-table">
        <template #empty>
          <el-empty description="暂无未解决告警" :image-size="50" data-test="monitoring-alert-empty" />
        </template>
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ formatTime(row.fired_at || row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="级别" width="90">
          <template #default="{ row }">
            <el-tag :type="severityType(row.severity)" size="small">{{ severityLabel(row.severity) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="标题" min-width="160" show-overflow-tooltip />
        <el-table-column prop="message" label="内容" min-width="220" show-overflow-tooltip />
      </el-table>
      <div class="list-footer">
        <el-button link type="primary" @click="$router.push('/platform/observability/monitoring/alerts')">告警中心 →</el-button>
        <el-button link type="primary" @click="$router.push('/platform/observability/monitoring/traces')">链路追踪 →</el-button>
        <el-button link type="primary" @click="$router.push('/platform/observability/monitoring/budgets')">预算管理 →</el-button>
        <el-button link type="primary" @click="$router.push('/platform/observability/app-calls')">应用调用记录 →</el-button>
      </div>
    </el-card>
  </PageContainer>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import PageContainer from '@/components/page/PageContainer.vue'
import {
  alertsApi,
  monitoringApi,
  type LlmAlertItem,
  type LlmMonitoringDashboard,
  type LlmMonitoringTimePoint,
} from '@/core/api/governance'

/**
 * 统一监控（v1.9.7 R7 真实化）：`/monitoring/dashboard`（概览/性能/成本/错误/资源）
 * + `/alerts?resolved=false` 最新告警。移除本地 KPI 与随机曲线。
 */
const timeRange = ref('6h')
const loading = ref(false)
const errorMessage = ref('')
const dashboard = ref<LlmMonitoringDashboard | null>(null)
const alerts = ref<LlmAlertItem[]>([])
const timeSeries = computed<LlmMonitoringTimePoint[]>(() => dashboard.value?.performance?.time_series ?? [])

const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

const metricCards = computed(() => {
  const overview = dashboard.value?.overview
  return [
    { label: '请求量', value: String(overview?.total_requests ?? 0), danger: false },
    { label: 'Token 消耗', value: String(overview?.total_tokens ?? 0), danger: false },
    { label: '成本($)', value: Number(overview?.total_cost ?? 0).toFixed(2), danger: false },
    { label: '错误率', value: `${Number(overview?.error_rate ?? 0).toFixed(2)}%`, danger: Number(overview?.error_rate ?? 0) > 1 },
  ]
})

function severityType(severity: string) {
  return { critical: 'danger', high: 'danger', medium: 'warning', low: 'info', info: 'info' }[severity] || 'info'
}
function severityLabel(severity: string) {
  return { critical: '严重', high: '高', medium: '中', low: '低', info: '提示' }[severity] || severity
}
function formatTime(value: string | null) {
  if (!value) return '-'
  return value.replace('T', ' ').slice(0, 19)
}

function renderChart() {
  if (!chartRef.value || timeSeries.value.length === 0) return
  if (!chart) chart = echarts.init(chartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['请求量', '平均延迟(ms)'] },
    grid: { left: 50, right: 56, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: timeSeries.value.map((point) => point.timestamp) },
    yAxis: [
      { type: 'value', name: '请求量' },
      { type: 'value', name: '延迟(ms)' },
    ],
    series: [
      {
        name: '请求量',
        type: 'line',
        smooth: true,
        data: timeSeries.value.map((point) => point.request_count),
        areaStyle: { opacity: 0.12 },
      },
      {
        name: '平均延迟(ms)',
        type: 'line',
        smooth: true,
        yAxisIndex: 1,
        data: timeSeries.value.map((point) => point.avg_latency_ms),
      },
    ],
  })
}

function handleResize() {
  chart?.resize()
}

async function loadDashboard() {
  loading.value = true
  errorMessage.value = ''
  try {
    dashboard.value = await monitoringApi.dashboard(timeRange.value)
    await nextTick()
    renderChart()
  } catch (error) {
    errorMessage.value = `监控数据加载失败：${error instanceof Error ? error.message : '未知错误'}`
  } finally {
    loading.value = false
  }
}

async function loadAlerts() {
  try {
    const page = await alertsApi.list({ status: 'firing', page: 1, page_size: 10 })
    alerts.value = page.alerts
  } catch (error) {
    errorMessage.value = errorMessage.value || `告警加载失败：${error instanceof Error ? error.message : '未知错误'}`
  }
}

onMounted(async () => {
  window.addEventListener('resize', handleResize)
  await Promise.all([loadDashboard(), loadAlerts()])
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.metric-card { text-align: center; }
.metric-label { color: var(--ob-text-secondary); font-size: 13px; }
.metric-value { font-size: 22px; font-weight: 600; margin-top: 6px; }
.mt-16 { margin-top: 16px; }
.chart { height: 320px; }
.list-footer { margin-top: 8px; text-align: right; }
</style>
