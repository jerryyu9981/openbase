<template>
  <div>
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
      </el-table>
    </div>

    <el-dialog v-model="newVisible" title="新建会话" width="480px" data-test="new-conversation-dialog">
      <el-form label-width="100px">
        <el-form-item label="会话标题"><el-input v-model="newForm.title" placeholder="留空自动生成" /></el-form-item>
        <el-form-item label="模型" required>
          <el-select v-model="newForm.model" style="width: 100%">
            <el-option label="gpt-4o" value="gpt-4o" />
            <el-option label="qwen2.5-7b" value="qwen2.5-7b" />
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
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

interface ChatMessage { id: number; role: 'user' | 'assistant'; content: string }
interface Conversation {
  id: number
  title: string
  model: string
  messages: number
  started_at: string
  tokens?: number
  archived?: boolean
  chatMessages?: ChatMessage[]
}

const keyword = ref('')
const modelFilter = ref('')
const selection = ref<Conversation[]>([])
const newVisible = ref(false)
const chatVisible = ref(false)
const chatInput = ref('')
const chatLoading = ref(false)
const current = ref<Conversation | null>(null)
const newForm = reactive({ title: '', model: 'gpt-4o', systemPrompt: '' })

const conversations = ref<Conversation[]>([
  { id: 1, title: 'RAG 知识库测试对话', model: 'qwen2.5-7b', messages: 12, started_at: '2026-08-25 10:20', tokens: 3842, chatMessages: [
    { id: 1, role: 'user', content: '介绍一下知识库检索流程' },
    { id: 2, role: 'assistant', content: '知识库检索分为：文档切分 → 向量化 → 检索召回 → 重排 → 生成回答五个阶段。' },
  ] },
  { id: 2, title: '多轮需求讨论', model: 'gpt-4o', messages: 8, started_at: '2026-08-25 09:10', tokens: 5210 },
  { id: 3, title: 'SQL 生成练习', model: 'gpt-4o', messages: 5, started_at: '2026-08-24 16:45', tokens: 2980, archived: true },
])

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
  newForm.model = 'gpt-4o'
  newForm.systemPrompt = ''
  newVisible.value = true
}
function createConversation() {
  conversations.value.unshift({
    id: Date.now(),
    title: newForm.title.trim() || `新会话 ${new Date().toLocaleTimeString()}`,
    model: newForm.model,
    messages: 0,
    started_at: new Date().toISOString().slice(0, 16).replace('T', ' '),
    tokens: 0,
    chatMessages: [],
  })
  newVisible.value = false
  ElMessage.success('会话已创建')
}
function openChat(row: Conversation) {
  current.value = row
  if (!row.chatMessages) row.chatMessages = []
  chatVisible.value = true
}
function sendMessage() {
  if (!chatInput.value.trim() || !current.value) return
  current.value.chatMessages!.push({ id: Date.now(), role: 'user', content: chatInput.value.trim() })
  current.value.messages += 1
  chatInput.value = ''
  chatLoading.value = true
  setTimeout(() => {
    if (current.value) {
      current.value.chatMessages!.push({ id: Date.now() + 1, role: 'assistant', content: '（模拟流式回复）已收到您的消息，该功能对接后由真实模型生成。' })
      current.value.messages += 1
    }
    chatLoading.value = false
  }, 500)
}
function toggleArchive(row: Conversation) {
  row.archived = !row.archived
  ElMessage.success(`已${row.archived ? '归档' : '取消归档'}：${row.title}`)
}
function remove(id: number) {
  conversations.value = conversations.value.filter((c) => c.id !== id)
  ElMessage.success('对话已删除')
}
function batchDelete() {
  const ids = selection.value.map((s) => s.id)
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
.chat-box { height: 380px; overflow-y: auto; padding: 8px; background: var(--ob-bg-secondary, #f5f7fa); border-radius: 6px; }
.chat-msg { display: flex; margin-bottom: 10px; }
.chat-msg.user { justify-content: flex-end; }
.chat-bubble { max-width: 80%; padding: 8px 12px; border-radius: 8px; background: #fff; border: 1px solid var(--el-border-color-lighter); }
.chat-msg.user .chat-bubble { background: var(--el-color-primary-light-9); }
.chat-msg.assistant .chat-bubble.typing { color: var(--ob-text-secondary); }
.chat-input { display: flex; gap: 8px; margin-top: 12px; }
</style>
