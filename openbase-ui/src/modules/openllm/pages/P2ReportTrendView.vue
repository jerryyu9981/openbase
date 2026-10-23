<template>
  <PageContainer title="报表趋势" description="调用量、Token 与成本趋势（真实聚合）" test-id="p2-report-trend-view-page">
    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="rep-error"
      @close="errorMessage = ''"
    />

    <el-row :gutter="16" class="mb-16">
      <el-col v-for="item in kpis" :key="item.label" :span="6">
        <el-card shadow="hover" data-test="rep-kpi">
          <div class="kpi-label">{{ item.label }}</div>
          <div class="kpi-value">{{ item.value }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :span="16">
        <el-card header="调用量与 Token 趋势" data-test="rep-trend-card">
          <div class="page-toolbar">
            <el-radio-group v-model="range" size="small" data-test="rep-range">
              <el-radio-button value="7d">近 7 天</el-radio-button>
              <el-radio-button value="30d">近 30 天</el-radio-button>
            </el-radio-group>
            <el-button :loading="loading" size="small" data-test="rep-refresh" @click="load">刷新</el-button>
          </div>
          <div ref="trendRef" class="trend-chart" data-test="rep-chart" />
          <el-empty v-if="!loading && series.length === 0" description="暂无趋势数据" :image-size="60" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card header="成本排名（用户，Top 5）" data-test="rep-rank-card">
          <el-table :data="rankings" size="small" empty-text="暂无成本数据" data-test="rep-rank-table">
            <el-table-column label="排名" width="60">
              <template #default="{ $index }">
                <span class="rank-badge" :class="{ top: $index < 3 }">{{ $index + 1 }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="user" label="用户" min-width="120" show-overflow-tooltip />
            <el-table-column label="成本" width="100">
              <template #default="{ row }">${{ row.cost.toFixed(4) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { monitoringApi, usageApi, type LlmMonitoringDashboard } from '@/core/api/governance'
import { describeError } from '@/core/api/error'

/**
 * 报表趋势（v1.12.0 / XR-LLM-03 报表部分）：复用 OpenLLM 既有聚合端点，
 * 不新增后端接口。展示概览 KPI + 调用量/Token 双轴趋势 + 用户成本排名。
 */
const RANGE_DAYS: Record<string, number> = { '7d': 7, '30d': 30 }

const range = ref('30d')
const loading = ref(false)
const errorMessage = ref('')
const dashboard = ref<LlmMonitoringDashboard | null>(null)
const series = ref<Array<Record<string, unknown>>>([])
const rankings = ref<Array<{ user: string; cost: number }>>([])
const trendRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

function errorText(error: unknown, fallback: string) {
  return describeError(error).detail || fallback
}

const kpis = computed(() => {
  const overview = dashboard.value?.overview
  if (!overview) {
    return [
      { label: '调用量', value: '—' },
      { label: 'Token', value: '—' },
      { label: '成本', value: '—' },
      { label: '平均延迟', value: '—' },
    ]
  }
  return [
    { label: '调用量', value: Number(overview.total_requests).toLocaleString() },
    { label: 'Token', value: Number(overview.total_tokens).toLocaleString() },
    { label: '成本', value: `$${Number(overview.total_cost).toFixed(2)}` },
    { label: '平均延迟', value: `${Number(overview.avg_latency_ms).toFixed(0)} ms` },
  ]
})

function renderChart() {
  if (!trendRef.value) return
  if (!series.value.length) {
    chart?.clear()
    return
  }
  if (trendRef.value.clientWidth === 0) return
  if (!chart) chart = echarts.init(trendRef.value)
  const labels = series.value.map((point) => String(point.date ?? ''))
  const requests = series.value.map((point) => Number(point.requests ?? 0))
  const tokens = series.value.map((point) => Number(point.total_tokens ?? 0))
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['调用量', 'Token'] },
    grid: { left: 60, right: 60, top: 40, bottom: 40 },
    xAxis: { type: 'category', data: labels },
    yAxis: [
      { type: 'value', name: '调用量' },
      { type: 'value', name: 'Token' },
    ],
    series: [
      { name: '调用量', type: 'line', smooth: true, areaStyle: { opacity: 0.12 }, data: requests, yAxisIndex: 0 },
      { name: 'Token', type: 'bar', data: tokens, yAxisIndex: 1 },
    ],
  })
}

async function loadUsageTrend() {
  const days = RANGE_DAYS[range.value] ?? 30
  const usage = await usageApi.trends({ dimension: 'date', period: 'day' })
  const points = usage.series ?? []
  series.value = points.slice(Math.max(points.length - days, 0)) as unknown as Array<Record<string, unknown>>
  await nextTick()
  renderChart()
}

async function loadDashboard() {
  dashboard.value = await monitoringApi.dashboard(range.value)
}

async function loadRankings() {
  const costs = await monitoringApi.costs({ dimension: ['user'], time_range: range.value })
  rankings.value = (costs.dimensions.user ?? [])
    .slice(0, 5)
    .map((item) => ({ user: item.value || '未知', cost: Number(item.total_cost ?? 0) }))
}

async function load() {
  loading.value = true
  errorMessage.value = ''
  const results = await Promise.allSettled([loadDashboard(), loadUsageTrend(), loadRankings()])
  const failed = results.filter((item) => item.status === 'rejected')
  if (failed.length) {
    const first = (failed[0] as PromiseRejectedResult).reason
    errorMessage.value = errorText(first, '报表数据加载失败')
  }
  loading.value = false
}

watch(range, () => void load())

onMounted(async () => {
  await load()
})

onBeforeUnmount(() => {
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.page-toolbar { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.trend-chart { height: 320px; }
.kpi-label { font-size: 13px; color: var(--ob-text-secondary); }
.kpi-value { font-size: 22px; font-weight: 600; margin-top: 6px; }
.rank-badge { display: inline-flex; width: 24px; height: 24px; border-radius: 50%; background: #f1f5f9; align-items: center; justify-content: center; font-size: 13px; }
.rank-badge.top { background: #1677FF; color: #fff; }
</style>
