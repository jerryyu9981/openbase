<template>
  <PageContainer title="今日工作台" description="一屏回答：今天做什么、哪里有问题" test-id="overview-page">
    <!-- 顶部待办：四类计数，点击带筛选直达 -->
    <el-row :gutter="16" class="mb-16">
      <el-col v-for="card in todoCards" :key="card.key" :xs="12" :md="6" class="todo-col">
        <button
          type="button"
          class="todo-card"
          :class="`todo-card--${card.tone}`"
          data-test="overview-todo-card"
          @click="go(card.link)"
        >
          <span class="todo-card__label">{{ card.label }}</span>
          <span class="todo-card__value" data-test="overview-todo-value">
            {{ card.value === null ? '—' : card.value }}
          </span>
          <span class="todo-card__hint">{{ card.hint }}</span>
          <span class="todo-card__action">去处理 →</span>
        </button>
      </el-col>
    </el-row>

    <el-alert
      v-if="todoError"
      type="warning"
      show-icon
      :closable="false"
      class="mb-16"
      data-test="overview-todo-error"
      :title="todoError"
    >
      <el-button link type="primary" data-test="overview-todo-retry" @click="loadTodos">重试</el-button>
    </el-alert>

    <el-row :gutter="16" class="mb-16">
      <!-- 治理告警：局部降级，不阻断规模区块 -->
      <el-col :xs="24" :lg="14">
        <el-card shadow="never" data-test="overview-alerts-card">
          <template #header>
            <div class="card-header">
              <span>治理告警</span>
              <span class="muted sm">BLOCK {{ blockCount }} · WARN {{ warnCount }}</span>
            </div>
          </template>
          <el-alert
            v-if="alertError"
            type="warning"
            show-icon
            :closable="false"
            data-test="overview-alerts-error"
            :title="alertError"
          >
            <el-button link type="primary" @click="loadAlerts">重试</el-button>
          </el-alert>
          <template v-else>
            <div v-if="alertPartial" class="muted sm mb-8" data-test="overview-alerts-partial">{{ alertPartial }}</div>
            <el-empty
              v-if="!alerts.length && !alertsLoading"
              description="暂无治理告警"
              :image-size="70"
              data-test="overview-alerts-empty"
            />
            <ul v-else v-loading="alertsLoading" class="alert-list">
              <li v-for="alert in alerts" :key="alert.key" class="alert-item">
                <el-tag :type="alert.severity === 'BLOCK' ? 'danger' : 'warning'" size="small" effect="dark">
                  {{ alert.severity }}
                </el-tag>
                <div class="alert-main">
                  <div class="alert-title">{{ alert.title }}</div>
                  <div class="alert-object">{{ alert.object }}</div>
                </div>
                <el-button link type="primary" size="small" @click="go(alert.link)">去修复</el-button>
              </li>
            </ul>
          </template>
        </el-card>
      </el-col>

      <!-- 我的队列：按模板分组的待审核进度 -->
      <el-col :xs="24" :lg="10">
        <el-card shadow="never" data-test="overview-queue-card">
          <template #header>
            <div class="card-header">
              <span>我的队列</span>
              <span class="muted sm">待审核共 {{ pendingTotal === null ? '—' : pendingTotal }} 条</span>
            </div>
          </template>
          <el-empty
            v-if="pendingTotal === 0 && !queueLoading"
            description="今日暂无待办"
            :image-size="70"
            data-test="overview-queue-empty"
          >
            <el-button type="primary" @click="go({ path: '/portrait/dps/annotations' })">去录入标注</el-button>
          </el-empty>
          <ul v-else-if="queueGroups.length" v-loading="queueLoading" class="queue-list">
            <li v-for="group in queueGroups" :key="group.code" class="queue-item">
              <div class="queue-item__head">
                <NameCodeLabel :name="group.name" :code="group.code" />
                <span class="queue-item__count">{{ group.count }} / {{ pendingTotal || group.count }}</span>
              </div>
              <el-progress
                :percentage="group.percent"
                :show-text="false"
                :stroke-width="6"
                class="queue-item__bar"
              />
            </li>
            <li class="queue-more">
              <el-button link type="primary" @click="go({ path: '/portrait/dps/annotations', query: { view: 'review', status: 'pending' } })">
                进入审核收件箱 →
              </el-button>
            </li>
          </ul>
          <el-skeleton v-else-if="queueLoading" :rows="3" animated />
          <div v-else class="muted sm" data-test="overview-queue-unavailable">
            队列数据暂不可用{{ todoError ? '，请按上方提示重试' : '' }}
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 规模概览：保留既有 KPI 与图表；趋势窗口由接口固定为近 30 天 -->
    <el-card shadow="never" data-test="overview-scale-card">
      <template #header>
        <div class="card-header">
          <span>规模概览</span>
          <span class="muted sm">趋势窗口：近 30 天（接口固定，不做前端假数据切换）</span>
        </div>
      </template>
      <el-alert
        v-if="statsError"
        type="error"
        show-icon
        closable
        class="mb-12"
        data-test="overview-error"
        @close="statsError = ''"
      >
        <template #default>
          <span>{{ statsError }}</span>
          <el-button link type="primary" data-test="overview-retry" @click="loadScale">重新加载</el-button>
        </template>
      </el-alert>

      <el-row :gutter="16" class="mb-12">
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

      <el-row :gutter="16">
        <el-col :xs="24" :lg="10" class="chart-col">
          <el-card shadow="never" header="画像风险分布" data-test="overview-pie-card">
            <el-empty v-if="pieEmpty" description="暂无画像风险数据" :image-size="80" />
            <div v-show="!pieEmpty" ref="pieRef" class="chart" />
          </el-card>
        </el-col>
        <el-col :xs="24" :lg="14" class="chart-col">
          <el-card shadow="never" header="画像新增趋势（近 30 天）" data-test="overview-line-card">
            <el-empty v-if="lineEmpty" description="暂无趋势数据" :image-size="80" />
            <div v-show="!lineEmpty" ref="lineRef" class="chart" />
          </el-card>
        </el-col>
      </el-row>
    </el-card>

    <el-card shadow="never" data-test="overview-latest-card">
      <template #header>
        <div class="card-header">
          <span>最新画像</span>
          <el-button link type="primary" data-test="overview-view-all" @click="go({ path: '/portrait/list' })">查看全部</el-button>
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
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import NameCodeLabel from '@/components/common/NameCodeLabel.vue'
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter, type RouteLocationRaw } from 'vue-router'
import * as echarts from 'echarts'
import {
  dpsApi,
  type DpsAnnotationTemplate,
  type DpsOrphanAnnotationTemplate,
  type DpsPortrait,
  type DpsPortraitTemplate,
  type DpsScoringIssue,
} from '@/core/api/dps'
import { describeDpsError } from '@/core/api/error'

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
  avg_overall_score?: number
  high_risk_count?: number
  medium_risk_count?: number
  low_risk_count?: number
  risk_distribution?: Array<{ name: string; value: number }>
  trend?: Array<{ date: string; count: number }>
  [key: string]: unknown
}

