<template>
  <PageContainer title="链路追踪" description="请求级链路与 Span 明细（OpenLLM Trace 服务）" test-id="traces-page">
    <div class="page-toolbar">
      <el-select v-model="range" style="width: 140px" data-test="trace-range" @change="loadStatistics">
        <el-option v-for="item in TIME_RANGES" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
      <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width: 140px" data-test="trace-status-filter">
        <el-option label="进行中" value="running" />
        <el-option label="成功" value="success" />
        <el-option label="错误" value="error" />
        <el-option label="超时" value="timeout" />
        <el-option label="已取消" value="cancelled" />
      </el-select>
      <el-input v-model="modelFilter" placeholder="模型筛选" clearable style="width: 180px" data-test="trace-model-filter" />
      <el-button type="primary" :loading="loading" data-test="trace-query" @click="reload">查询</el-button>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="traces-error"
      @close="errorMessage = ''"
    />

    <el-row :gutter="16">
      <el-col v-for="card in statCards" :key="card.label" :xs="12" :lg="4">
        <el-card class="stat-card" data-test="trace-stat">
          <div class="stat-label">{{ card.label }}</div>
          <div class="stat-value" :style="card.danger ? 'color: var(--el-color-danger)' : ''">{{ card.value }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="mt-16" header="追踪列表" data-test="trace-table-card">
      <div v-loading="loading" class="ob-table-scroll">
        <el-table :data="traces" stripe data-test="trace-table">
          <template #empty>
            <el-empty description="该时间范围内暂无追踪记录" :image-size="60" data-test="traces-empty" />
          </template>
          <el-table-column label="开始时间" width="170">
            <template #default="{ row }">{{ formatTime(row.start_time || row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="模型" min-width="150">
            <template #default="{ row }">{{ row.model || '-' }}</template>
          </el-table-column>
          <el-table-column label="提供商" width="120">
            <template #default="{ row }">{{ row.provider || '-' }}</template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="延迟(ms)" width="110">
            <template #default="{ row }">{{ row.latency_ms ?? '-' }}</template>
          </el-table-column>
          <el-table-column prop="span_count" label="Span" width="80" />
          <el-table-column label="Token" width="100">
            <template #default="{ row }">{{ row.tokens_total ?? 0 }}</template>
          </el-table-column>
          <el-table-column label="成本($)" width="100">
            <template #default="{ row }">{{ Number(row.cost ?? 0).toFixed(6) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="90" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" data-test="trace-detail" @click="openDetail(row)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        class="pagination"
        data-test="trace-pagination"
        @current-change="loadTraces"
        @size-change="reload"
      />
    </el-card>

    <el-drawer v-model="detailVisible" title="追踪详情" size="720px" data-test="trace-detail-drawer">
      <div v-loading="detailLoading">
        <el-descriptions v-if="detail" :column="2" border data-test="trace-detail-meta">
          <el-descriptions-item label="Trace ID" :span="2">{{ detail.trace_id }}</el-descriptions-item>
          <el-descriptions-item label="模型">{{ detail.model || '-' }}</el-descriptions-item>
          <el-descriptions-item label="提供商">{{ detail.provider || '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusType(detail.status)" size="small">{{ statusLabel(detail.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="延迟">{{ detail.latency_ms ?? '-' }} ms</el-descriptions-item>
          <el-descriptions-item label="Token">{{ detail.tokens_total ?? 0 }}</el-descriptions-item>
          <el-descriptions-item label="成本">${{ Number(detail.cost ?? 0).toFixed(6) }}</el-descriptions-item>
          <el-descriptions-item label="开始时间">{{ formatTime(detail.start_time) }}</el-descriptions-item>
          <el-descriptions-item label="结束时间">{{ formatTime(detail.end_time) }}</el-descriptions-item>
          <el-descriptions-item v-if="detail.error_message" label="错误信息" :span="2">
            {{ detail.error_message }}
          </el-descriptions-item>
        </el-descriptions>

        <h4 class="span-title">Span 明细</h4>
        <el-table :data="detail?.spans ?? []" size="small" stripe data-test="trace-span-table">
          <template #empty>
            <el-empty description="该追踪无 Span 明细" :image-size="50" />
          </template>
          <el-table-column prop="name" label="名称" min-width="160" />
          <el-table-column prop="kind" label="类型" width="110" />
          <el-table-column label="耗时(ms)" width="100">
            <template #default="{ row }">{{ row.duration_ms ?? '-' }}</template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="row.status === 'error' ? 'danger' : 'success'" size="small">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status_message" label="状态消息" min-width="160" show-overflow-tooltip />
        </el-table>
      </div>
    </el-drawer>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { computed, onMounted, ref } from 'vue'
import { tracesApi, type LlmTrace, type LlmTraceDetail, type LlmTraceStatistics } from '@/core/api/governance'

/**
 * 链路追踪（v1.9.4 R4 新增）：替换原 GenericPage 占位。
 * 数据源：`/api/v1/monitoring/traces`、`/monitoring/traces/statistics`、`/monitoring/traces/{trace_id}`。
 * 分页与筛选均由服务端完成，租户过滤由上游按当前身份（JWT/API Key 用户）组织推导。
 */
const TIME_RANGES = [
  { value: '1h', label: '1 小时' },
  { value: '6h', label: '6 小时' },
  { value: '24h', label: '24 小时' },
  { value: '7d', label: '7 天' },
  { value: '30d', label: '30 天' },
]

const range = ref('24h')
const statusFilter = ref('')
const modelFilter = ref('')
const loading = ref(false)
const errorMessage = ref('')

const statistics = ref<LlmTraceStatistics | null>(null)
const traces = ref<LlmTrace[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const detailVisible = ref(false)
const detailLoading = ref(false)
const detail = ref<LlmTraceDetail | null>(null)

const statCards = computed(() => [
  { label: '总请求', value: statistics.value?.total_count ?? 0, danger: false },
  { label: '成功', value: statistics.value?.success_count ?? 0, danger: false },
  { label: '错误', value: statistics.value?.error_count ?? 0, danger: (statistics.value?.error_count ?? 0) > 0 },
  { label: '错误率', value: `${Number(statistics.value?.error_rate ?? 0).toFixed(2)}%`, danger: (statistics.value?.error_rate ?? 0) > 1 },
  { label: '平均延迟', value: `${Number(statistics.value?.avg_latency_ms ?? 0).toFixed(0)} ms`, danger: false },
  { label: '成本($)', value: Number(statistics.value?.total_cost ?? 0).toFixed(2), danger: false },
])

function statusType(status: string) {
  return { running: 'warning', success: 'success', error: 'danger', timeout: 'warning', cancelled: 'info' }[status] || 'info'
}
function statusLabel(status: string) {
  return { running: '进行中', success: '成功', error: '错误', timeout: '超时', cancelled: '已取消' }[status] || status
}
function formatTime(value: string | null | undefined) {
  if (!value) return '-'
  return value.replace('T', ' ').slice(0, 19)
}

async function loadStatistics() {
  try {
    statistics.value = await tracesApi.statistics(range.value)
  } catch (error) {
    errorMessage.value = `追踪统计加载失败：${error instanceof Error ? error.message : '未知错误'}`
  }
}

async function loadTraces() {
  loading.value = true
  try {
    const result = await tracesApi.list({
      status: statusFilter.value || undefined,
      model: modelFilter.value.trim() || undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    traces.value = result.traces
    total.value = result.total
  } catch (error) {
    errorMessage.value = `追踪列表加载失败：${error instanceof Error ? error.message : '未知错误'}`
  } finally {
    loading.value = false
  }
}

function reload() {
  errorMessage.value = ''
  page.value = 1
  void Promise.all([loadStatistics(), loadTraces()])
}

async function openDetail(row: LlmTrace) {
  detailVisible.value = true
  detailLoading.value = true
  detail.value = null
  try {
    detail.value = await tracesApi.detail(row.trace_id)
  } catch (error) {
    errorMessage.value = `追踪详情加载失败：${error instanceof Error ? error.message : '未知错误'}`
    detailVisible.value = false
  } finally {
    detailLoading.value = false
  }
}

onMounted(reload)
</script>

<style scoped>
.mb-16 {
  margin-bottom: 16px;
}
.mt-16 {
  margin-top: 16px;
}
.stat-card {
  text-align: center;
}
.stat-label {
  color: var(--ob-text-secondary);
  font-size: 13px;
}
.stat-value {
  font-size: 20px;
  font-weight: 600;
  margin-top: 6px;
}
.pagination {
  margin-top: 12px;
  justify-content: flex-end;
}
.span-title {
  margin: 20px 0 10px;
}
</style>
