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
        @change="onKbChange"
      >
        <el-option v-for="kb in knowledgeBases" :key="kb.id" :label="kb.name" :value="kb.id">
          <span>{{ kb.name }}</span>
          <span class="kb-doc-count">{{ kb.documents }} 篇文档</span>
        </el-option>
      </el-select>
      <p v-if="selectedKb" class="panel-hint">
        已关联 {{ selectedKb.documents }} 篇文档 / {{ selectedKb.chunks }} 个分块
      </p>
      <p v-else class="panel-hint">请选择知识库后开始对话</p>
      <el-divider />
      <p class="panel-tip">对话将基于所选知识库的检索结果生成回答，并附带来源引用。</p>
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
                      <span class="source-doc">{{ src.doc_name }}</span>
                      <span class="source-score">
                        <el-progress
                          :percentage="Math.round(src.score * 100)"
                          :stroke-width="8"
                          :show-text="false"
                          class="score-bar"
                        />
                        <span>{{ (src.score * 100).toFixed(0) }}%</span>
                      </span>
                    </div>
                    <p class="source-snippet">{{ src.snippet }}</p>
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
          @keydown.enter.exact.prevent="sendMessage"
        />
        <div class="chat-actions">
          <el-button
            :disabled="streaming || !lastUserMessage"
            data-test="regenerate"
            @click="regenerate"
          >
            重新生成
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
import { computed, onBeforeUnmount, ref } from 'vue'
import { ElMessage } from 'element-plus'

interface SourceRef {
  doc_name: string
  snippet: string
  score: number
}

interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  sources?: SourceRef[]
}

interface KnowledgeBase {
  id: number
  name: string
  documents: number
  chunks: number
}

const knowledgeBases = ref<KnowledgeBase[]>([
  { id: 1, name: '产品文档库', documents: 24, chunks: 1560 },
  { id: 2, name: '技术问答库', documents: 12, chunks: 890 },
  { id: 3, name: '法律合规库', documents: 8, chunks: 640 },
])

const selectedKbId = ref<number | null>(null)
const selectedKb = computed(() => knowledgeBases.value.find((kb) => kb.id === selectedKbId.value) || null)
const draft = ref('')
const messages = ref<ChatMessage[]>([])
const chatLoading = ref(false)
const streamingId = ref<number | null>(null)
const errorMessage = ref('')

const streaming = computed(() => streamingId.value !== null)
const lastUserMessage = computed(() => {
  return [...messages.value].reverse().find((msg) => msg.role === 'user') || null
})

let streamTimer: number | undefined

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
  streamReply(buildReply(text))
}

function regenerate() {
  if (!lastUserMessage.value || streaming.value) return
  const last = messages.value[messages.value.length - 1]
  if (last.role === 'assistant') {
    messages.value.pop()
  }
  streamReply(buildReply(lastUserMessage.value.content))
}

function buildReply(question: string): { content: string; sources: SourceRef[] } {
  const content = [
    `根据「${selectedKb.value?.name ?? '知识库'}」的检索结果，关于“${question}”的回答如下：`,
    '',
    'OpenBase 知识库采用「文档解析 → 分块 → 向量化 → 检索召回 → 重排」的完整链路。上传的文档先被解析为纯文本，再按默认分块大小切分为语义片段，并由 Embedding 模型生成向量索引。',
    '',
    '查询时系统计算向量相似度召回 TopK 个候选分块，结合重排序模型精排后，将最相关的片段作为上下文交由大模型生成回答。建议在检索测试台验证不同参数下的召回效果，再调整系统配置中的检索 TopK 与召回阈值。',
  ].join('\n')
  const sources: SourceRef[] = [
    { doc_name: '快速开始.md', snippet: 'OpenBase 提供统一登录与动态模块挂载能力，知识库模块支持文档上传、自动分块与向量检索，检索结果可追溯来源……', score: 0.86 },
    { doc_name: 'RAG 架构设计.pdf', snippet: '检索链路：查询向量化 → 相似度召回 TopK → 重排序 → 大模型生成，支持自定义分块大小与召回阈值……', score: 0.74 },
    { doc_name: 'API 参考.docx', snippet: 'POST /api/v1/knowledge/retrieve 提交查询与知识库 ID，返回命中的分块、文档名与相似度得分……', score: 0.65 },
  ]
  return { content, sources }
}

function streamReply(reply: { content: string; sources: SourceRef[] }) {
  const msg: ChatMessage = { id: Date.now() + 1, role: 'assistant', content: '', sources: reply.sources }
  messages.value.push(msg)
  chatLoading.value = true
  streamingId.value = msg.id
  let index = 0
  streamTimer = window.setInterval(() => {
    index += 2
    msg.content = reply.content.slice(0, index)
    if (index >= reply.content.length) {
      msg.content = reply.content
      if (streamTimer !== undefined) {
        window.clearInterval(streamTimer)
        streamTimer = undefined
      }
      streamingId.value = null
      chatLoading.value = false
    }
  }, 40)
}

onBeforeUnmount(() => {
  if (streamTimer !== undefined) {
    window.clearInterval(streamTimer)
    streamTimer = undefined
  }
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