interface TodoCard {
  key: string
  label: string
  tone: string
  value: number | null
  hint: string
  link: RouteLocationRaw
}

interface QueueGroup {
  code: string
  name: string
  count: number
  percent: number
}

interface GovernanceAlert {
  key: string
  severity: 'BLOCK' | 'WARN'
  title: string
  object: string
  link: RouteLocationRaw
}

const router = useRouter()

const statsError = ref('')
const overview = ref<OverviewStats>({})
const latestPortraits = ref<DpsPortrait[]>([])
const pieRef = ref<HTMLDivElement>()
const lineRef = ref<HTMLDivElement>()
let pieChart: echarts.ECharts | null = null
let lineChart: echarts.ECharts | null = null

const todoError = ref('')
const pendingTotal = ref<number | null>(null)
const rejectedTotal = ref<number | null>(null)
const queueGroups = ref<QueueGroup[]>([])
const queueLoading = ref(false)

const alerts = ref<GovernanceAlert[]>([])
const alertError = ref('')
const alertPartial = ref('')
const alertsLoading = ref(false)

const todoCards = computed<TodoCard[]>(() => [
  {
    key: 'entry',
    label: '待标注',
    tone: 'blue',
    value: null,
    hint: '主体待标注统计待 A1/A6 接口就绪；点击直接开始录入',
    link: { path: '/portrait/dps/annotations' },
  },
  {
    key: 'review',
    label: '待我审核',
    tone: 'amber',
    value: pendingTotal.value,
    hint: '当前按待审核总数展示（审核人维度待 A2 接口）',
    link: { path: '/portrait/dps/annotations', query: { view: 'review', status: 'pending' } },
  },
  {
    key: 'rework',
    label: '返修',
    tone: 'red',
    value: rejectedTotal.value,
    hint: '已驳回、需重新标注或补充证据',
    link: { path: '/portrait/dps/annotations', query: { status: 'rejected' } },
  },
  {
    key: 'ai',
    label: 'AI 待复核',
    tone: 'violet',
    value: null,
    hint: '候选尚未持久化（A14），前往复核页查看当前批次',
    link: { path: '/portrait/dps/annotation-adapters' },
  },
])

