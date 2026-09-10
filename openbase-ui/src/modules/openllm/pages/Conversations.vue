<template>
  <div>
    <el-result
      v-if="isForbidden"
      icon="error"
      :title="presentation?.title || ''"
      :sub-title="presentation?.detail || ''"
      data-test="isolation-forbidden"
    >
      <template #extra>
        <p v-if="presentation?.requestId" class="request-id" data-test="error-request-id">
          请求编号：{{ presentation.requestId }}
        </p>
        <el-button data-test="isolation-back" @click="$router.push('/dashboard')">返回仪表盘</el-button>
      </template>
    </el-result>

    <div v-else-if="isNotFound" data-test="isolation-not-found">
      <el-empty description="资源不存在或已被移除" />
    </div>

    <template v-else>
      <el-alert
        v-if="showErrorBar"
        :title="errorMessage"
        type="error"
        show-icon
        closable
        class="mb-16"
        data-test="isolation-error-bar"
        @close="presentation = null"
      >
        <template #default>
          <el-button link type="primary" size="small" data-test="isolation-retry" @click="loadConversations">点击重试</el-button>
        </template>
      </el-alert>
      <div class="page-toolbar">
        <el-input v-model="keyword" placeholder="搜索对话标题" clearable style="width: 200px" data-test="conversation-search" />
        <el-select v-model="modelFilter" placeholder="模型筛选" clearable style="width: 140px">
          <el-option label="gpt-4o" value="gpt-4o" />
          <el-option label="qwen2.5-7b" value="qwen2.5-7b" />
        </el-select>
        <el-button type="primary" data-test="new-conversation" @click="openNew">新建会话</el-button>
        <el-button data-test="export-conversations" @click="exportJson">导出（JSON）</el-button>
        <el-popconfirm title="确认批量删除选中对话？" @confirm="batchDelete">
          <template #reference>
            <el-button type="danger" plain :disabled="selection.length === 0">批量删除</el-button>
          </template>
        </el-popconfirm>
      </div>
      <div class="ob-table-scroll">
        <el-table :data="filtered" stripe data-test="conversation-table" @selection-change="(rows: any[]) => (selection = rows)">
          <el-table-column type="selection" width="44" />
          <el-table-column prop="title" label="标题" min-width="170" />
          <el-table-column prop="model" label="模型" width="120" />
          <el-table-column prop="messages" label="消息数" width="80" />
          <el-table-column prop="started_at" label="开始时间" width="160" />
          <el-table-column label="Token 消耗" width="100">
            <template #default="{ row }">{{ row.tokens ?? '-' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="190" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openChat(row)">聊天</el-button>
              <el-button link type="primary" @click="toggleArchive(row)">{{ row.archived ? '取消归档' : '归档' }}</el-button>
              <el-popconfirm title="确认删除该对话？" @confirm="remove(row.id)">
                <template #reference><el-button link type="danger">删除</el-button></template>
              </el-popconfirm>
            </template>
          </el-table-column>
          <template #empty>
            <el-empty data-test="isolation-empty" :description="emptyDescription" />
          </template>
        </el-table>
      </div>

      <el-dialog v-model="newVisible" title="新建会话" width="480px" data-test="new-conversation-dialog">
        <el-form label-width="100px">
          <el-form-item label="会话标题"><el-input v-model="newForm.title" placeholder="留空自动生成" /></el-form-item>
          <el-form-item label="模型" required>
            <el-select v-model="newForm.model" style="width: 100%">
              <el-option v-for="m in modelOptions" :key="m" :label="m" :value="m" />
            </el-select>
          </el-form-item>
          <el-form-item label="系统提示"><el-input v-model="newForm.systemPrompt" type="textarea" :rows="2" placeholder="可选" /></el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="newVisible = false">取消</el-button>
          <el-button type="primary" data-test="new-conversation-submit" @click="createConversation">创建</el-button>
        </template>
      </el-dialog>

      <el-drawer v-model="chatVisible" :title="current?.title || '对话'" size="520px" data-test="chat-drawer">
        <div class="chat-box">
          <div v-for="msg in current?.chatMessages" :key="msg.id" class="chat-msg" :class="msg.role">
            <div class="chat-bubble">{{ msg.content }}</div>
          </div>
          <div v-if="chatLoading" class="chat-msg assistant">
            <div class="chat-bubble typing">…</div>
          </div>
        </div>
        <div class="chat-input">
          <el-input v-model="chatInput" placeholder="输入消息，Enter 发送" data-test="chat-input" @keyup.enter="sendMessage" />
          <el-button type="primary" :disabled="!chatInput.trim()" @click="sendMessage">发送</el-button>
        </div>
      </el-drawer>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { llmApi, type ChatMessage as ApiChatMessage } from '@/core/api/llm'
