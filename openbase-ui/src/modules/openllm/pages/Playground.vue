<template>
  <div>
    <div class="page-toolbar">
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
    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon closable class="mb-16" @close="errorMessage = ''" />
    <div class="chat-panel">
      <div v-for="(m, i) in messages" :key="i" class="chat-msg" :class="m.role">
        <span class="chat-role">{{ m.role === 'user' ? '我' : '模型' }}</span>
        <div class="chat-content">{{ m.content }}</div>
      </div>
      <el-empty v-if="messages.length === 0" description="选择模型并开始一段对话调试" :image-size="60" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { llmApi, type ChatMessage, type LlmModel } from '@/core/api/llm'

interface ChatMessageView { role: 'user' | 'assistant'; content: string }

const prompt = ref('')
const streaming = ref(false)
const messages = ref<ChatMessageView[]>([])
const errorMessage = ref('')
const models = ref<LlmModel[]>([])
const modelId = ref('')
const modelsLoading = ref(false)

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
  if (!modelId.value) {
    errorMessage.value = '请先选择可用模型（模型列表来自 /llm-proxy/models）'
    return
  }
  messages.value.push({ role: 'user', content: text })
  prompt.value = ''
  errorMessage.value = ''
  streaming.value = true
  // 会话历史仅保留角色/内容（去掉 SSE 聚合消息）
  const history: ChatMessage[] = messages.value
    .filter((m) => m.content)
    .map((m) => ({ role: m.role, content: m.content }))
  try {
    let received = ''
    await llmApi.sendChatStream({ model: modelId.value, messages: history }, (evt) => {
      if (evt.event === 'chunk' && evt.data) {
        const delta = parseDelta(evt.data)
        if (delta) {
          received += delta
          appendDelta(delta)
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
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
.chat-panel { min-height: 360px; border: 1px solid var(--ob-border); border-radius: var(--ob-radius-md); padding: 16px; background: var(--ob-surface); }
.chat-msg { margin-bottom: 12px; }
.chat-role { font-weight: 600; font-size: 13px; color: var(--ob-text-secondary); }
.chat-content { margin-top: 4px; white-space: pre-wrap; line-height: 1.6; }
</style>
