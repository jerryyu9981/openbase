<template>
  <PageContainer title="计费" description="用量统计、配额与账单（OpenLLM 计费服务）" test-id="billing-view-page">
    <div class="page-toolbar">
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        value-format="YYYY-MM-DD"
        data-test="billing-range"
      />
      <el-button type="primary" :loading="loading" data-test="billing-refresh" @click="loadAll">刷新</el-button>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="billing-error"
      @close="errorMessage = ''"
    />

    <el-row :gutter="16" class="mb-16">
      <el-col v-for="card in statCards" :key="card.label" :xs="12" :lg="6">
        <el-card shadow="hover" data-test="billing-stat">
          <div class="stat-label">{{ card.label }}</div>
          <div class="stat-value">{{ card.value }}</div>
          <div class="stat-sub">{{ card.sub }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :span="12">
        <el-card header="消费趋势" class="mb-16" data-test="billing-trend">
          <div v-loading="loading">
            <el-empty v-if="trendSeries.length === 0" description="该时间范围内暂无消费数据" :image-size="70" data-test="billing-trend-empty" />
            <div v-else ref="trendRef" class="chart" />
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card header="配额告警" class="mb-16" data-test="billing-alerts">
          <el-table :data="quotas" size="small" data-test="billing-quota-table">
            <template #empty>
              <el-empty description="暂无配额配置" :image-size="50" data-test="billing-quota-empty" />
            </template>
            <el-table-column prop="quota_type" label="资源" width="110" />
            <el-table-column label="用量" min-width="150">
              <template #default="{ row }">{{ row.used_amount }} / {{ row.quota_limit }}</template>
            </el-table-column>
            <el-table-column label="使用率" width="110">
              <template #default="{ row }">{{ Number(row.usage_percent ?? 0).toFixed(1) }}%</template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="row.is_exceeded ? 'danger' : 'success'" size="small">
                  {{ row.is_exceeded ? '已超限' : '正常' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-card header="账单列表" data-test="billing-invoices">
      <div v-loading="loading" class="ob-table-scroll">
        <el-table :data="bills" stripe data-test="billing-table">
          <template #empty>
            <el-empty description="暂无账单" :image-size="60" data-test="billing-empty" />
          </template>
          <el-table-column label="账期" width="220">
            <template #default="{ row }">{{ row.period_start }} ~ {{ row.period_end }}</template>
          </el-table-column>
          <el-table-column prop="total_requests" label="请求数" width="100" />
          <el-table-column label="Tokens" width="140">
            <template #default="{ row }">{{ row.total_tokens_input + row.total_tokens_output }}</template>
          </el-table-column>
          <el-table-column label="金额" width="140">
            <template #default="{ row }">{{ row.currency }} {{ Number(row.total_cost ?? 0).toFixed(2) }}</template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="billStatusType(row.status)" size="small">{{ billStatusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="notes" label="备注" min-width="160" show-overflow-tooltip />
          <el-table-column label="操作" width="90" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" data-test="billing-detail" @click="viewInvoice(row)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <el-dialog v-model="billDialogVisible" title="账单详情" width="560px" data-test="billing-detail-dialog">
      <el-descriptions v-if="selectedBill" :column="1" border>
        <el-descriptions-item label="账单 ID">{{ selectedBill.id }}</el-descriptions-item>
        <el-descriptions-item label="账期">{{ selectedBill.period_start }} ~ {{ selectedBill.period_end }}</el-descriptions-item>
        <el-descriptions-item label="请求数">{{ selectedBill.total_requests }}</el-descriptions-item>
        <el-descriptions-item label="输入 Tokens">{{ selectedBill.total_tokens_input }}</el-descriptions-item>
        <el-descriptions-item label="输出 Tokens">{{ selectedBill.total_tokens_output }}</el-descriptions-item>
        <el-descriptions-item label="金额">{{ selectedBill.currency }} {{ Number(selectedBill.total_cost ?? 0).toFixed(2) }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ billStatusLabel(selectedBill.status) }}</el-descriptions-item>
        <el-descriptions-item label="备注">{{ selectedBill.notes || '-' }}</el-descriptions-item>
        <el-descriptions-item label="明细">
          <pre class="detail-json">{{ JSON.stringify(selectedBill.details ?? {}, null, 2) }}</pre>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import {
  billingApi,
  usageApi,
  type LlmBill,
  type LlmBillingUsageStatistics,
  type LlmQuota,
  type LlmUsageTrendPoint,
} from '@/core/api/governance'

/**
 * 计费（v1.9.4 R4 真实化）：用量统计 `/billing/usage/statistics`、配额 `/billing/quotas`、
 * 账单 `/billing/bills`；消费趋势复用 `/usage/trends`（按天聚合）。
 * 租户范围由上游按当前身份的组织推导，非管理员仅能看到本组织数据。
 */
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

const dateRange = ref<[string, string]>([daysAgo(29), formatDate(new Date())])
const loading = ref(false)
const errorMessage = ref('')

const statistics = ref<LlmBillingUsageStatistics | null>(null)
const quotas = ref<LlmQuota[]>([])
const bills = ref<LlmBill[]>([])
const trendSeries = ref<LlmUsageTrendPoint[]>([])

const trendRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

const statCards = computed(() => {
  const data = statistics.value
  const tokens = (data?.total_tokens_input ?? 0) + (data?.total_tokens_output ?? 0)
  return [
    { label: '总请求数', value: String(data?.total_requests ?? 0), sub: '当前组织' },
    { label: '总 Tokens', value: String(tokens), sub: '输入 + 输出' },
    { label: '总费用($)', value: Number(data?.total_cost ?? 0).toFixed(2), sub: '所选区间' },
    { label: '平均延迟', value: `${Number(data?.average_latency_ms ?? 0).toFixed(0)} ms`, sub: '全部请求' },
  ]
})

function billStatusType(status: string) {
  return { paid: 'success', pending: 'warning', unpaid: 'warning', overdue: 'danger' }[status] || 'info'
}
function billStatusLabel(status: string) {
  return { paid: '已支付', pending: '待支付', unpaid: '待支付', overdue: '已逾期' }[status] || status
}

function renderTrend() {
  if (!trendRef.value || trendSeries.value.length === 0) return
  if (!chart) chart = echarts.init(trendRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 56, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: trendSeries.value.map((point) => point.date) },
    yAxis: { type: 'value' },
    series: [
      {
        name: '消费($)',
        type: 'line',
        smooth: true,
        areaStyle: { opacity: 0.15 },
        data: trendSeries.value.map((point) => Number(point.cost ?? 0)),
      },
    ],
  })
}

