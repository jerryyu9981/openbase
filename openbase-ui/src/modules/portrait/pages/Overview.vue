<template>
  <div v-loading="loading">
    <!-- 错误态 -->
    <el-alert v-if="errorMessage" type="error" show-icon closable class="mb-16" data-test="overview-error" @close="errorMessage = ''">
      <template #default>
        <span>{{ errorMessage }}</span>
        <el-button link type="primary" data-test="overview-retry" @click="loadData">重新加载</el-button>
      </template>
    </el-alert>

    <!-- 数据总览：KPI 卡片（真实 dps-proxy 数据，与画像列表同源） -->
    <el-row :gutter="16" class="mb-16">
      <el-col v-for="kpi in kpiCards" :key="kpi.label" :xs="12" :sm="12" :md="6" class="kpi-col">
        <div class="kpi-card" data-test="overview-kpi-card">
          <div class="kpi-label">{{ kpi.label }}</div>
          <div class="kpi-value">{{ kpi.value }}</div>
          <el-progress
            v-if="kpi.rate !== undefined"
            :percentage="kpi.rate"
            :show-text="false"
            :stroke-width="6"
            class="kpi-progress"
            data-test="overview-kpi-progress"
          />
          <div v-else class="kpi-trend">{{ kpi.trend }}</div>
        </div>
      </el-col>
    </el-row>

    <!-- ECharts 双图：风险分布（饼图）+ 近 30 天新增趋势（折线图） -->
    <el-row :gutter="16" class="mb-16">
      <el-col :xs="24" :lg="10" class="chart-col">
        <el-card shadow="never" header="画像风险分布" data-test="overview-pie-card">
          <el-empty v-if="pieEmpty" description="暂无画像风险数据" :image-size="80" />
          <div v-else ref="pieRef" class="chart" />
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="14" class="chart-col">
        <el-card shadow="never" header="画像新增趋势（近 30 天）" data-test="overview-line-card">
          <el-empty v-if="lineEmpty" description="暂无趋势数据" :image-size="80" />
          <div v-else ref="lineRef" class="chart" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 最新画像列表（真实 /dps-proxy/portraits 分页数据） -->
    <el-card shadow="never" data-test="overview-latest-card">
      <template #header>
        <div class="card-header">
          <span>最新画像</span>
          <el-button link type="primary" data-test="overview-view-all" @click="$router.push('/portrait/list')">查看全部</el-button>
        </div>
      </template>
      <div class="ob-table-scroll">
        <el-table :data="latestPortraits" stripe data-test="overview-latest-table">
          <el-table-column prop="name" label="姓名" min-width="110" />
          <el-table-column prop="person_id" label="画像 ID" min-width="180" show-overflow-tooltip />
          <el-table-column label="风险等级" width="110">
            <template #default="{ row }">
              <el-tag :type="riskType(row)" size="small">{{ riskLabel(row) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="overall_score" label="综合分" width="90" />
          <el-table-column label="更新时间" width="170">
            <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
          </el-table-column>
          <template #empty>
            <el-empty description="暂无画像数据" :image-size="80" />
          </template>
        </el-table>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { dpsApi, type DpsPortrait } from '@/core/api/dps'

interface KpiCard {
  label: string
  value: string
  trend: string
  rate?: number
}

interface OverviewStats {
  total_profiles?: number
  today_new?: number
  active_profiles?: number
  inactive_profiles?: number
  avg_overall_score?: number
  high_risk_count?: number
  medium_risk_count?: number
  low_risk_count?: number
  risk_distribution?: Array<{ name: string; value: number }>
  trend?: Array<{ date: string; count: number }>
  [key: string]: unknown
}

const loading = ref(true)
const errorMessage = ref('')
const overview = ref<OverviewStats>({})
const latestPortraits = ref<DpsPortrait[]>([])
const pieRef = ref<HTMLDivElement>()
const lineRef = ref<HTMLDivElement>()
let pieChart: echarts.ECharts | null = null
let lineChart: echarts.ECharts | null = null

const kpiCards = computed<KpiCard[]>(() => {
  const stats = overview.value
  const total = stats.total_profiles ?? 0
  const active = stats.active_profiles ?? 0
  const activeRate = total > 0 ? Math.round((active / total) * 1000) / 10 : 0
  return [
    { label: '画像总数', value: String(total), trend: `平均综合分 ${stats.avg_overall_score ?? '-'}` },
    { label: '今日新增', value: String(stats.today_new ?? 0), trend: '当日创建画像' },
    { label: '高风险画像', value: String(stats.high_risk_count ?? 0), trend: `中风险 ${stats.medium_risk_count ?? 0} / 低风险 ${stats.low_risk_count ?? 0}` },
    { label: '活跃画像率', value: `${activeRate}%`, trend: `近 30 天活跃 ${active} 人`, rate: activeRate },
  ]
})

const pieEmpty = computed(() => !(overview.value.risk_distribution || []).some((d) => d.value > 0))
const lineEmpty = computed(() => !(overview.value.trend || []).some((d) => d.count > 0))

function riskOf(row: DpsPortrait): number {
  const raw = row.risk_level ?? row.risk_score
  const n = Number(raw)
  return Number.isFinite(n) ? n : -1
}

function riskLabel(row: DpsPortrait): string {
  const v = riskOf(row)
  if (v < 0) return '未知'
  if (v >= 70) return '高'
  if (v >= 40) return '中'
  return '低'
}

function riskType(row: DpsPortrait): 'success' | 'warning' | 'danger' | 'info' {
  const v = riskOf(row)
  if (v < 0) return 'info'
  if (v >= 70) return 'danger'
  if (v >= 40) return 'warning'
  return 'success'
}

function formatTime(v?: string) {
  if (!v) return '-'
  const d = new Date(v)
  return Number.isNaN(d.getTime()) ? v : d.toLocaleString('zh-CN', { hour12: false })
}

function renderCharts() {
  const distribution = overview.value.risk_distribution || []
  if (pieRef.value) {
    if (!pieChart) pieChart = echarts.init(pieRef.value)
    pieChart.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c}（{d}%）' },
      legend: { bottom: 0 },
      color: ['#ef4444', '#f59e0b', '#10b981'],
      series: [
        {
          name: '风险分布',
          type: 'pie',
          radius: ['42%', '68%'],
          center: ['50%', '45%'],
          data: distribution,
          label: { formatter: '{b} {d}%' },
        },
      ],
    })
  }
  const trend = overview.value.trend || []
  if (lineRef.value) {
    if (!lineChart) lineChart = echarts.init(lineRef.value)
    lineChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 48, right: 16, top: 32, bottom: 28 },
      xAxis: { type: 'category', boundaryGap: false, data: trend.map((t) => t.date) },
      yAxis: { type: 'value', minInterval: 1 },
      series: [
        {
          name: '新增画像数',
          type: 'line',
          smooth: true,
          data: trend.map((t) => t.count),
          areaStyle: { opacity: 0.12 },
          itemStyle: { color: '#2563eb' },
        },
      ],
    })
  }
}