const blockCount = computed(() => alerts.value.filter((item) => item.severity === 'BLOCK').length)
const warnCount = computed(() => alerts.value.filter((item) => item.severity === 'WARN').length)

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

const pieEmpty = computed(() => !(overview.value.risk_distribution || []).some((item) => item.value > 0))
const lineEmpty = computed(() => !(overview.value.trend || []).some((item) => item.count > 0))

function go(link: RouteLocationRaw) {
  void router.push(link)
}

function riskOf(row: DpsPortrait): number {
  const raw = row.risk_level ?? row.risk_score
  const n = Number(raw)
  return Number.isFinite(n) ? n : -1
}

function riskLabel(row: DpsPortrait): string {
  const value = riskOf(row)
  if (value < 0) return '未知'
  if (value >= 70) return '高'
  if (value >= 40) return '中'
  return '低'
}

function riskType(row: DpsPortrait): 'success' | 'warning' | 'danger' | 'info' {
  const value = riskOf(row)
  if (value < 0) return 'info'
  if (value >= 70) return 'danger'
  if (value >= 40) return 'warning'
  return 'success'
}

function formatTime(value?: string) {
  if (!value) return '-'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false })
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
    pieChart.resize()
  }
  const trend = overview.value.trend || []
  if (lineRef.value) {
    if (!lineChart) lineChart = echarts.init(lineRef.value)
    lineChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 48, right: 16, top: 32, bottom: 28 },
      xAxis: { type: 'category', boundaryGap: false, data: trend.map((item) => item.date) },
      yAxis: { type: 'value', minInterval: 1 },
      series: [
        {
          name: '新增画像数',
          type: 'line',
          smooth: true,
          data: trend.map((item) => item.count),
          areaStyle: { opacity: 0.12 },
          itemStyle: { color: '#2563eb' },
        },
      ],
    })
    lineChart.resize()
  }
}

function handleResize() {
  pieChart?.resize()
  lineChart?.resize()
}

/** 待办与我的队列：现有队列接口聚合，失败仅该区块降级 */
async function loadTodos() {
  todoError.value = ''
  queueLoading.value = true
  pendingTotal.value = null
  rejectedTotal.value = null
  try {
    const [pending, rejected] = await Promise.all([
      dpsApi.listAnnotations({ review_status: 'pending', page: 1, page_size: 100 }),
      dpsApi.listAnnotations({ review_status: 'rejected', page: 1, page_size: 1 }),
    ])
    pendingTotal.value = Number(pending.total || 0)
    rejectedTotal.value = Number(rejected.total || 0)

    const grouped = new Map<string, { code: string; name: string; count: number }>()
    ;(pending.items || []).forEach((row) => {
      const code = row.annotation_template || 'unknown'
      const existing = grouped.get(code)
      if (existing) {
        existing.count += 1
      } else {
        grouped.set(code, {
          code,
          name: row.annotation_template_name || code,
          count: 1,
        })
      }
    })
    const total = pendingTotal.value || pending.items?.length || 0
    queueGroups.value = Array.from(grouped.values())
      .sort((left, right) => right.count - left.count)
      .map((group) => ({
        ...group,
        percent: total > 0 ? Math.min(100, Math.round((group.count / total) * 100)) : 0,
      }))
  } catch (err) {
    todoError.value = `待办与队列加载失败：${describeDpsError(err).detail}`
    queueGroups.value = []
  } finally {
    queueLoading.value = false
  }
}

