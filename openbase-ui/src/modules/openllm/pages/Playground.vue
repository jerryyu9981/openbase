<template>
  <PageContainer title="Playground" description="在线调试模型与提示词" test-id="playground-page">
    <div class="page-toolbar">
      <el-radio-group
        v-model="channelMode"
        data-test="playground-channel"
        :disabled="streaming"
        @change="handleChannelChange"
      >
        <el-radio-button value="direct">直连模型</el-radio-button>
        <el-radio-button value="auto">自动编排</el-radio-button>
      </el-radio-group>
      <el-select
        v-model="modelId"
        placeholder="选择模型"
        style="width: 220px"
        data-test="playground-model"
        :loading="modelsLoading"
        @change="handleModelChange"
      >
        <el-option v-for="m in models" :key="m.id" :label="modelLabel(m)" :value="m.id" />
      </el-select>
      <el-input
        v-model="prompt"
        placeholder="输入对话内容，回车发送（真实 SSE 流式，经 OpenBase llm-proxy）"
        data-test="playground-input"
        :disabled="streaming"
        @keyup.enter="send"
      />
      <el-button type="primary" data-test="playground-send" :loading="streaming" @click="send">发送</el-button>
    </div>
    <div class="channel-hint" data-test="playground-channel-hint">{{ channelHint }}</div>
    <div v-if="contextMetaText" class="context-meta" data-test="playground-context-meta">{{ contextMetaText }}</div>
    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon closable class="mb-16" @close="errorMessage = ''" />
    <div class="chat-panel">
      <div v-for="(m, i) in messages" :key="i" class="chat-msg" :class="m.role">
        <span class="chat-role">{{ m.role === 'user' ? '我' : '模型' }}</span>
        <div class="chat-content">{{ m.content }}</div>
      </div>
      <el-empty v-if="messages.length === 0" description="选择通道与模型后开始一段对话调试" :image-size="60" />
    </div>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { computed, onMounted, ref } from 'vue'
import { llmApi, type ChatMessage, type ChatStreamPayload, type LlmModel } from '@/core/api/llm'
import {
  extractContextMeta,
  formatContextMeta,
  loadContextPolicy,
  type ContextMeta,
} from '@/core/contextPolicy'

interface ChatMessageView { role: 'user' | 'assistant'; content: string }

/** 对话通道：direct=模型直呼（不经编排）；auto=OpenLLM 统一编排 */
type ChannelMode = 'direct' | 'auto'

const prompt = ref('')
const streaming = ref(false)
const messages = ref<ChatMessageView[]>([])
const errorMessage = ref('')
const models = ref<LlmModel[]>([])
const modelId = ref('')
const modelsLoading = ref(false)
const channelMode = ref<ChannelMode>('direct')
/** auto 模式下的本轮编排回执（来自 SSE routing 事件） */
const routingHint = ref('')
/** 批次 4 R7：本轮上下文裁剪回执（context_meta） */
const contextMeta = ref<ContextMeta | null>(null)
const contextMetaText = computed(() => formatContextMeta(contextMeta.value))

const channelHint = computed(() => {
  if (channelMode.value === 'direct') {
    return '通道 A · 直连模型：仅调用所选模型，不经 DPS / 记忆 / 知识库装配'
  }
  return routingHint.value || '通道 B · 自动编排：由 OpenLLM 判断是否装配 画像 / 记忆 / 知识库'
})

/** 候选偏好模型（本地 Ollama 实机常用） */
const PREFERRED = ['qwen2.5:0.5b', 'llama3.2:1b', 'qwen2.5:1.5b']

function modelLabel(m: LlmModel): string {
  const parts = [m.name || m.id]
  if (m.status) parts.push(`[${m.status}]`)
  if (m.provider) parts.push(`(${m.provider})`)
  return parts.join(' ')
}

async function loadModels() {
  modelsLoading.value = true
  try {
    const { models: list } = await llmApi.fetchModels()
    models.value = list || []
    const active = list || []
    const preferred = active.find((m) => PREFERRED.includes(m.id)) || active.find((m) => (m.status ?? 'enabled') !== 'disabled') || active[0]
    modelId.value = preferred?.id || ''
    if (!modelId.value) errorMessage.value = '未获取到可用模型，请检查 OpenLLM(8001)/llm-proxy 连通性'
  } catch (err) {
    errorMessage.value = `模型列表加载失败：${(err as Error).message || '网络错误'}`
  } finally {
    modelsLoading.value = false
  }
}

function handleModelChange() {
  errorMessage.value = ''
}

function handleChannelChange() {
  errorMessage.value = ''
  routingHint.value = ''
}

