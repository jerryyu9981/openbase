<template>
  <div>
    <el-row :gutter="16">
      <el-col :xs="12" :lg="6" v-for="card in metricCards" :key="card.label">
        <el-card class="metric-card">
          <div class="metric-label">{{ card.label }}</div>
          <div class="metric-value">{{ card.value }}</div>
        </el-card>
      </el-col>
    </el-row>
    <el-card class="mt-16" header="请求量趋势（10s 自动轮询）" data-test="monitoring-chart">
      <div ref="chartRef" class="chart" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'

const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

const metricCards = [
  { label: 'QPS', value: '128' },
  { label: '平均延迟', value: '240ms' },
  { label: 'P50', value: '198ms' },
  { label: 'P99', value: '1,024ms' },
]

function renderChart() {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 16, top: 24, bottom: 28 },
    xAxis: { type: 'category', data: ['09:00', '09:10', '09:20', '09:30', '09:40', '09:50', '10:00'] },
    yAxis: { type: 'value' },
    series: [{ type: 'line', smooth: true, data: [80, 96, 110, 132, 118, 140, 128], areaStyle: { opacity: 0.15 } }],
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
})
</script>

<style scoped>
.metric-card { text-align: center; }
.metric-label { color: var(--ob-text-secondary); font-size: 13px; }
.metric-value { font-size: 22px; font-weight: 600; margin-top: 6px; }
.mt-16 { margin-top: 16px; }
.chart { height: 320px; }
</style>