/** 治理告警：四路数据并行，单路失败不阻断其余来源 */
async function loadAlerts() {
  alertError.value = ''
  alertPartial.value = ''
  alertsLoading.value = true
  const failures: string[] = []
  const next: GovernanceAlert[] = []
  try {
    const [consistency, orphans, annotationTemplates, portraitTemplates] = await Promise.allSettled([
      dpsApi.getScoringConsistency({ only_active: true, limit: 20 }),
      dpsApi.getOrphanAnnotationTemplates(),
      dpsApi.listAnnotationTemplates({ page: 1, page_size: 100 }),
      dpsApi.listTemplates({ page: 1, page_size: 100 }),
    ])

    if (consistency.status === 'fulfilled') {
      ;(consistency.value.issues || []).forEach((issue: DpsScoringIssue, index: number) => {
        next.push({
          key: `consistency-${issue.code}-${index}`,
          severity: issue.severity === 'BLOCK' ? 'BLOCK' : 'WARN',
          title: issue.message || issue.code,
          object: [
            issue.portrait_template ? `模板 ${issue.portrait_template}` : '',
            issue.annotation_template ? `标注模板 ${issue.annotation_template}` : '',
            issue.field_key ? `字段 ${issue.field_key}` : '',
          ]
            .filter(Boolean)
            .join(' · ') || '-',
          link: { path: '/portrait/dps/scoring-consistency' },
        })
      })
    } else {
      failures.push('口径体检')
    }

    if (orphans.status === 'fulfilled') {
      ;(orphans.value.items || []).forEach((item: DpsOrphanAnnotationTemplate) => {
        next.push({
          key: `orphan-${item.code}`,
          severity: 'WARN',
          title: `孤儿标注模板：${item.reason}`,
          object: [item.name, item.code, item.status].filter(Boolean).join(' · '),
          link: { path: '/portrait/dps/annotation-templates' },
        })
      })
    } else {
      failures.push('孤儿模板')
    }

    if (annotationTemplates.status === 'fulfilled' && portraitTemplates.status === 'fulfilled') {
      const ownerStatus = new Map<string, string>(
        (portraitTemplates.value.items || []).map((template: DpsPortraitTemplate) => [
          template.code,
          String(template.status || 'draft'),
        ]),
      )
      ;(annotationTemplates.value.items || []).forEach((template: DpsAnnotationTemplate) => {
        const ownerCode = template.template_code
        if (!ownerCode) return
        const status = ownerStatus.get(ownerCode)
        if (status === undefined || status !== 'active') {
          next.push({
            key: `owner-${template.code}`,
            severity: 'WARN',
            title: status === undefined ? '标注模板归属的画像模板不存在' : '标注模板归属的画像模板未激活',
            object: `${template.name || template.code} → ${ownerCode}`,
            link: { path: `/portrait/dps/annotation-templates/${encodeURIComponent(template.code)}/fields` },
          })
        }
      })
    } else {
      failures.push('模板归属')
    }

    alerts.value = next.slice(0, 12)
    if (failures.length && !next.length) {
      alertError.value = `治理告警加载失败：${failures.join('、')}`
    } else if (failures.length) {
      alertPartial.value = `部分治理数据加载失败：${failures.join('、')}`
    }
  } finally {
    alertsLoading.value = false
  }
}

/** 规模概览：保留原有汇总与图表 */
async function loadScale() {
  statsError.value = ''
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
    statsError.value = `规模概览加载失败：${describeDpsError(err).detail}`
  }
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
  void loadTodos()
  void loadAlerts()
  void loadScale()
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
.mb-12 { margin-bottom: 12px; }
.mb-8 { margin-bottom: 8px; }
.muted { color: var(--ob-text-secondary); }
.sm { font-size: 12px; }
.card-header { display: flex; justify-content: space-between; align-items: center; gap: 12px; }

.todo-col { margin-bottom: 16px; }
.todo-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  width: 100%;
  height: 100%;
  padding: 18px 20px;
  border: 1px solid var(--ob-border);
  border-radius: var(--ob-radius-lg);
  background: var(--ob-bg-card, #ffffff);
  cursor: pointer;
  text-align: left;
  transition: box-shadow 0.15s ease, transform 0.15s ease;
}
.todo-card:hover { box-shadow: var(--ob-shadow-md); transform: translateY(-1px); }
.todo-card:focus-visible { outline: 2px solid var(--ob-primary, #2563eb); outline-offset: 2px; }
.todo-card__label { font-size: 13px; color: var(--ob-text-secondary); }
.todo-card__value { font-size: 30px; font-weight: 700; line-height: 1.1; }
.todo-card__hint { font-size: 12px; color: var(--ob-text-secondary); line-height: 1.5; }
.todo-card__action { margin-top: auto; font-size: 12px; color: var(--ob-primary, #2563eb); }
.todo-card--blue { border-top: 3px solid #2563eb; }
.todo-card--amber { border-top: 3px solid #f59e0b; }
.todo-card--red { border-top: 3px solid #ef4444; }
.todo-card--violet { border-top: 3px solid #7c3aed; }

.alert-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 10px; }
.alert-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--ob-border);
}
.alert-item:last-child { border-bottom: none; padding-bottom: 0; }
.alert-main { flex: 1; min-width: 0; }
.alert-title { font-size: 13px; color: var(--ob-text-primary); line-height: 1.5; }
.alert-object { font-size: 12px; color: var(--ob-text-secondary); margin-top: 2px; word-break: break-all; }

.queue-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 14px; }
.queue-item__head { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.queue-item__count { font-size: 12px; color: var(--ob-text-secondary); white-space: nowrap; }
.queue-item__bar { margin-top: 6px; }
.queue-more { text-align: right; }

.kpi-col { margin-bottom: 12px; }
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
.chart { height: 300px; }
.chart-col { margin-bottom: 12px; }

@media (max-width: 767px) {
  .chart { height: 240px; }
}
</style>