function handleResize() {
  chart?.resize()
}

async function loadAll() {
  errorMessage.value = ''
  const [start, end] = dateRange.value ?? []
  if (!start || !end) {
    errorMessage.value = '请选择统计时间范围'
    return
  }
  loading.value = true
  try {
    const [stats, quotaList, billList, trend] = await Promise.all([
      billingApi.usageStatistics({ start_date: start, end_date: end }),
      billingApi.quotas(),
      billingApi.bills(),
      usageApi.trends({ dimension: 'time', period: 'day', start_date: start, end_date: end }),
    ])
    statistics.value = stats
    quotas.value = quotaList
    bills.value = billList
    trendSeries.value = trend.series ?? []
    await nextTick()
    renderTrend()
  } catch (error) {
    errorMessage.value = `计费数据加载失败：${error instanceof Error ? error.message : '未知错误'}`
  } finally {
    loading.value = false
  }
}

const billDialogVisible = ref(false)
const selectedBill = ref<LlmBill | null>(null)

function viewInvoice(row: LlmBill) {
  selectedBill.value = row
  billDialogVisible.value = true
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
  void loadAll()
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
.stat-label {
  font-size: 13px;
  color: var(--ob-text-secondary);
}
.stat-value {
  font-size: 22px;
  font-weight: 600;
  margin: 4px 0;
}
.stat-sub {
  font-size: 12px;
  color: var(--ob-text-secondary);
}
.chart {
  height: 260px;
}
.detail-json {
  margin: 0;
  max-height: 220px;
  overflow: auto;
  font-size: 12px;
}
</style>
