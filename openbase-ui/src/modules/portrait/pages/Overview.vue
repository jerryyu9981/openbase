<template>
  <div v-loading="loading">
    <!-- 错误态 -->
    <el-alert v-if="errorMessage" type="error" show-icon closable class="mb-16" data-test="overview-error" @close="errorMessage = ''">
      <template #default>
        <span>{{ errorMessage }}</span>
        <el-button link type="primary" data-test="overview-retry" @click="loadOverview">重新加载</el-button>
      </template>
    </el-alert>

    <!-- TD-13-26 数据总览：顶部 KPI 卡片（深色卡片风格） -->
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

    <!-- ECharts 双图：画像类型分布（饼图）+ 画像数量趋势（折线图） -->
    <el-row :gutter="16" class="mb-16">
      <el-col :xs="24" :lg="10" class="chart-col">
        <el-card shadow="never" header="画像类型分布" data-test="overview-pie-card">
          <el-empty v-if="pieEmpty" description="暂无画像类型数据" :image-size="80" />
          <div v-else ref="pieRef" class="chart" />
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="14" class="chart-col">
        <el-card shadow="never" header="画像数量趋势（近 30 天）" data-test="overview-line-card">
          <el-empty v-if="lineEmpty" description="暂无趋势数据" :image-size="80" />
          <div v-else ref="lineRef" class="chart" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 最新画像列表 -->
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
          <el-table-column label="画像类型" width="110">
            <template #default="{ row }">
              <el-tag size="small">{{ row.portrait_type }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="标签" min-width="170">
            <template #default="{ row }">
              <el-tag v-for="tag in row.tags" :key="tag" size="small" class="tag-item" type="info">{{ tag }}</el-tag>
              <span v-if="!row.tags.length" class="text-secondary">—</span>
            </template>
          </el-table-column>
          <el-table-column prop="updated_at" label="更新时间" width="160" />
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

interface KpiCard {
  label: string
  value: string
  trend: string
  rate?: number
}

interface LatestPortrait {
  id: number
  name: string
  portrait_type: string
  tags: string[]
  updated_at: string
}

interface TrendData {
  dates: string[]
  counts: number[]
}

const loading = ref(true)
const errorMessage = ref('')
const trendData = ref<TrendData>({ dates: [], counts: [] })
const pieRef = ref<HTMLDivElement>()
const lineRef = ref<HTMLDivElement>()
let pieChart: echarts.ECharts | null = null
let lineChart: echarts.ECharts | null = null

/** 契约 mock：KPI 汇总数据，不调用真实 API */
const kpiData = { total: 955, weekly_new: 38, tag_total: 156, active_rate: 86.4, weekly_growth: '+12.4%' }

/** 契约 mock：画像类型分布 */
const portraitTypeDistribution = [
  { name: '基础画像', value: 420 },
  { name: '行为画像', value: 260 },
  { name: '偏好画像', value: 180 },
  { name: '组合画像', value: 95 },
]

/** 契约 mock：最新画像 5 条 */
const latestPortraits = ref<LatestPortrait[]>([
  { id: 1001, name: '张伟', portrait_type: '行为画像', tags: ['高频用户', 'RAG'], updated_at: '2026-08-26 09:12' },
  { id: 1002, name: '张敏', portrait_type: '偏好画像', tags: ['付费用户', '内容偏好'], updated_at: '2026-08-26 08:40' },
  { id: 1003, name: '李娜', portrait_type: '基础画像', tags: ['试用'], updated_at: '2026-08-25 18:05' },
  { id: 1004, name: '王强', portrait_type: '组合画像', tags: ['高频用户', '技术型'], updated_at: '2026-08-25 15:30' },
  { id: 1005, name: '刘洋', portrait_type: '基础画像', tags: ['试用', '夜间活跃'], updated_at: '2026-08-24 22:11' },
])

const kpiCards = computed<KpiCard[]>(() => [
  { label: '画像总数', value: String(kpiData.total), trend: `较上周 ${kpiData.weekly_growth}` },
  { label: '新增本周', value: String(kpiData.weekly_new), trend: '近 7 天新创建画像' },
  { label: '标签总数', value: String(kpiData.tag_total), trend: '画像/行为/偏好三类' },
  { label: '活跃画像率', value: `${kpiData.active_rate}%`, trend: '近 30 天活跃画像占比', rate: kpiData.active_rate },
])

const pieEmpty = computed(() => portraitTypeDistribution.length === 0)
const lineEmpty = computed(() => trendData.value.dates.length === 0)

function formatDate(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

/** 契约 mock：生成近 30 天画像数量趋势 */
function buildTrend(): TrendData {
  const dates: string[] = []
  const counts: number[] = []
  for (let index = 29; index >= 0; index -= 1) {
    const date = new Date()
    date.setDate(date.getDate() - index)
    dates.push(formatDate(date))
    const weekendBoost = index % 7 === 0 ? 15 : 0
    counts.push(12 + weekendBoost + Math.floor(Math.random() * 30))
  }
  return { dates, counts }
}

function renderCharts() {
  if (pieRef.value) {
    if (!pieChart) pieChart = echarts.init(pieRef.value)
    pieChart.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c}（{d}%）' },
      legend: { bottom: 0 },
      series: [
        {
          name: '画像类型',
          type: 'pie',
          radius: ['42%', '68%'],
          center: ['50%', '45%'],
          data: portraitTypeDistribution,
          label: { formatter: '{b} {d}%' },
        },
      ],
    })
  }
  if (lineRef.value) {
    if (!lineChart) lineChart = echarts.init(lineRef.value)
    lineChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 48, right: 16, top: 32, bottom: 28 },
      xAxis: { type: 'category', boundaryGap: false, data: trendData.value.dates },
      yAxis: { type: 'value' },
      series: [
        {
          name: '新增画像数',
          type: 'line',
          smooth: true,
          data: trendData.value.counts,
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

function mockDelay(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms))
}

async function loadOverview() {
  errorMessage.value = ''
  loading.value = true
  try {
    await mockDelay(400)
    trendData.value = buildTrend()
    await nextTick()
    renderCharts()
  } catch {
    errorMessage.value = '数据总览加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
  void loadOverview()
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
.tag-item { margin-right: 4px; }
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
