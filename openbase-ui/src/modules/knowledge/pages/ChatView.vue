<template>
  <div class="chat-layout">
    <!-- 左侧：知识库选择 -->
    <aside class="kb-panel">
      <h3 class="panel-title">知识库选择</h3>
      <el-select
        v-model="selectedKbId"
        placeholder="选择知识库"
        style="width: 100%"
        data-test="kb-select"
        :loading="kbLoading"
        @change="onKbChange"
      >
        <el-option v-for="kb in knowledgeBases" :key="kb.id" :label="kb.name" :value="kb.id">
          <span>{{ kb.name }}</span>
          <span class="kb-doc-count">{{ kb.document_count ?? 0 }} 篇文档</span>
        </el-option>
      </el-select>
      <p v-if="selectedKb" class="panel-hint">
        已关联 {{ selectedKb.document_count ?? 0 }} 篇文档
      </p>
      <p v-else class="panel-hint">请选择知识库后开始对话</p>
      <el-divider />
      <p class="panel-tip">对话将基于所选知识库的检索结果生成回答，并附带来源引用。</p>
      <el-button link type="primary" size="small" class="kb-refresh" @click="loadKbs">刷新列表</el-button>
    </aside>

    <!-- 右侧：聊天区 -->
    <section class="chat-panel">
      <el-alert
        v-if="errorMessage"
        :title="errorMessage"
        type="error"
        show-icon
        closable
        class="chat-alert"
        @close="errorMessage = ''"
      />
      <div v-loading="chatLoading" class="chat-messages" element-loading-text="检索知识库中…" data-test="chat-messages">
        <el-empty v-if="messages.length === 0" description="开始你的 RAG 对话吧" :image-size="80" />
        <template v-for="msg in messages" :key="msg.id">
          <div class="chat-msg" :class="msg.role">
            <span class="chat-msg-role">{{ msg.role === 'user' ? '我' : '助手' }}</span>
            <div class="chat-bubble">
              <div class="chat-content">
                {{ msg.content }}
                <span v-if="msg.id === streamingId" class="stream-cursor">▍</span>
              </div>
              <el-collapse v-if="msg.role === 'assistant' && msg.sources?.length" class="source-collapse">
                <el-collapse-item :title="`来源引用（${msg.sources.length}）`" name="sources">
                  <div v-for="(src, idx) in msg.sources" :key="idx" class="source-item">
                    <div class="source-head">
                      <span class="source-doc">{{ src.doc_name || src.chunk_id || '来源片段' }}</span>
                      <span class="source-score">
                        <el-progress
                          :percentage="Math.round((src.score ?? 0) * 100)"
                          :stroke-width="8"
                          :show-text="false"
                          class="score-bar"
                        />
                        <span>{{ ((src.score ?? 0) * 100).toFixed(0) }}%</span>
                      </span>
                    </div>
                    <p class="source-snippet">{{ src.snippet || src.content || '' }}</p>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </div>
          </div>
        </template>
      </div>
      <div class="chat-input">
        <el-input
          v-model="draft"
          type="textarea"
          :rows="3"
          resize="none"
          placeholder="输入问题，Enter 发送（Shift+Enter 换行）"
          data-test="chat-input"
          :disabled="streaming"
          @keydown.enter.exact.prevent="sendMessage"
        />
        <div class="chat-actions">
          <el-button :disabled="streaming || !lastUserMessage" data-test="regenerate" @click="regenerate">
            重新生成
          </el-button>
          <el-button v-if="streaming" type="danger" plain data-test="stop-stream" @click="stopStream">
            停止
          </el-button>
          <el-button
            type="primary"
            :disabled="!draft.trim() || streaming"
            data-test="send-message"
            @click="sendMessage"
          >
            发送
          </el-button>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ragApi, type RagCollection, type RagSource } from '@/core/api/rag'

interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  sources?: RagSource[]
}

const knowledgeBases = ref<RagCollection[]>([])
const kbLoading = ref(false)
const selectedKbId = ref<string | null>(null)
const selectedKb = computed(() => knowledgeBases.value.find((kb) => kb.id === selectedKbId.value) || null)
const draft = ref('')
const messages = ref<ChatMessage[]>([])
const chatLoading = ref(false)
const streamingId = ref<number | null>(null)
const errorMessage = ref('')

let abortController: AbortController | null = null

const streaming = computed(() => streamingId.value !== null)
const lastUserMessage = computed(() => {
  return [...messages.value].reverse().find((msg) => msg.role === 'user') || null
})

async function loadKbs() {
  kbLoading.value = true
  try {
    const result = await ragApi.listCollections({ page: 1, page_size: 100 })
    knowledgeBases.value = result.items || []
  } catch {
    errorMessage.value = '知识库列表加载失败，请检查网络后重试'
  } finally {
    kbLoading.value = false
  }
}

function onKbChange() {
  errorMessage.value = ''
  ElMessage.info(`已切换到知识库：${selectedKb.value?.name ?? ''}`)
}

function sendMessage() {
  const text = draft.value.trim()
  if (!text) return
  if (!selectedKb.value) {
    errorMessage.value = '请先选择知识库，再进行对话'
    return
  }
  errorMessage.value = ''
  messages.value.push({ id: Date.now(), role: 'user', content: text })
  draft.value = ''
  void streamReply(text)
}

function regenerate() {
  if (!lastUserMessage.value || streaming.value) return
  const last = messages.value[messages.value.length - 1]
  if (last.role === 'assistant') {
    messages.value.pop()
  }
  void streamReply(lastUserMessage.value.content)
}

