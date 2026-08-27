<template>
  <div>
    <div class="page-toolbar">
      <el-radio-group v-model="timeRange" data-test="time-range" @change="renderChart">
        <el-radio-button value="1h">1 小时</el-radio-button>
        <el-radio-button value="6h">6 小时</el-radio-button>
        <el-radio-button value="24h">24 小时</el-radio-button>
        <el-radio-button value="7d">7 天</el-radio-button>
      </el-radio-group>
    </div>
    <el-row :gutter="16">
      <el-col v-for="card in metricCards" :key="card.label" :xs="12" :lg="6">
        <el-card class="metric-card">
          <div class="metric-label">{{ card.label }}</div>
          <div class="metric-value" :style="card.danger ? 'color: var(--el-color-danger)' : ''">{{ card.value }}</div>
        </el-card>
      </el-col>
    </el-row>
    <el-card class="mt-16" header="请求量趋势（自动轮询）" data-test="monitoring-chart">
      <div ref="chartRef" class="chart" />
    </el-card>
    <el-card class="mt-16" header="最新告警" data-test="alert-list">
      <el-table :data="alerts" size="small">
        <el-table-column prop="time" label="时间" width="160" />
        <el-table-column label="级别" width="90">
          <template #default="{ row }">
            <el-tag :type="alertType(row.level)" size="small">{{ row.level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="content" label="内容" />
      </el-table>
      <div class="list-footer">
        <el-button link type="primary" @click="$router.push('/openllm/monitoring/alerts')">前往告警中心 →</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'

const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null
const timeRange = ref('6h')

const metricCards = ref([
  { label: '请求量', value: '12,480', danger: false },
  { label: 'Token 消耗', value: '8.2M', danger: false },
  { label: '成本', value: '$1,204.5', danger: false },
  { label: '错误率', value: '0.8%', danger: true },
])

const alerts = ref([
  { time: '2026-08-27 09:42', level: '严重', content: 'P99 延迟超过 1s 阈值' },
  { time: '2026-08-27 09:15', level: '警告', content: 'OpenAI 提供商错误率升高' },
  { time: '2026-08-27 08:58', level: '提示', content: '成本预算使用率达 80%' },
])

const rangeData: Record<string, { x: string[]; y: number[] }> = {
  '1h': { x: ['09:00', '09:10', '09:20', '09:30', '09:40', '09:50', '10:00'], y: [80, 96, 110, 132, 118, 140, 128] },
  '6h': { x: ['04:00', '05:00', '06:00', '07:00', '08:00', '09:00', '10:00'], y: [52, 61, 78, 94, 105, 118, 128] },
  '24h': { x: ['昨天 10:00', '14:00', '18:00', '22:00', '02:00', '06:00', '10:00'], y: [60, 88, 122, 96, 40, 55, 128] },
  '7d': { x: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'], y: [98, 112, 105, 132, 145, 88, 128] },
}

function alertType(level: string) {
  return { 严重: 'danger', 警告: 'warning', 提示: 'info' }[level] || 'info'
}

function renderChart() {
  if (!chartRef.value) return
  chart = chart || echarts.init(chartRef.value)
  const data = rangeData[timeRange.value]
  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 16, top: 24, bottom: 28 },
    xAxis: { type: 'category', data: data.x },
    yAxis: { type: 'value' },
    series: [{ type: 'line', smooth: true, data: data.y, areaStyle: { opacity: 0.15 } }],
  })
}

function handleResize() { chart?.resize() }

onMounted(() => {
  renderChart()
  window.addEventListener('resize', handleResize)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.page-toolbar { margin-bottom: 16px; }
.metric-card { text-align: center; }
.metric-label { color: var(--ob-text-secondary); font-size: 13px; }
.metric-value { font-size: 22px; font-weight: 600; margin-top: 6px; }
.mt-16 { margin-top: 16px; }
.chart { height: 320px; }
.list-footer { margin-top: 8px; text-align: right; }
</style>
