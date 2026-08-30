<template>
  <div class="gpu-monitor">
    <div class="page-toolbar">
      <el-radio-group v-model="timeRange" data-test="gpu-range">
        <el-radio-button value="1h">1 小时</el-radio-button>
        <el-radio-button value="6h">6 小时</el-radio-button>
        <el-radio-button value="24h">24 小时</el-radio-button>
      </el-radio-group>
    </div>

    <el-alert
      v-if="noGpu"
      title="当前环境未检测到 GPU（可查看模拟演示数据）"
      type="warning"
      show-icon
      closable
      class="mb-16"
      data-test="gpu-no-env"
      @close="noGpu = false"
    />

    <el-card header="GPU 卡列表" class="mb-16" data-test="gpu-card">
      <div class="ob-table-scroll">
        <el-table :data="gpus" stripe empty-text="暂无 GPU 卡" data-test="gpu-table">
          <el-table-column prop="name" label="型号" min-width="160" />
          <el-table-column label="利用率" min-width="160">
            <template #default="{ row }">
              <el-progress :percentage="row.utilization" :color="utilColor(row.utilization)" />
            </template>
          </el-table-column>
          <el-table-column label="显存" width="140">
            <template #default="{ row }">{{ row.memory_used }} / {{ row.memory_total }} GB</template>
          </el-table-column>
          <el-table-column prop="temperature" label="温度(°C)" width="100">
            <template #default="{ row }">
              <el-tag :type="row.temperature > 85 ? 'danger' : 'info'" size="small">{{ row.temperature }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="power" label="功耗(W)" width="100" />
        </el-table>
      </div>
    </el-card>

    <el-card header="利用率趋势" data-test="gpu-trend-card">
      <div v-loading="trendLoading">
        <el-empty v-if="trendEmpty" description="暂无趋势数据" :image-size="80" data-test="gpu-trend-empty" />
        <div v-else ref="chartRef" class="chart" />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

interface GpuCard {
  name: string
  utilization: number
  memory_used: number
  memory_total: number
  temperature: number
  power: number
}

const mockGpus: GpuCard[] = [
  { name: 'NVIDIA A100 40GB #0', utilization: 72, memory_used: 31.2, memory_total: 40, temperature: 68, power: 285 },
  { name: 'NVIDIA A100 40GB #1', utilization: 45, memory_used: 22.8, memory_total: 40, temperature: 61, power: 210 },
  { name: 'NVIDIA A100 40GB #2', utilization: 12, memory_used: 8.4, memory_total: 40, temperature: 49, power: 95 },
  { name: 'NVIDIA RTX 4090 24GB #3', utilization: 91, memory_used: 22.1, memory_total: 24, temperature: 82, power: 420 },
]

const gpus = ref<GpuCard[]>(mockGpus)
const timeRange = ref('1h')
const noGpu = ref(true)
const trendLoading = ref(false)
const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

const trendEmpty = computed(() => gpus.value.length === 0)

function utilColor(v: number) {
  return v > 90 ? '#DC2626' : v > 70 ? '#D97706' : '#16A34A'
}

function renderTrend() {
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  const points = 24
  const hours = { '1h': 1, '6h': 6, '24h': 24 }[timeRange.value] || 1
  const labels: string[] = []
  const series: number[][] = gpus.value.map((g) => {
    const data: number[] = []
    for (let i = 0; i < points; i += 1) {
      const base = g.utilization
      const wave = Math.sin((i / points) * Math.PI * 4) * 8
      data.push(Math.max(0, Math.min(100, Math.round(base + wave + (Math.random() - 0.5) * 6))))
    }
    return data
  })
  for (let i = 0; i < points; i += 1) {
    const offset = hours - (hours * i) / (points - 1)
    labels.push(`-${offset.toFixed(1)}h`)
  }
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: gpus.value.map((g) => g.name) },
    grid: { left: 40, right: 20, top: 40, bottom: 40 },
    xAxis: { type: 'category', data: labels },
    yAxis: { type: 'value', max: 100 },
    series: gpus.value.map((g, idx) => ({
      name: g.name,
      type: 'line',
      smooth: true,
      showSymbol: false,
      data: series[idx],
    })),
  })
}

watch(timeRange, () => nextTick(renderTrend))

onMounted(() => {
  trendLoading.value = true
  setTimeout(() => {
    trendLoading.value = false
    nextTick(renderTrend)
  }, 300)
})

onBeforeUnmount(() => {
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
.chart { height: 320px; }
</style>