function stopStream() {
  abortController?.abort()
  abortController = null
  if (streamingId.value !== null) {
    streamingId.value = null
    chatLoading.value = false
  }
  ElMessage.info('已停止生成')
}

/** 从 SSE error 事件体提取可读错误信息（message / detail 数组 / detail 字符串） */
function extractErrorMessage(raw: string): string {
  try {
    const data = JSON.parse(raw) as { message?: string; detail?: unknown }
    if (typeof data.message === 'string' && data.message) return data.message
    if (Array.isArray(data.detail)) {
      const msgs = data.detail
        .filter((item): item is { msg?: string } => typeof item === 'object' && item !== null)
        .map((item) => item.msg)
        .filter((m): m is string => typeof m === 'string')
      if (msgs.length > 0) return msgs.join('；')
    }
    if (typeof data.detail === 'string') return data.detail
  } catch {
    // 非 JSON 错误体
  }
  return '流式回复出错'
}

function streamReply(question: string) {
  const cid = selectedKb.value?.id
  if (!cid) return
  abortController?.abort()
  abortController = new AbortController()
  const msg: ChatMessage = { id: Date.now() + 1, role: 'assistant', content: '' }
  messages.value.push(msg)
  chatLoading.value = true
  streamingId.value = msg.id
  const finalSources: RagSource[] = []

  ragApi
    .queryStream(
      cid,
      { query: question, top_k: 5, collection_ids: [cid] },
      (evt) => {
        if (evt.event === 'token') {
          try {
            const data = JSON.parse(evt.data) as { delta?: string }
            if (data.delta) msg.content += data.delta
          } catch {
            // 忽略解析失败的事件片段
          }
        } else if (evt.event === 'done') {
          try {
            const data = JSON.parse(evt.data) as { answer?: string; sources?: RagSource[] }
            if (data.answer) msg.content = data.answer
            if (Array.isArray(data.sources) && data.sources.length > 0) {
              finalSources.push(...data.sources)
            }
          } catch {
            // done 事件无数据体（非流式兜底）时保持已渲染内容
          }
        } else if (evt.event === 'error') {
          errorMessage.value = extractErrorMessage(evt.data)
        }
      },
      abortController.signal,
    )
    .catch(() => {
      if (!abortController?.signal.aborted) {
        errorMessage.value = '流式请求失败，请重试'
      }
    })
    .finally(() => {
      msg.sources = finalSources.length > 0 ? finalSources : undefined
      streamingId.value = null
      chatLoading.value = false
      abortController = null
    })
}

onMounted(() => {
  void loadKbs()
})

onBeforeUnmount(() => {
  abortController?.abort()
  abortController = null
})
</script>

<style scoped>
.chat-layout { display: flex; gap: 16px; align-items: flex-start; }
.kb-panel {
  width: 250px; flex-shrink: 0;
  background: var(--ob-surface); border: 1px solid var(--ob-border);
  border-radius: var(--ob-radius-md); padding: 16px;
}
.panel-title { margin: 0 0 12px; font-size: 14px; }
.kb-doc-count { float: right; color: var(--ob-text-disabled); font-size: 12px; }
.panel-hint { color: var(--ob-text-secondary); font-size: 12px; margin: 10px 0 0; line-height: 1.6; }
.panel-tip { color: var(--ob-text-disabled); font-size: 12px; line-height: 1.6; margin: 0; }
.kb-refresh { margin-top: 10px; }
.chat-panel {
  flex: 1; min-width: 0;
  display: flex; flex-direction: column;
  background: var(--ob-surface); border: 1px solid var(--ob-border);
  border-radius: var(--ob-radius-md); padding: 16px;
}
.chat-alert { margin-bottom: 12px; }
.chat-messages {
  height: calc(100vh - 260px); min-height: 360px;
  overflow-y: auto; padding: 12px;
  background: var(--ob-bg); border-radius: var(--ob-radius-md);
}
.chat-msg { display: flex; gap: 8px; margin-bottom: 14px; }
.chat-msg.user { flex-direction: row-reverse; }
.chat-msg-role { flex-shrink: 0; font-size: 12px; color: var(--ob-text-secondary); margin-top: 8px; }
.chat-bubble {
  max-width: 74%; padding: 10px 12px;
  border-radius: var(--ob-radius-md);
  background: var(--ob-surface); border: 1px solid var(--ob-border);
  white-space: pre-wrap; word-break: break-word; line-height: 1.6;
}
.chat-msg.user .chat-bubble { background: var(--el-color-primary-light-9); border-color: var(--el-color-primary-light-7); }
.source-collapse { margin-top: 8px; border-top: 1px dashed var(--ob-border); }
.source-item { padding: 6px 0; }
.source-head { display: flex; justify-content: space-between; align-items: center; gap: 12px; font-size: 13px; }
.source-doc { font-weight: 600; }
.source-score { display: flex; align-items: center; gap: 6px; color: var(--ob-text-secondary); font-size: 12px; white-space: nowrap; }
.score-bar { width: 90px; }
.source-snippet { color: var(--ob-text-secondary); font-size: 12px; margin: 4px 0 0; line-height: 1.6; }
.chat-input { margin-top: 12px; }
.chat-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 8px; }
.stream-cursor { color: var(--ob-primary); animation: ob-blink 1s step-start infinite; }
@keyframes ob-blink { 50% { opacity: 0; } }
</style>
