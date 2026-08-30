<template>
  <div class="billing-page">
    <el-row :gutter="16" class="mb-16">
      <el-col v-for="card in statCards" :key="card.label" :span="6">
        <el-card shadow="hover" data-test="billing-stat">
          <div class="stat-label">{{ card.label }}</div>
          <div class="stat-value">{{ card.value }}</div>
          <div class="stat-sub">{{ card.sub }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <!-- 消费趋势 -->
      <el-col :span="12">
        <el-card header="消费趋势" class="mb-16" data-test="billing-trend">
          <div ref="trendRef" class="chart" />
        </el-card>
      </el-col>
      <!-- 配额告警 -->
      <el-col :span="12">
        <el-card header="配额告警" class="mb-16" data-test="billing-alerts">
          <el-table :data="alerts" size="small" empty-text="暂无告警">
            <el-table-column prop="rule" label="规则" min-width="140" />
            <el-table-column prop="tenant" label="租户" width="100" />
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="row.triggered ? 'danger' : 'success'" size="small">{{ row.triggered ? '已触发' : '正常' }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 账单列表 -->
    <el-card header="账单列表" data-test="billing-invoices">
      <div class="ob-table-scroll">
        <el-table :data="invoices" stripe empty-text="暂无账单" data-test="billing-table">
          <el-table-column prop="period" label="账期" width="120" />
          <el-table-column prop="tenant" label="租户" width="120" />
          <el-table-column prop="amount" label="金额(¥)" width="120" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === 'paid' ? 'success' : 'warning'" size="small">{{ row.status === 'paid' ? '已支付' : '待支付' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="detail" label="明细" min-width="180" />
          <el-table-column label="操作" width="90">
            <template #default="{ row }">
              <el-button link type="primary" size="small" data-test="billing-detail" @click="viewInvoice(row)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'

const statCards = ref([
  { label: '账户余额', value: '¥ 12,580.00', sub: '上次充值 08-20' },
  { label: '本月消费', value: '¥ 8,432.50', sub: '环比 +12.4%' },
  { label: '预估下月', value: '¥ 9,100.00', sub: '基于用量趋势' },
  { label: '待支付', value: '¥ 2,310.00', sub: '2 张账单' },
])

const alerts = ref([
  { rule: '余额 < 1000 元告警', tenant: '模型组', triggered: false },
  { rule: '月消费超预算 80%', tenant: 'AI 平台部', triggered: true },
  { rule: '配额使用率 > 90%', tenant: '模型组', triggered: false },
])

const invoices = ref([
  { period: '2026-08', tenant: 'AI 平台部', amount: 5320.0, status: 'unpaid', detail: '模型调用 + 存储 + 网关' },
  { period: '2026-08', tenant: '模型组', amount: 3112.5, status: 'paid', detail: '模型调用 + GPU' },
  { period: '2026-07', tenant: 'AI 平台部', amount: 4980.0, status: 'paid', detail: '模型调用 + 存储' },
])

const trendRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

function renderTrend() {
  if (!trendRef.value) return
  if (!chart) chart = echarts.init(trendRef.value)
  const months = ['3月', '4月', '5月', '6月', '7月', '8月']
  const values = [3200, 4100, 3800, 5600, 7500, 8432]
  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 50, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: months },
    yAxis: { type: 'value' },
    series: [{ name: '消费(¥)', type: 'line', smooth: true, areaStyle: { opacity: 0.15 }, data: values }],
  })
}

function viewInvoice(row: { period: string; tenant: string; amount: number }) {
  ElMessage.success(`账单详情：${row.period} ${row.tenant} ¥${row.amount.toFixed(2)}`)
}

onMounted(() => nextTick(renderTrend))
onBeforeUnmount(() => {
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.stat-label { font-size: 13px; color: #6b7280; }
.stat-value { font-size: 22px; font-weight: 600; margin: 4px 0; }
.stat-sub { font-size: 12px; color: #9ca3af; }
.chart { height: 260px; }
</style>
