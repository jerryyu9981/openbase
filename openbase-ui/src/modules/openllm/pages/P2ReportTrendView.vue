<template>
  <div class="p2-reports">
    <el-row :gutter="16">
      <el-col :span="16">
        <el-card header="报表趋势分析" data-test="rep-trend-card">
          <div class="page-toolbar">
            <el-radio-group v-model="range" size="small" data-test="rep-range">
              <el-radio-button value="7d">近 7 天</el-radio-button>
              <el-radio-button value="30d">近 30 天</el-radio-button>
              <el-radio-button value="90d">近 90 天</el-radio-button>
            </el-radio-group>
          </div>
          <div ref="trendRef" class="trend-chart" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card header="组织排名" data-test="rep-rank-card">
          <el-table :data="rankings" size="small" empty-text="暂无排名" data-test="rep-rank-table">
            <el-table-column label="排名" width="60">
              <template #default="{ row }">
                <span class="rank-badge" :class="{ top: row.rank <= 3 }">{{ row.rank }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="org" label="组织" min-width="110" />
            <el-table-column prop="usage" label="调用量" width="100" />
            <el-table-column prop="trend" label="趋势" width="70">
              <template #default="{ row }">
                <el-tag :type="row.trend.startsWith('+') ? 'success' : 'danger'" size="small">{{ row.trend }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const range = ref('30d')
const trendRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

const rankings = ref([
  { rank: 1, org: 'AI 平台部', usage: '2,340,000', trend: '+12.4%' },
  { rank: 2, org: '模型组', usage: '1,890,000', trend: '+8.2%' },
  { rank: 3, org: '运维部', usage: '620,000', trend: '-3.1%' },
  { rank: 4, org: '外部客户', usage: '180,000', trend: '+35.0%' },
])

function renderTrend() {
  if (!trendRef.value) return
  if (!chart) chart = echarts.init(trendRef.value)
  const points = range.value === '7d' ? 7 : range.value === '30d' ? 30 : 12
  const labels: string[] = []
  const data: number[] = []
  const base = range.value === '7d' ? 60 : 72
  for (let i = 0; i < points; i += 1) {
    labels.push(range.value === '90d' ? `W${i + 1}` : `D${i + 1}`)
    data.push(Math.round(base + Math.sin(i / 4) * 15 + Math.random() * 10))
  }
  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 60, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: labels },
    yAxis: { type: 'value' },
    series: [{ name: '调用量(千)', type: 'line', smooth: true, areaStyle: { opacity: 0.15 }, data }],
  })
}

watch(range, () => nextTick(renderTrend))
onMounted(() => nextTick(renderTrend))
onBeforeUnmount(() => {
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
.trend-chart { height: 340px; }
.rank-badge { display: inline-flex; width: 24px; height: 24px; border-radius: 50%; background: #f1f5f9; align-items: center; justify-content: center; font-size: 13px; }
.rank-badge.top { background: #1677FF; color: #fff; }
</style>