/** 解析 SSE routing 回执，呈现本轮实际装配结果（仅 auto 模式有意义） */
function updateRoutingHint(raw: string) {
  try {
    const trace = JSON.parse(raw) as {
      path?: string
      components?: {
        need_memory?: boolean
        need_rag?: boolean
        executed?: string[]
        degraded?: string[]
      }
      model?: { selected?: string }
    }
    const components = trace.components || {}
    const executed = components.executed || []
    routingHint.value = [
      '通道 B · 自动编排',
      trace.path ? `路径 ${trace.path}` : '',
      `记忆 ${components.need_memory || executed.includes('memory') ? '启用' : '跳过'}`,
      `知识库 ${components.need_rag || executed.includes('rag') ? '启用' : '跳过'}`,
      trace.model?.selected ? `模型 ${trace.model.selected}` : '',
      components.degraded?.length ? `降级 ${components.degraded.join('/')}` : '',
    ]
      .filter(Boolean)
      .join(' · ')
  } catch {
    routingHint.value = '通道 B · 自动编排（routing 回执解析失败）'
  }
}

function appendDelta(text: string) {
  const last = messages.value[messages.value.length - 1]
  if (last && last.role === 'assistant') {
    last.content += text
  } else {
    messages.value.push({ role: 'assistant', content: text })
  }
}

function parseDelta(data: string): string {
  try {
    const chunk = JSON.parse(data) as {
      delta?: string
      choices?: Array<{ delta?: { content?: string }; message?: { content?: string } }>
    }
    const choice = chunk.choices?.[0]
    return choice?.delta?.content ?? choice?.message?.content ?? chunk.delta ?? ''
  } catch {
    return ''
  }
}

async function send() {
  const text = prompt.value.trim()
  if (!text) return
  if (channelMode.value === 'direct' && !modelId.value) {
    errorMessage.value = '请先选择可用模型（模型列表来自 /llm-proxy/models）'
    return
  }
  messages.value.push({ role: 'user', content: text })
  prompt.value = ''
  errorMessage.value = ''
  routingHint.value = ''
  contextMeta.value = null
  streaming.value = true
  // 会话历史仅保留角色/内容（去掉 SSE 聚合消息）；编排侧会自动排除当前 query
  const history: ChatMessage[] = messages.value
    .filter((m) => m.content)
    .map((m) => ({ role: m.role, content: m.content }))
  // 直连：model + messages；自动编排：mode + query（model 作为 options.model 交给编排）
  const payload: ChatStreamPayload =
    channelMode.value === 'auto'
      ? {
          mode: 'auto',
          query: text,
          messages: history,
          options: modelId.value ? { model: modelId.value } : {},
          output_mode: 'llm_response',
        }
      : { model: modelId.value, messages: history }
  // 批次 4 R7：携带「推理设置」中的上下文裁剪策略（未配置则不传，走后端默认）
  const contextPolicy = loadContextPolicy()
  if (contextPolicy) payload.context_policy = contextPolicy
  try {
    let received = ''
    await llmApi.sendChatStream(payload, (evt) => {
      if (evt.event === 'chunk' && evt.data) {
        const delta = parseDelta(evt.data)
        if (delta) {
          received += delta
          appendDelta(delta)
        }
      } else if (evt.event === 'routing' && evt.data) {
        // 批次 4 R7：routing 事件可能携带首包 context_meta
        try {
          const meta = extractContextMeta(JSON.parse(evt.data))
          if (meta) contextMeta.value = meta
        } catch {
          // 非 JSON 载荷忽略，不影响对话
        }
      } else if (evt.event === 'done' && evt.data) {
        // 收尾回执携带终态 routing_trace（首包 routing 只是决策前快照）与最终 context_meta
        try {
          const done = JSON.parse(evt.data) as { routing_trace?: unknown }
          const meta = extractContextMeta(done)
          if (meta) contextMeta.value = meta
          if (done.routing_trace && channelMode.value === 'auto') {
            updateRoutingHint(JSON.stringify(done.routing_trace))
          }
        } catch {
          // done 载荷不含 routing_trace 时保持默认提示
        }
      } else if (evt.event === 'error' && evt.data) {
        errorMessage.value = `流式对话错误：${evt.data}`
      }
    })
    if (!received) {
      messages.value.push({ role: 'assistant', content: '（未收到模型回复，请检查模型可用性与上游连通性）' })
    }
  } catch (err) {
    errorMessage.value = `对话失败：${(err as Error).message || '网络错误'}`
  } finally {
    streaming.value = false
  }
}

onMounted(() => {
  void loadModels()
})
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.channel-hint { margin-bottom: 12px; font-size: 12px; color: var(--ob-text-secondary); }
.context-meta { margin-bottom: 12px; font-size: 12px; color: var(--ob-text-secondary); }
.chat-panel { min-height: 360px; border: 1px solid var(--ob-border); border-radius: var(--ob-radius-md); padding: 16px; background: var(--ob-surface); }
.chat-msg { margin-bottom: 12px; }
.chat-role { font-weight: 600; font-size: 13px; color: var(--ob-text-secondary); }
.chat-content { margin-top: 4px; white-space: pre-wrap; line-height: 1.6; }
</style>