import { describeError, type ErrorPresentation } from '@/core/api/error'

interface ChatMessage { id: number; role: 'user' | 'assistant'; content: string }
interface Conversation {
  id: string
  title: string
  model: string
  messages: number
  started_at: string
  tokens?: number
  archived?: boolean
  chatMessages?: ChatMessage[]
  _assistantId?: number
}

const keyword = ref('')
const modelFilter = ref('')
const selection = ref<Conversation[]>([])
const newVisible = ref(false)
const chatVisible = ref(false)
const chatInput = ref('')
const chatLoading = ref(false)
const loading = ref(false)
const presentation = ref<ErrorPresentation | null>(null)
const current = ref<Conversation | null>(null)
const newForm = reactive({ title: '', model: 'qwen2.5-7b', systemPrompt: '' })
const modelOptions = ref<string[]>(['qwen2.5-7b'])

const isForbidden = computed(() => presentation.value?.pageLevel === true)
const isNotFound = computed(() => presentation.value?.kind === 'not-found')
const showErrorBar = computed(
  () => !!presentation.value && !presentation.value.pageLevel && presentation.value.kind !== 'not-found',
)
const errorMessage = computed(() =>
  showErrorBar.value ? `会话列表加载失败：${presentation.value?.detail || '网络错误'}` : '',
)
const emptyDescription = computed(() => {
  if (showErrorBar.value) return '加载失败，请点击上方提示条「点击重试」'
  return '当前租户暂无数据（如为权限问题请联系管理员）'
})

const conversations = ref<Conversation[]>([])

async function loadModelOptions() {
  try {
    const { models } = await llmApi.fetchModels()
    const ids = (models || []).map((m) => String(m.id || '')).filter(Boolean)
    if (ids.length) modelOptions.value = ids
  } catch {
    /* 模型选项加载失败时保留默认值 */
  }
}

async function loadConversations() {
  loading.value = true
  presentation.value = null
  try {
    const { items } = await llmApi.listConversations({ skip: 0, limit: 100 })
    conversations.value = (items || []).map((c) => ({
      id: String(c.id || ''),
      title: String(c.title || '未命名会话'),
      model: String(c.model || ''),
      messages: Number(c.messages || 0),
      started_at: String(c.started_at || ''),
      tokens: c.tokens ? Number(c.tokens) : undefined,
      archived: Boolean(c.archived),
      chatMessages: [],
    }))
  } catch (err) {
    conversations.value = []
    presentation.value = describeError(err)
  } finally {
    loading.value = false
  }
}
onMounted(() => {
  loadConversations()
  loadModelOptions()
})

const filtered = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return conversations.value.filter((c) => {
    const matchKw = !kw || c.title.toLowerCase().includes(kw)
    const matchModel = !modelFilter.value || c.model === modelFilter.value
    return matchKw && matchModel
  })
})

