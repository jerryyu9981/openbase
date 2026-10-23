<template>
  <PageContainer title="工具调用监控" description="工具调用记录与输入输出（OpenLLM Tool Call）" test-id="tool-call-monitor-view-page">
    <div class="page-toolbar">
      <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 130px" data-test="tc-status">
        <el-option label="待执行" value="pending" />
        <el-option label="执行中" value="running" />
        <el-option label="成功" value="success" />
        <el-option label="失败" value="failed" />
      </el-select>
      <el-input v-model="toolNameFilter" placeholder="工具名筛选" clearable style="width: 180px" data-test="tc-tool-filter" />
      <el-button type="primary" data-test="tc-query" @click="reload">查询</el-button>
      <el-button :loading="refreshing" data-test="tc-refresh" @click="load">刷新</el-button>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="tc-error"
      @close="errorMessage = ''"
    />

    <el-card header="工具调用记录" data-test="tc-card">
      <div v-loading="refreshing" class="ob-table-scroll">
        <el-table :data="calls" stripe data-test="tc-table">
          <template #empty>
            <el-empty description="暂无调用记录" :image-size="60" data-test="tc-empty" />
          </template>
          <el-table-column label="时间" width="170">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column prop="tool_name" label="工具" min-width="150" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" size="small" data-test="tc-status-badge">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="token_count" label="Token" width="100" />
          <el-table-column label="耗时(ms)" width="110">
            <template #default="{ row }">{{ row.latency_ms ?? '-' }}</template>
          </el-table-column>
          <el-table-column prop="error_message" label="错误" min-width="180" show-overflow-tooltip />
          <el-table-column label="操作" width="90" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" data-test="tc-detail" @click="openDetail(row)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        class="mt-8"
        data-test="tc-pagination"
        @current-change="load"
        @size-change="reload"
      />
    </el-card>

    <el-drawer v-model="detailOpen" title="工具调用详情" size="560px" data-test="tc-detail-drawer">
      <div v-loading="detailLoading">
        <el-descriptions v-if="currentDetail" :column="1" border>
          <el-descriptions-item label="调用 ID">{{ currentDetail.id }}</el-descriptions-item>
          <el-descriptions-item label="工具">{{ currentDetail.tool_name }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ statusLabel(currentDetail.status) }}</el-descriptions-item>
          <el-descriptions-item label="插件">{{ currentDetail.plugin_id }}</el-descriptions-item>
          <el-descriptions-item label="会话">{{ currentDetail.conversation_id || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Token">{{ currentDetail.token_count }}</el-descriptions-item>
          <el-descriptions-item label="耗时">{{ currentDetail.latency_ms }} ms</el-descriptions-item>
          <el-descriptions-item label="开始时间">{{ formatTime(currentDetail.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="完成时间">{{ formatTime(currentDetail.completed_at) }}</el-descriptions-item>
          <el-descriptions-item v-if="currentDetail.error_message" label="错误">
            {{ currentDetail.error_message }}
          </el-descriptions-item>
        </el-descriptions>
        <template v-if="currentDetail">
          <div class="json-title">输入参数</div>
          <pre class="json-body" data-test="tc-input">{{ JSON.stringify(currentDetail.input_params ?? {}, null, 2) }}</pre>
          <div class="json-title">输出结果</div>
          <pre class="json-body" data-test="tc-output">{{ JSON.stringify(currentDetail.output_result ?? {}, null, 2) }}</pre>
        </template>
      </div>
    </el-drawer>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { onMounted, ref } from 'vue'
import { toolCallsApi, type LlmToolCall } from '@/core/api/governance'

/**
 * 工具调用监控（v1.9.5 R5 真实化）：`/tool-calls` 列表（状态/工具名筛选 + 服务端分页）
 * 与 `/tool-calls/{id}` 详情。原「调用链时间线」「取消执行」为 mock：上游取消能力作用于
 * 调用链（`/tool-calls/chains/{id}/cancel`），单条工具调用无取消端点，故本轮移除。
 */
const statusFilter = ref('')
const toolNameFilter = ref('')
const refreshing = ref(false)
const errorMessage = ref('')

const calls = ref<LlmToolCall[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

const detailOpen = ref(false)
const detailLoading = ref(false)
const currentDetail = ref<LlmToolCall | null>(null)

function statusType(status: string) {
  return { pending: 'info', running: 'warning', success: 'success', failed: 'danger' }[status] || 'info'
}
function statusLabel(status: string) {
  return { pending: '待执行', running: '执行中', success: '成功', failed: '失败' }[status] || status
}
function formatTime(value: string | null) {
  if (!value) return '-'
  return value.replace('T', ' ').slice(0, 19)
}

async function load() {
  refreshing.value = true
  errorMessage.value = ''
  try {
    const page = await toolCallsApi.list({
      status: statusFilter.value || undefined,
      tool_name: toolNameFilter.value.trim() || undefined,
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
    })
    calls.value = page.items
    total.value = page.total
  } catch (error) {
    errorMessage.value = `工具调用加载失败：${error instanceof Error ? error.message : '未知错误'}`
  } finally {
    refreshing.value = false
  }
}

function reload() {
  currentPage.value = 1
  void load()
}

async function openDetail(row: LlmToolCall) {
  detailOpen.value = true
  detailLoading.value = true
  currentDetail.value = null
  try {
    currentDetail.value = await toolCallsApi.detail(row.id)
  } catch (error) {
    errorMessage.value = `工具调用详情加载失败：${error instanceof Error ? error.message : '未知错误'}`
    detailOpen.value = false
  } finally {
    detailLoading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.mt-8 { margin-top: 8px; justify-content: flex-end; }
.json-title { font-weight: 600; margin: 16px 0 6px; }
.json-body {
  margin: 0;
  max-height: 220px;
  overflow: auto;
  font-size: 12px;
  background: var(--el-fill-color-lighter);
  padding: 8px;
  border-radius: 4px;
}
</style>