function handleResize() {
  pieChart?.resize()
  lineChart?.resize()
}

async function loadData() {
  errorMessage.value = ''
  loading.value = true
  try {
    const [stats, list] = await Promise.all([
      dpsApi.getReportsOverview(),
      dpsApi.listPortraits({ page: 1, page_size: 5 }),
    ])
    overview.value = (stats || {}) as OverviewStats
    latestPortraits.value = list.items || []
    await nextTick()
    renderCharts()
  } catch (err) {
    errorMessage.value = `数据总览加载失败：${(err as Error).message || '网络错误'}`
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
  void loadData()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  pieChart?.dispose()
  pieChart = null
  lineChart?.dispose()
  lineChart = null
})
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.text-secondary { color: var(--ob-text-secondary); }
.kpi-col { margin-bottom: 16px; }
.kpi-card {
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  border-radius: var(--ob-radius-lg);
  padding: 20px 22px;
  box-shadow: var(--ob-shadow-md);
  height: 100%;
}
.kpi-label { color: #94a3b8; font-size: 13px; }
.kpi-value { color: #ffffff; font-size: 30px; font-weight: 700; margin: 10px 0 12px; }
.kpi-trend { color: #64748b; font-size: 12px; }
.kpi-progress { margin-top: 4px; }
.chart { height: 320px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
@media (max-width: 767px) {
  .chart { height: 260px; }
}
</style>