function openNew() {
  newForm.title = ''
  newForm.model = modelOptions.value[0] || 'qwen2.5-7b'
  newForm.systemPrompt = ''
  newVisible.value = true
}
async function createConversation() {
  try {
    const created = await llmApi.createConversation({
      title: newForm.title.trim() || undefined,
      model: newForm.model,
      system_prompt: newForm.systemPrompt || undefined,
    })
    conversations.value.unshift({
      id: String(created.id || Date.now()),
      title: String(created.title || newForm.title.trim() || '新会话'),
      model: String(created.model || newForm.model),
      messages: 0,
      started_at: String(created.started_at || ''),
      chatMessages: [],
    })
    newVisible.value = false
    ElMessage.success('会话已创建')
  } catch {
    ElMessage.error('会话创建失败（OpenLLM 会话端点为 JWT 通道，M1 待完善）')
  }
}
function openChat(row: Conversation) {
  current.value = row
  if (!row.chatMessages) row.chatMessages = []
  chatVisible.value = true
}
async function sendMessage() {
  if (!chatInput.value.trim() || !current.value) return
  const text = chatInput.value.trim()
  current.value.chatMessages!.push({ id: Date.now(), role: 'user', content: text })
  current.value.messages += 1
  chatInput.value = ''
  chatLoading.value = true
  const model = current.value.model || modelOptions.value[0] || 'qwen2.5-7b'
  const history: ApiChatMessage[] = (current.value.chatMessages || []).map((m) => ({ role: m.role, content: m.content }))
  let reply = ''
  try {
    await llmApi.sendChatStream({ model, messages: history }, (evt) => {
      if (evt.event === 'chunk') {
        try {
          const parsed = JSON.parse(evt.data)
          const delta = parsed.choices?.[0]?.delta?.content || parsed.choices?.[0]?.message?.content || ''
          if (delta) {
              reply += delta
              const msgs = current.value?.chatMessages || []
              const last = msgs.length ? msgs[msgs.length - 1] : undefined
              if (last && last.role === 'assistant' && last.id === current.value?._assistantId) {
                last.content = reply
              } else {
              const id = Date.now()
              if (current.value) current.value._assistantId = id
              current.value?.chatMessages?.push({ id, role: 'assistant', content: reply })
            }
          }
        } catch {
          /* 非 chunk JSON 忽略 */
        }
      } else if (evt.event === 'error') {
        ElMessage.error('对话流异常，请重试')
      }
    })
    if (!reply && current.value) {
      current.value.chatMessages!.push({ id: Date.now(), role: 'assistant', content: '（无回复，请检查模型可用性）' })
    }
  } catch {
    ElMessage.error('对话失败，请确认 OpenLLM 服务（8001）可用')
  } finally {
    chatLoading.value = false
  }
}
async function toggleArchive(row: Conversation) {
  try {
    await llmApi.archiveConversation(row.id, { archived: !row.archived })
    row.archived = !row.archived
    ElMessage.success(`已${row.archived ? '归档' : '取消归档'}：${row.title}`)
  } catch {
    ElMessage.error('归档操作失败（OpenLLM 会话端点为 JWT 通道，M1 待完善）')
  }
}
async function remove(id: string) {
  try {
    await llmApi.deleteConversation(id)
    conversations.value = conversations.value.filter((c) => c.id !== id)
    ElMessage.success('对话已删除')
  } catch {
    ElMessage.error('删除失败（OpenLLM 会话端点为 JWT 通道，M1 待完善）')
  }
}
async function batchDelete() {
  const ids = selection.value.map((s) => s.id)
  for (const id of ids) {
    try {
      await llmApi.deleteConversation(id)
    } catch {
      /* 单条失败继续 */
    }
  }
  conversations.value = conversations.value.filter((c) => !ids.includes(c.id))
  ElMessage.success(`已删除 ${ids.length} 条对话`)
}
function exportJson() {
  const data = JSON.stringify(conversations.value, null, 2)
  const blob = new Blob([data], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `conversations-${new Date().toISOString().slice(0, 10)}.json`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success(`已导出 ${conversations.value.length} 条对话`)
}
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.mb-16 { margin-bottom: 16px; }
.request-id { color: #6b7280; font-size: 12px; margin-bottom: 8px; }
.chat-box { height: 380px; overflow-y: auto; padding: 8px; background: var(--ob-bg-secondary, #f5f7fa); border-radius: 6px; }
.chat-msg { display: flex; margin-bottom: 10px; }
.chat-msg.user { justify-content: flex-end; }
.chat-bubble { max-width: 80%; padding: 8px 12px; border-radius: 8px; background: #fff; border: 1px solid var(--el-border-color-lighter); }
.chat-msg.user .chat-bubble { background: var(--el-color-primary-light-9); }
.chat-msg.assistant .chat-bubble.typing { color: var(--ob-text-secondary); }
.chat-input { display: flex; gap: 8px; margin-top: 12px; }
</style>
