<template>
  <div class="audit-page">
    <div class="page-toolbar">
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始时间"
        end-placeholder="结束时间"
        value-format="YYYY-MM-DD HH:mm:ss"
        data-test="audit-range"
      />
      <el-select v-model="userFilter" placeholder="操作用户" clearable style="width: 140px" data-test="audit-user" />
      <el-select v-model="actionFilter" placeholder="操作类型" clearable style="width: 140px" data-test="audit-action">
        <el-option v-for="a in actionTypes" :key="a" :label="a" :value="a" />
      </el-select>
      <el-select v-model="resultFilter" placeholder="结果" clearable style="width: 110px" data-test="audit-result">
        <el-option label="成功" value="success" />
        <el-option label="失败" value="failed" />
      </el-select>
      <el-button type="primary" data-test="audit-query" @click="applyFilter">查询</el-button>
      <el-button :disabled="filteredRows.length === 0" data-test="audit-export" @click="exportCsv">导出</el-button>
    </div>

    <el-card header="审计日志" data-test="audit-card">
      <div class="ob-table-scroll">
        <el-table :data="pagedRows" stripe empty-text="暂无审计记录" data-test="audit-table">
          <el-table-column prop="time" label="时间" width="170" />
          <el-table-column prop="user" label="用户" width="110" />
          <el-table-column prop="action" label="操作" width="140" />
          <el-table-column prop="module" label="模块" width="100" />
          <el-table-column label="结果" width="90">
            <template #default="{ row }">
              <el-tag :type="row.result === 'success' ? 'success' : 'danger'" size="small">{{ row.result === 'success' ? '成功' : '失败' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="detail" label="详情" min-width="200" show-overflow-tooltip />
          <el-table-column label="操作" width="80">
            <template #default="{ row }">
              <el-button link type="primary" size="small" data-test="audit-detail" @click="openDetail(row)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="filteredRows.length"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        class="mt-8"
        data-test="audit-pagination"
      />
    </el-card>

    <!-- 异常检测报表 -->
    <el-card header="异常检测报表" class="mt-16" data-test="audit-report-card">
      <el-row :gutter="16">
        <el-col v-for="stat in anomalyStats" :key="stat.label" :span="8">
          <div class="stat-item">
            <div class="stat-label">{{ stat.label }}</div>
            <div class="stat-value">{{ stat.value }}</div>
            <el-tag :type="stat.trend > 0 ? 'danger' : 'success'" size="small">
              {{ stat.trend > 0 ? `+${stat.trend}%` : `${stat.trend}%` }} 较上周
            </el-tag>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 详情抽屉 -->
    <el-drawer v-model="detailOpen" title="审计详情" size="420px" data-test="audit-detail-drawer">
      <el-descriptions v-if="currentDetail" :column="1" border>
        <el-descriptions-item label="时间">{{ currentDetail.time }}</el-descriptions-item>
        <el-descriptions-item label="用户">{{ currentDetail.user }}</el-descriptions-item>
        <el-descriptions-item label="操作">{{ currentDetail.action }}</el-descriptions-item>
        <el-descriptions-item label="模块">{{ currentDetail.module }}</el-descriptions-item>
        <el-descriptions-item label="结果">{{ currentDetail.result }}</el-descriptions-item>
        <el-descriptions-item label="耗时">{{ currentDetail.duration }}ms</el-descriptions-item>
        <el-descriptions-item label="详情">{{ currentDetail.detail }}</el-descriptions-item>
      </el-descriptions>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

interface AuditRow {
  id: number
  time: string
  user: string
  action: string
  module: string
  result: 'success' | 'failed'
  detail: string
  duration: number
}

const mockLogs: AuditRow[] = [
  { id: 1, time: '2026-08-28 12:30:11', user: 'admin', action: 'model.deploy', module: 'openllm', result: 'success', detail: '部署模型 llama3-8b 到实例 10.0.0.5:8001', duration: 3420 },
  { id: 2, time: '2026-08-28 11:52:03', user: 'ops01', action: 'gateway.register', module: 'gateway', result: 'success', detail: '注册实例 openllm@10.0.0.5:8001', duration: 18 },
  { id: 3, time: '2026-08-28 10:14:47', user: 'dev01', action: 'config.update', module: 'openllm', result: 'failed', detail: '更新 proxy.openllm.instances 权限不足', duration: 5 },
  { id: 4, time: '2026-08-27 18:03:22', user: 'admin', action: 'user.disable', module: 'auth', result: 'success', detail: '禁用用户 dev03', duration: 12 },
  { id: 5, time: '2026-08-27 16:41:09', user: 'ops01', action: 'aggregate.execute', module: 'gateway', result: 'failed', detail: '聚合步骤 kbs 超时 2000ms', duration: 2013 },
  { id: 6, time: '2026-08-27 09:20:55', user: 'admin', action: 'billing.quota.update', module: 'openllm', result: 'success', detail: '调整租户 quota 至 5000000', duration: 30 },
]

const logs = ref<AuditRow[]>(mockLogs)
const dateRange = ref<[string, string] | null>(null)
const userFilter = ref('')
const actionFilter = ref('')
const resultFilter = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const detailOpen = ref(false)
const currentDetail = ref<AuditRow | null>(null)

const actionTypes = ['model.deploy', 'gateway.register', 'config.update', 'user.disable', 'aggregate.execute', 'billing.quota.update']

const filteredRows = computed(() =>
  logs.value.filter((r) => {
    const matchUser = !userFilter.value || r.user === userFilter.value
    const matchAction = !actionFilter.value || r.action === actionFilter.value
    const matchResult = !resultFilter.value || r.result === resultFilter.value
    return matchUser && matchAction && matchResult
  }),
)

const pagedRows = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredRows.value.slice(start, start + pageSize.value)
})

const anomalyStats = computed(() => {
  const total = logs.value.length
  const failed = logs.value.filter((r) => r.result === 'failed').length
  return [
    { label: '日志总量', value: total, trend: 12 },
    { label: '失败操作', value: failed, trend: 40 },
    { label: '平均耗时(ms)', value: Math.round(logs.value.reduce((s, r) => s + r.duration, 0) / Math.max(1, total)), trend: -5 },
  ]
})

function applyFilter() {
  currentPage.value = 1
}

function openDetail(row: AuditRow) {
  currentDetail.value = row
  detailOpen.value = true
}

function exportCsv() {
  const header = '时间,用户,操作,模块,结果,详情\n'
  const body = filteredRows.value.map((r) => [r.time, r.user, r.action, r.module, r.result, `"${r.detail}"`].join(',')).join('\n')
  const blob = new Blob([header + body], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'audit-logs.csv'
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; align-items: center; flex-wrap: wrap; }
.mt-8 { margin-top: 8px; }
.mt-16 { margin-top: 16px; }
.stat-item { text-align: center; padding: 12px; border: 1px solid #e5e7eb; border-radius: 8px; }
.stat-label { font-size: 13px; color: #6b7280; }
.stat-value { font-size: 24px; font-weight: 600; margin: 4px 0; }
</style>
