<template>
  <div class="tool-monitor">
    <div class="page-toolbar">
      <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 130px" data-test="tc-status">
        <el-option label="执行中" value="running" />
        <el-option label="成功" value="success" />
        <el-option label="失败" value="failed" />
        <el-option label="已取消" value="cancelled" />
      </el-select>
      <el-date-picker v-model="timeRange" type="datetimerange" range-separator="至" data-test="tc-range" />
      <el-button type="primary" data-test="tc-query" @click="applyFilter">查询</el-button>
      <el-button :loading="refreshing" data-test="tc-refresh" @click="load">刷新</el-button>
    </div>

    <el-card header="工具调用记录" data-test="tc-card">
      <div class="ob-table-scroll">
        <el-table :data="pagedRows" stripe empty-text="暂无调用记录" data-test="tc-table">
          <el-table-column prop="time" label="时间" width="170" />
          <el-table-column prop="model" label="模型" width="130" />
          <el-table-column prop="tool" label="工具" width="120" />
          <el-table-column prop="duration" label="耗时(ms)" width="100" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" size="small" data-test="tc-status-badge">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150">
            <template #default="{ row }">
              <el-button link type="primary" size="small" data-test="tc-detail" @click="openDetail(row)">调用链</el-button>
              <el-button v-if="row.status === 'running'" link type="danger" size="small" data-test="tc-cancel" @click="cancel(row)">取消执行</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <el-pagination
        v-model:current-page="currentPage"
        :total="filteredRows.length"
        :page-size="pageSize"
        layout="total, prev, pager, next"
        class="mt-8"
      />
    </el-card>

    <!-- 调用链详情 -->
    <el-drawer v-model="detailOpen" title="工具调用链" size="440px" data-test="tc-detail-drawer">
      <template v-if="currentDetail">
        <el-timeline data-test="tc-chain">
          <el-timeline-item v-for="(node, idx) in currentDetail.chain" :key="idx" :timestamp="node.time" :type="node.status === 'success' ? 'success' : node.status === 'running' ? 'primary' : 'danger'">
            <div class="chain-node">
              <div>{{ node.step }}</div>
              <pre class="chain-body">{{ JSON.stringify(node.body, null, 2) }}</pre>
            </div>
          </el-timeline-item>
        </el-timeline>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'

type CallStatus = 'running' | 'success' | 'failed' | 'cancelled'

interface CallRecord {
  id: number
  time: string
  model: string
  tool: string
  duration: number
  status: CallStatus
  chain: Array<{ step: string; time: string; status: string; body: Record<string, unknown> }>
}

const mockCalls: CallRecord[] = [
  { id: 1, time: '2026-08-28 13:40:12', model: 'qwen2-7b', tool: 'web_search', duration: 812, status: 'success', chain: [
    { step: '模型发起工具调用', time: '13:40:12', status: 'success', body: { tool: 'web_search', args: { query: 'OpenBase 网关' } } },
    { step: '工具执行', time: '13:40:13', status: 'success', body: { hits: 5, elapsed_ms: 690 } },
  ]},
  { id: 2, time: '2026-08-28 13:38:05', model: 'llama3-8b', tool: 'db_query', duration: 3200, status: 'running', chain: [
    { step: '模型发起工具调用', time: '13:38:05', status: 'success', body: { tool: 'db_query', args: { sql: 'SELECT * FROM kb_docs' } } },
    { step: '数据库查询', time: '13:38:06', status: 'running', body: { executing: true } },
  ]},
  { id: 3, time: '2026-08-28 13:30:44', model: 'chatglm3-6b', tool: 'calc', duration: 23, status: 'failed', chain: [
    { step: '模型发起工具调用', time: '13:30:44', status: 'success', body: { tool: 'calc', args: { expr: '2**1000' } } },
    { step: '安全沙箱拒绝', time: '13:30:44', status: 'failed', body: { reason: 'expression exceeds safety limit' } },
  ]},
]

const calls = ref<CallRecord[]>(mockCalls)
const statusFilter = ref('')
const timeRange = ref<[Date, Date] | null>(null)
const currentPage = ref(1)
const pageSize = 10
const detailOpen = ref(false)
const currentDetail = ref<CallRecord | null>(null)
const refreshing = ref(false)

const filteredRows = computed(() =>
  statusFilter.value ? calls.value.filter((c) => c.status === statusFilter.value) : calls.value,
)
const pagedRows = computed(() => filteredRows.value.slice(0, pageSize))

function applyFilter() {
  currentPage.value = 1
}

function load() {
  refreshing.value = true
  setTimeout(() => {
    refreshing.value = false
    ElMessage.success('刷新完成')
  }, 400)
}

function statusType(s: CallStatus) {
  return { running: 'warning', success: 'success', failed: 'danger', cancelled: 'info' }[s] as 'warning' | 'success' | 'danger' | 'info'
}

function statusLabel(s: CallStatus) {
  return { running: '执行中', success: '成功', failed: '失败', cancelled: '已取消' }[s]
}

function openDetail(row: CallRecord) {
  currentDetail.value = row
  detailOpen.value = true
}

function cancel(row: CallRecord) {
  row.status = 'cancelled'
  row.chain.push({ step: '人工取消执行', time: new Date().toLocaleTimeString('zh-CN'), status: 'cancelled', body: { reason: 'operator cancelled' } })
  ElMessage.success('已发送取消指令')
}
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; align-items: center; flex-wrap: wrap; }
.mt-8 { margin-top: 8px; }
.chain-node { margin-bottom: 8px; }
.chain-body { background: #f6f8fa; border-radius: 6px; padding: 8px; font-size: 12px; margin-top: 6px; }
</style>
