<template>
  <div>
    <div class="page-toolbar">
      <span class="page-title" data-test="sessions-title">会话管理</span>
      <span class="tab-hint">OpenMemory 会话：查看会话列表与详情，可终止并清空会话上下文</span>
      <el-button type="primary" plain :loading="loading" data-test="sessions-refresh" @click="load">刷新</el-button>
    </div>
    <el-alert
      v-if="errorMsg"
      :title="errorMsg"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="sessions-error"
      @close="errorMsg = ''"
    />
    <div v-loading="loading">
      <el-table :data="sessions" stripe data-test="sessions-table" empty-text="暂无会话（OpenMemory 当前无活跃会话）">
        <el-table-column label="会话 ID" min-width="220">
          <template #default="{ row }">
            <code class="mono" data-test="session-id">{{ row.session_id }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="user_id" label="用户 ID" width="110" />
        <el-table-column label="消息数" width="90">
          <template #default="{ row }">{{ row.message_count ?? row.messages?.length ?? 0 }}</template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">{{ row.created_at || '—' }}</template>
        </el-table-column>
        <el-table-column label="更新时间" width="170">
          <template #default="{ row }">{{ row.updated_at || '—' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="170" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" data-test="session-detail" @click="openDetail(row.session_id)">详情</el-button>
            <el-popconfirm title="确认终止该会话？终止后会话上下文将被清空" @confirm="terminate(row.session_id)">
              <template #reference>
                <el-button link type="danger" data-test="session-terminate">终止</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="detailVisible" title="会话详情" width="640px" data-test="session-detail-dialog">
      <div v-loading="detailLoading">
        <template v-if="detail">
          <el-descriptions :column="2" border class="mb-16">
            <el-descriptions-item label="会话 ID" :span="2">
              <code class="mono">{{ detail.session_id }}</code>
            </el-descriptions-item>
            <el-descriptions-item label="用户 ID">{{ detail.user_id || '—' }}</el-descriptions-item>
            <el-descriptions-item label="消息数">{{ detail.messages?.length ?? 0 }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ detail.created_at || '—' }}</el-descriptions-item>
            <el-descriptions-item label="更新时间">{{ detail.updated_at || '—' }}</el-descriptions-item>
          </el-descriptions>
          <div v-if="detail.messages?.length" class="message-list" data-test="session-messages">
            <div v-for="(msg, idx) in detail.messages" :key="idx" class="message-row">
              <el-tag size="small" :type="msg.role === 'user' ? 'primary' : 'success'" effect="plain">
                {{ msg.role || 'system' }}
              </el-tag>
              <span class="message-text">{{ typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content) }}</span>
            </div>
          </div>
          <el-empty v-else description="该会话暂无消息" :image-size="60" />
        </template>
      </div>
      <template #footer>
        <el-button type="primary" @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { http } from '@/core/api/http'

interface SessionRow {
  session_id: string
  user_id: string | null
  message_count?: number
  messages?: SessionMessage[]
  created_at: string | null
  updated_at: string | null
}

interface SessionMessage {
  role?: string
  content?: string | Record<string, unknown>
}

const sessions = ref<SessionRow[]>([])
const loading = ref(false)
const detailLoading = ref(false)
const errorMsg = ref('')
const detailVisible = ref(false)
const detail = ref<SessionRow | null>(null)

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    const { data } = await http.get<{ code: number; message: string; data: SessionRow[] }>('/memory-proxy/sessions')
    sessions.value = data.data || []
  } catch (e) {
    sessions.value = []
    errorMsg.value = (e as { response?: { data?: { message?: string } } })?.response?.data?.message || '会话列表加载失败'
  } finally {
    loading.value = false
  }
}

async function openDetail(sessionId: string) {
  detailVisible.value = true
  detailLoading.value = true
  detail.value = null
  try {
    const { data } = await http.get<{ code: number; message: string; data: SessionRow }>(
      `/memory-proxy/sessions/${sessionId}`,
    )
    detail.value = data.data
  } catch (e) {
    detail.value = null
    ElMessage.error((e as { response?: { data?: { message?: string } } })?.response?.data?.message || '会话详情加载失败')
  } finally {
    detailLoading.value = false
  }
}

async function terminate(sessionId: string) {
  try {
    const { data } = await http.post<{ code: number; message: string; data: unknown }>(
      `/memory-proxy/sessions/${sessionId}/terminate`,
    )
    if (data.code === 0) {
      ElMessage.success('会话已终止并清空')
      await load()
    } else {
      ElMessage.error(data.message || '终止失败')
    }
  } catch (e) {
    ElMessage.error((e as { response?: { data?: { message?: string } } })?.response?.data?.message || '终止失败')
  }
}

onMounted(load)
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }
.page-title { font-size: 16px; font-weight: 600; }
.tab-hint { color: var(--ob-text-secondary); font-size: 13px; }
.mb-16 { margin-bottom: 16px; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px; word-break: break-all; }
.message-list { max-height: 320px; overflow: auto; display: flex; flex-direction: column; gap: 8px; }
.message-row { display: flex; align-items: flex-start; gap: 8px; }
.message-text { flex: 1; font-size: 13px; line-height: 1.6; white-space: pre-wrap; word-break: break-word; }
</style>
