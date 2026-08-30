<template>
  <div>
    <div class="page-toolbar">
      <span class="page-title" data-test="write-title">写入记忆</span>
      <span class="tab-hint">内容将经 memory-proxy 写入 OpenMemory 持久存储（POST /api/v1/remember）</span>
    </div>
    <el-alert
      v-if="errorMsg"
      :title="errorMsg"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="write-error"
      @close="errorMsg = ''"
    />
    <el-row :gutter="16">
      <el-col :xs="24" :lg="16">
        <el-card class="mb-16">
          <template #header>记忆内容</template>
          <el-form label-width="90px" :model="form" @submit.prevent>
            <el-form-item label="记忆内容" required>
              <el-input
                v-model="form.content"
                type="textarea"
                :rows="6"
                maxlength="50000"
                show-word-limit
                placeholder="输入要写入 OpenMemory 的记忆内容，如：用户 admin 喜欢喝美式咖啡，不加糖"
                data-test="write-content"
              />
            </el-form-item>
            <el-form-item label="用户 ID">
              <el-input v-model="form.user_id" placeholder="留空默认当前登录用户" data-test="write-user" />
            </el-form-item>
            <el-form-item label="会话 ID">
              <el-input v-model="form.session_id" placeholder="关联会话（可选）" data-test="write-session" />
            </el-form-item>
            <el-form-item label="智能体 ID">
              <el-input v-model="form.agent_id" placeholder="关联智能体（可选）" data-test="write-agent" />
            </el-form-item>
            <el-form-item label="标签">
              <el-select
                v-model="form.tags"
                multiple
                filterable
                allow-create
                default-first-option
                placeholder="输入后回车创建标签"
                style="width: 100%"
                data-test="write-tags"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="submitting" data-test="write-submit" @click="submit">写入记忆</el-button>
              <el-button @click="resetForm">重置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="8">
        <el-card v-if="lastResult" class="mb-16" data-test="write-result-card">
          <template #header>写入结果</template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="记忆 ID">
              <code class="mono" data-test="write-memory-id">{{ lastResult.memory_id }}</code>
            </el-descriptions-item>
            <el-descriptions-item label="状态">{{ lastResult.status }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ lastResult.created_at }}</el-descriptions-item>
          </el-descriptions>
          <div class="result-actions">
            <el-button size="small" type="primary" plain @click="$router.push('/memory/list')">查看记忆列表</el-button>
            <el-button size="small" @click="$router.push(`/memory/${lastResult.memory_id}`)">查看详情</el-button>
          </div>
        </el-card>
        <el-card>
          <template #header>提示</template>
          <ul class="hint-list">
            <li>写入内容将经 OpenBase 统一认证（JWT）与双层密钥通道转发至 OpenMemory 8020。</li>
            <li>带标签的记忆便于后续列表页按标签过滤。</li>
            <li>写入成功后可在「记忆列表」页看到该条记录。</li>
          </ul>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { http } from '@/core/api/http'

interface RememberResult {
  memory_id: string
  status: string
  created_at: string
}

const form = reactive<{
  content: string
  user_id: string
  session_id: string
  agent_id: string
  tags: string[]
}>({
  content: '',
  user_id: '',
  session_id: '',
  agent_id: '',
  tags: [],
})

const errorMsg = ref('')
const submitting = ref(false)
const lastResult = ref<RememberResult | null>(null)

async function submit() {
  const content = form.content.trim()
  if (!content) {
    errorMsg.value = '请输入记忆内容'
    return
  }
  errorMsg.value = ''
  submitting.value = true
  try {
    const payload: Record<string, unknown> = { content }
    if (form.user_id.trim()) payload.user_id = form.user_id.trim()
    if (form.session_id.trim()) payload.session_id = form.session_id.trim()
    if (form.agent_id.trim()) payload.agent_id = form.agent_id.trim()
    if (form.tags.length) payload.metadata = { tags: form.tags }
    const { data } = await http.post<{ code: number; message: string; data: RememberResult }>(
      '/memory-proxy/remember',
      payload,
    )
    if (data.code === 0 && data.data?.memory_id) {
      lastResult.value = data.data
      ElMessage.success('记忆写入成功')
      form.content = ''
      form.tags = []
    } else {
      errorMsg.value = data.message || '写入失败'
    }
  } catch (e) {
    errorMsg.value = (e as { response?: { data?: { message?: string } } })?.response?.data?.message || '写入失败，请稍后重试'
  } finally {
    submitting.value = false
  }
}

function resetForm() {
  form.content = ''
  form.user_id = ''
  form.session_id = ''
  form.agent_id = ''
  form.tags = []
  errorMsg.value = ''
}
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }
.page-title { font-size: 16px; font-weight: 600; }
.tab-hint { color: var(--ob-text-secondary); font-size: 13px; }
.mb-16 { margin-bottom: 16px; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px; word-break: break-all; }
.result-actions { margin-top: 12px; display: flex; gap: 8px; }
.hint-list { margin: 0; padding-left: 18px; line-height: 1.9; color: var(--ob-text-secondary); font-size: 13px; }
</style>
